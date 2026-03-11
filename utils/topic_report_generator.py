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
        生成主题报告HTML

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
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
            background: #fafafa;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h2 {{
            color: #1a73e8;
            border-bottom: 2px solid #1a73e8;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        .meta {{
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        .intro {{
            background: #e8f0fe;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 25px;
            border-left: 4px solid #1a73e8;
        }}
        .topics-overview {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 25px;
        }}
        .topics-overview ul {{
            margin: 10px 0 0 0;
            padding-left: 20px;
        }}
        .topics-overview li {{
            margin: 5px 0;
        }}
        .topic-section {{
            margin: 30px 0;
            padding: 20px;
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
        }}
        .topic-header {{
            color: #1a73e8;
            margin-top: 0;
            padding-bottom: 10px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .topic-meta {{
            color: #666;
            font-size: 13px;
            margin-bottom: 15px;
        }}
        .topic-overview {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 6px;
            margin: 15px 0;
        }}
        .key-insights {{
            background: #e8f5e9;
            padding: 12px;
            border-radius: 6px;
            margin: 15px 0;
            border-left: 4px solid #34a853;
        }}
        .key-insights h4 {{
            margin: 0 0 10px 0;
            color: #34a853;
        }}
        .key-insights ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .paper-card {{
            background: #fff;
            border: 1px solid #e0e0e0;
            padding: 15px;
            margin: 15px 0;
            border-radius: 6px;
        }}
        .paper-title {{
            color: #202124;
            font-size: 15px;
            font-weight: 600;
            margin: 0 0 10px 0;
        }}
        .paper-meta {{
            color: #666;
            font-size: 12px;
            margin-bottom: 10px;
        }}
        .paper-detail {{
            margin: 8px 0;
            font-size: 14px;
        }}
        .paper-detail strong {{
            color: #5f6368;
        }}
        .paper-link {{
            color: #1a73e8;
            text-decoration: none;
            font-size: 13px;
        }}
        .paper-link:hover {{
            text-decoration: underline;
        }}
        .footer {{
            color: #999;
            font-size: 12px;
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>AI Research Digest</h2>

        <div class="meta">
            <strong>Date:</strong> {date_str} | <strong>Topics:</strong> {len(topic_reports)} | <strong>Papers:</strong> {total_papers}
        </div>

        <div class="intro">
            {intro}
        </div>

        <div class="topics-overview">
            <strong>Topics in this digest:</strong>
            <ul>
"""

        # 添加主题概览
        for report in topic_reports:
            html += f"""                <li>{report.get('topic_name', 'Unknown')} ({report.get('paper_count', 0)} papers)</li>\n"""

        html += """            </ul>
        </div>

"""

        # 添加每个主题的详细内容
        for i, report in enumerate(topic_reports, 1):
            topic_name = report.get('topic_name', 'Unknown')
            overview = report.get('overview', 'N/A')
            key_insights = report.get('key_insights', [])
            papers = report.get('papers', [])
            paper_analyses = report.get('paper_analyses', [])

            html += f"""        <div class="topic-section">
            <h3 class="topic-header">Topic {i}: {topic_name}</h3>

            <div class="topic-meta">
                {report.get('paper_count', 0)} papers in this topic
            </div>

            <div class="topic-overview">
                <strong>Overview:</strong> {overview}
            </div>
"""

            # 关键洞察
            if key_insights:
                html += """            <div class="key-insights">
                <h4>Key Insights</h4>
                <ul>
"""
                for insight in key_insights[:5]:
                    html += f"                    <li>{insight}</li>\n"
                html += """                </ul>
            </div>
"""

            # 论文列表
            html += """            <div class="papers-section">
                <h4>Papers in this topic:</h4>
"""

            for j, paper in enumerate(papers, 1):
                analysis = paper_analyses[j-1] if j <= len(paper_analyses) else {}
                title = paper.get('title', 'N/A')
                authors = ', '.join(paper.get('authors', [])[:3])
                if len(paper.get('authors', [])) > 3:
                    authors += ' et al.'
                score = paper.get('importance_score', 0)
                url = paper.get('url', '#')
                pub_date = paper.get('published_date', 'N/A')

                relevance = analysis.get('relevance', 'Related to this topic')
                contribution = analysis.get('main_contribution', 'N/A')
                experiments = analysis.get('key_experiments', 'N/A')
                insight = analysis.get('key_insight', 'N/A')

                html += f"""                <div class="paper-card">
                    <p class="paper-title">{j}. {title}</p>
                    <p class="paper-meta">
                        <strong>Authors:</strong> {authors} |
                        <strong>Score:</strong> {score:.1f}/10 |
                        <strong>Published:</strong> {pub_date}
                    </p>
                    <p class="paper-detail"><strong>Why relevant:</strong> {relevance}</p>
                    <p class="paper-detail"><strong>Main contribution:</strong> {contribution}</p>
                    <p class="paper-detail"><strong>Key experiments:</strong> {experiments}</p>
                    <p class="paper-detail"><strong>Key insight:</strong> {insight}</p>
                    <a class="paper-link" href="{url}">View Paper</a>
                </div>
"""

            html += """            </div>
        </div>

"""

        html += f"""        <div class="footer">
            This automated report was generated on {timestamp}.<br>
            Powered by AI Research Digest System.
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