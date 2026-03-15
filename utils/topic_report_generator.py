"""
Topic Report Generator - 主题报告生成模块
生成基于主题的论文报告，包含主题概述和论文相关性分析
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm_client import LLMClient
from utils.topic_clusterer import TopicClusterer
from utils.email_sender import EmailSender
from prompts.topic_prompts import get_topic_summary_prompt, get_daily_digest_intro_prompt


class TopicReportGenerator:
    """主题报告生成器"""

    def __init__(self, llm_client: LLMClient, email_sender: EmailSender = None):
        """
        初始化报告生成器

        Args:
            llm_client: LLM客户端
            email_sender: 邮件发送器（可选）
        """
        self.llm_client = llm_client
        self.email_sender = email_sender
        self.clusterer = TopicClusterer(llm_client)

    async def generate_report(self, papers: List[Dict[str, Any]], date_str: str = None) -> Dict[str, Any]:
        """
        生成主题报告

        Args:
            papers: 论文列表
            date_str: 日期字符串

        Returns:
            报告数据 {
                "topic_reports": List[Dict],
                "html": str,
                "intro": str
            }
        """
        if not papers:
            return {"topic_reports": [], "html": "", "intro": ""}

        date_str = date_str or datetime.now().strftime("%Y-%m-%d")

        print(f"\n📊 生成主题报告 ({len(papers)} 篇论文)...")

        # 1. 聚类论文
        clusters = await self.clusterer.cluster_papers(papers)

        if not clusters:
            print("   ⚠️  聚类失败，生成单主题报告")
            clusters = {"AI Research": {"description": "Latest AI research", "key_insights": [], "papers": papers}}

        # 2. 为每个主题生成摘要
        topic_reports = []
        for topic_name, topic_data in clusters.items():
            print(f"   📝 生成主题摘要: {topic_name}...")

            summary = await self._summarize_topic(topic_name, topic_data)

            topic_reports.append({
                "topic_name": topic_name,
                "topic_description": topic_data.get("description", ""),
                "overview": summary.get("overview", ""),
                "key_insights": summary.get("key_insights", []),
                "paper_analyses": summary.get("paper_analyses", []),
                "papers": topic_data.get("papers", []),
                "paper_count": len(topic_data.get("papers", []))
            })

        # 3. 生成整体介绍
        intro = await self._generate_intro(topic_reports, date_str)

        # 4. 生成HTML
        html = self._generate_topic_html(topic_reports, date_str, intro)

        print(f"   ✅ 报告生成完成，共 {len(topic_reports)} 个主题")

        return {
            "topic_reports": topic_reports,
            "html": html,
            "intro": intro
        }

    async def _summarize_topic(self, topic_name: str, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        为主题生成摘要

        Args:
            topic_name: 主题名称
            topic_data: 主题数据

        Returns:
            摘要数据
        """
        papers = topic_data.get("papers", [])
        description = topic_data.get("description", "")

        if not papers:
            return {"overview": "", "key_insights": [], "paper_analyses": []}

        prompt = get_topic_summary_prompt(topic_name, description, papers)

        try:
            result = await self.llm_client.call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=3000
            )

            if result.get('success'):
                content = result['content']
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    return json.loads(json_str)

        except Exception as e:
            print(f"   ⚠️  主题摘要生成失败: {e}")

        # 回退：生成简单摘要
        return self._generate_fallback_summary(papers)

    def _generate_fallback_summary(self, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成回退摘要"""
        overview = f"This topic covers {len(papers)} research papers in AI/LLM area."

        key_insights = []
        paper_analyses = []

        for i, paper in enumerate(papers, 1):
            # 提取关键洞察
            if paper.get('summary'):
                key_insights.append(paper['summary'][:100])

            paper_analyses.append({
                "paper_id": i,
                "relevance": "Related to this topic",
                "main_contribution": paper.get('summary', 'N/A')[:100],
                "key_experiments": ", ".join(paper.get('key_methods', [])[:2]) if paper.get('key_methods') else 'N/A',
                "key_insight": paper.get('one_sentence', 'N/A')[:100] if paper.get('one_sentence') else paper.get('summary', 'N/A')[:100]
            })

        return {
            "overview": overview,
            "key_insights": key_insights[:5],
            "paper_analyses": paper_analyses
        }

    async def _generate_intro(self, topic_reports: List[Dict], date_str: str) -> str:
        """生成日报介绍"""
        prompt = get_daily_digest_intro_prompt(topic_reports, date_str)

        try:
            result = await self.llm_client.call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )

            if result.get('success'):
                content = result['content']
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    data = json.loads(json_str)
                    return data.get('intro', '')

        except Exception as e:
            print(f"   ⚠️  介绍生成失败: {e}")

        # 回退介绍
        total_papers = sum(r.get('paper_count', 0) for r in topic_reports)
        topics = [r.get('topic_name', '') for r in topic_reports]
        return f"Today's AI research digest covers {len(topic_reports)} topics with {total_papers} papers: {', '.join(topics[:3])}{'...' if len(topics) > 3 else ''}."

    def _generate_topic_html(self, topic_reports: List[Dict], date_str: str, intro: str) -> str:
        """
        生成主题报告HTML (移动端优化)

        Args:
            topic_reports: 主题报告列表
            date_str: 日期字符串
            intro: 介绍文本

        Returns:
            HTML字符串
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_papers = sum(r.get('paper_count', 0) for r in topic_reports)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="format-detection" content="telephone=no">
    <title>AI Research Digest</title>
    <style>
        * {{
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }}
        html {{
            font-size: 16px;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.5;
            color: #1a1a1a;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{
            max-width: 100%;
            margin: 0 auto;
            background: #fff;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 16px;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 1.3rem;
            font-weight: 600;
        }}
        .header .meta {{
            font-size: 0.85rem;
            opacity: 0.9;
        }}
        .intro {{
            background: linear-gradient(135deg, #e8f4f8 0%, #e8f0fe 100%);
            padding: 16px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 0.95rem;
            line-height: 1.6;
        }}
        .topics-nav {{
            background: #fafafa;
            padding: 12px 16px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .topics-nav-title {{
            font-size: 0.85rem;
            color: #666;
            margin-bottom: 8px;
        }}
        .topics-nav-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .topic-tag {{
            background: #e8f0fe;
            color: #1a73e8;
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 0.8rem;
            text-decoration: none;
            display: inline-block;
        }}
        .topic-section {{
            border-bottom: 8px solid #f0f0f0;
        }}
        .topic-header {{
            background: linear-gradient(135deg, #1a73e8 0%, #4285f4 100%);
            color: white;
            padding: 16px;
        }}
        .topic-header h2 {{
            margin: 0;
            font-size: 1.1rem;
            font-weight: 600;
        }}
        .topic-header .count {{
            font-size: 0.85rem;
            opacity: 0.9;
            margin-top: 4px;
        }}
        .topic-overview {{
            background: #fafafa;
            padding: 16px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 0.9rem;
            line-height: 1.6;
        }}
        .key-insights {{
            background: #e8f5e9;
            padding: 16px;
            border-left: 4px solid #34a853;
            margin: 0;
        }}
        .key-insights h3 {{
            margin: 0 0 12px 0;
            font-size: 0.95rem;
            color: #2e7d32;
        }}
        .key-insights ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .key-insights li {{
            margin: 8px 0;
            font-size: 0.85rem;
            line-height: 1.5;
        }}
        .paper-card {{
            border-bottom: 1px solid #e0e0e0;
            padding: 16px;
        }}
        .paper-card:last-child {{
            border-bottom: none;
        }}
        .paper-title {{
            font-size: 1rem;
            font-weight: 600;
            color: #202124;
            margin: 0 0 10px 0;
            line-height: 1.4;
        }}
        .paper-meta {{
            font-size: 0.75rem;
            color: #666;
            margin-bottom: 12px;
        }}
        .paper-meta span {{
            display: inline-block;
            margin-right: 12px;
        }}
        .paper-detail {{
            background: #fafafa;
            padding: 10px 12px;
            border-radius: 8px;
            margin: 8px 0;
            font-size: 0.85rem;
        }}
        .paper-detail strong {{
            color: #333;
            display: block;
            margin-bottom: 4px;
        }}
        .paper-link {{
            display: inline-block;
            margin-top: 12px;
            color: #1a73e8;
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        .paper-link:after {{
            content: ' →';
        }}
        .footer {{
            text-align: center;
            padding: 20px 16px;
            color: #999;
            font-size: 0.8rem;
            background: #fafafa;
        }}
        @media (min-width: 768px) {{
            .container {{
                max-width: 600px;
                margin: 0 auto;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI Research Digest</h1>
            <div class="meta">{date_str} · {len(topic_reports)} Topics · {total_papers} Papers</div>
        </div>

        <div class="intro">
            {intro}
        </div>

        <div class="topics-nav">
            <div class="topics-nav-title">Topics in this digest:</div>
            <div class="topics-nav-list">
"""

        # 添加主题导航
        for i, report in enumerate(topic_reports, 1):
            topic_name = report.get('topic_name', 'Unknown')[:30]
            html += f'                <a href="#topic-{i}" class="topic-tag">{topic_name}</a>\n'

        html += """            </div>
        </div>

"""

        # 添加每个主题的详细内容
        for i, report in enumerate(topic_reports, 1):
            topic_name = report.get('topic_name', 'Unknown')
            overview = report.get('overview', 'N/A')
            key_insights = report.get('key_insights', [])
            papers = report.get('papers', [])
            paper_analyses = report.get('paper_analyses', [])

            html += f"""        <div class="topic-section" id="topic-{i}">
            <div class="topic-header">
                <h2>Topic {i}: {topic_name}</h2>
                <div class="count">{report.get('paper_count', 0)} papers</div>
            </div>

            <div class="topic-overview">
                {overview}
            </div>
"""

            # 关键洞察
            if key_insights:
                html += """            <div class="key-insights">
                <h3>💡 Key Insights</h3>
                <ul>
"""
                for insight in key_insights[:5]:
                    html += f"                    <li>{insight}</li>\n"
                html += """                </ul>
            </div>
"""

            # 论文列表
            for j, paper in enumerate(papers, 1):
                analysis = paper_analyses[j-1] if j <= len(paper_analyses) else {}
                title = paper.get('title', 'N/A')
                authors = ', '.join(paper.get('authors', [])[:2])
                if len(paper.get('authors', [])) > 2:
                    authors += ' et al.'
                score = paper.get('importance_score', 0)
                url = paper.get('url', '#')
                pub_date = paper.get('published_date', 'N/A')

                relevance = analysis.get('relevance', 'Related to this topic')
                contribution = analysis.get('main_contribution', 'N/A')
                insight = analysis.get('key_insight', 'N/A')

                html += f"""            <div class="paper-card">
                <p class="paper-title">{j}. {title}</p>
                <div class="paper-meta">
                    <span>👤 {authors}</span>
                    <span>⭐ {score:.1f}/10</span>
                    <span>📅 {pub_date}</span>
                </div>
                <div class="paper-detail">
                    <strong>Why relevant</strong>
                    {relevance}
                </div>
                <div class="paper-detail">
                    <strong>Main contribution</strong>
                    {contribution}
                </div>
                <div class="paper-detail">
                    <strong>Key insight</strong>
                    {insight}
                </div>
                <a href="{url}" class="paper-link">View Paper</a>
            </div>
"""

            html += """        </div>

"""

        html += f"""        <div class="footer">
            Generated on {timestamp}<br>
            AI Research Digest System
        </div>
    </div>
</body>
</html>
"""

        return html

    def save_report(self, report_data: Dict[str, Any], output_dir: str = "data") -> str:
        """
        保存报告到文件

        Args:
            report_data: 报告数据
            output_dir: 输出目录

        Returns:
            保存的文件路径
        """
        os.makedirs(output_dir, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")

        # 保存HTML
        html_path = os.path.join(output_dir, f"topic_report_{date_str}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(report_data.get('html', ''))

        # 保存JSON
        json_path = os.path.join(output_dir, f"topic_report_{date_str}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            # 移除HTML，太大
            save_data = {k: v for k, v in report_data.items() if k != 'html'}
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        print(f"   💾 报告已保存: {html_path}")

        return html_path

    async def send_report_email(self, report_data: Dict[str, Any], subject: str = None) -> bool:
        """
        发送报告邮件

        Args:
            report_data: 报告数据
            subject: 邮件主题

        Returns:
            是否发送成功
        """
        if not self.email_sender:
            print("   ⚠️  未配置邮件发送器")
            return False

        date_str = datetime.now().strftime("%Y-%m-%d")
        subject = subject or f"AI Research Digest ({date_str})"

        html_content = report_data.get('html', '')
        if not html_content:
            print("   ⚠️  没有HTML内容")
            return False

        return self.email_sender.send_email_report(html_content, subject)


async def main():
    """测试报告生成"""
    # 创建测试数据
    test_papers = [
        {
            "title": "Test-Time Compute for Better Reasoning",
            "abstract": "We propose a new method for scaling compute during test time.",
            "importance_score": 9.0,
            "authors": ["Author A", "Author B"],
            "published_date": "2026-03-10",
            "url": "https://arxiv.org/abs/1234.5678",
            "key_methods": ["test-time scaling", "reasoning"],
            "summary": "Novel approach to improve reasoning by scaling compute at test time.",
            "one_sentence": "Test-time compute can significantly improve LLM reasoning."
        },
        {
            "title": "Multimodal Agent for Visual Tasks",
            "abstract": "A multimodal agent that can understand images and solve visual tasks.",
            "importance_score": 8.5,
            "authors": ["Author C", "Author D"],
            "published_date": "2026-03-09",
            "url": "https://arxiv.org/abs/2345.6789",
            "key_methods": ["multimodal", "agent"],
            "summary": "A new agent architecture for visual task solving.",
            "one_sentence": "Multimodal agents show promising results on visual benchmarks."
        }
    ]

    # 初始化
    llm_client = LLMClient()
    generator = TopicReportGenerator(llm_client)

    # 生成报告
    report = await generator.generate_report(test_papers)

    # 保存报告
    generator.save_report(report)

    # 打印部分HTML
    print("\n📄 HTML预览 (前500字符):")
    print(report['html'][:500])


if __name__ == "__main__":
    asyncio.run(main())