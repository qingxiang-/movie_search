"""
Hot Topic Discovery - 发现AI/LLM/Agent领域的热门研究主题
每周运行，从Brave Search和arXiv获取近期研究动态，提取热门主题和关键词
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接导入避免循环依赖
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))
from llm_client import LLMClient
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'prompts'))
from topic_prompts import (
    get_trend_extraction_prompt,
    get_keyword_generation_from_trends_prompt
)


class HotTopicDiscovery:
    """发现AI/LLM/Agent领域的热门研究主题"""

    def __init__(self, llm_client: LLMClient, brave_api_key: str = None, proxy: str = None):
        """
        初始化热门主题发现器

        Args:
            llm_client: LLM客户端
            brave_api_key: Brave Search API密钥
            proxy: 代理设置
        """
        self.llm_client = llm_client
        self.brave_api_key = brave_api_key or os.getenv("BRAVE_API_KEY", "")
        self.proxy = proxy or os.getenv("HTTP_PROXY", "http://127.0.0.1:7890")

        # 加载配置
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "hot_topic_sources.json"
        )

        default_config = {
            "search_queries": [
                "LLM research trends 2026",
                "AI agent developments 2026",
                "multimodal LLM breakthrough",
                "reasoning scaling LLM",
                "LLM training efficiency 2026",
                "AI safety research latest",
                "LLM evaluation benchmark 2026"
            ],
            "arxiv_categories": ["cs.CL", "cs.AI", "cs.LG"],
            "lookback_months": 6,
            "max_topics_per_week": 10,
            "max_articles_per_query": 5,
            "max_papers_from_arxiv": 20
        }

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                print(f"⚠️  加载配置文件失败: {e}，使用默认配置")

        return default_config

    async def discover_trending_topics(self) -> List[Dict[str, Any]]:
        """
        发现热门研究主题

        Returns:
            热门主题列表 [{"topic": str, "description": str, "keywords": List[str], "priority": int}]
        """
        print("=" * 70)
        print("🔍 开始发现热门研究主题")
        print("=" * 70)

        # 1. 从Brave Search获取文章
        print("\n📰 步骤1: 从Brave Search获取AI研究动态...")
        articles = await self._search_trend_articles()
        print(f"   ✅ 获取到 {len(articles)} 篇文章")

        # 2. 从arXiv获取近期高影响力论文
        print("\n📚 步骤2: 从arXiv获取近期热门论文...")
        papers = await self._search_trending_papers()
        print(f"   ✅ 获取到 {len(papers)} 篇论文")

        # 3. 使用LLM提取主题
        print("\n🤖 步骤3: 使用LLM分析并提取热门主题...")
        topics = await self._extract_topics_with_llm(articles, papers)
        print(f"   ✅ 提取到 {len(topics)} 个热门主题")

        # 显示结果
        print("\n" + "=" * 70)
        print("📊 发现的热门研究主题:")
        print("=" * 70)
        for i, topic in enumerate(topics[:self.config['max_topics_per_week']], 1):
            print(f"\n{i}. {topic['topic']} (优先级: {topic['priority']}/10)")
            print(f"   描述: {topic['description']}")
            print(f"   关键词: {', '.join(topic['keywords'])}")

        return topics[:self.config['max_topics_per_week']]

    async def _search_trend_articles(self) -> List[Dict[str, Any]]:
        """从Brave Search获取AI研究趋势文章"""
        if not self.brave_api_key:
            print("   ⚠️  未配置BRAVE_API_KEY，跳过Brave搜索")
            return self._get_fallback_articles()

        articles = []
        queries = self.config['search_queries']

        for query in queries:
            try:
                results = self._fetch_brave_search(query)
                articles.extend(results)
                await asyncio.sleep(1)  # 避免请求过快
            except Exception as e:
                print(f"   ⚠️  查询 '{query}' 失败: {e}")

        # 去重
        seen_titles = set()
        unique_articles = []
        for article in articles:
            title_lower = article.get('title', '').lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_articles.append(article)

        return unique_articles[:30]  # 最多30篇

    def _fetch_brave_search(self, query: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        使用Brave Search API搜索

        Args:
            query: 搜索查询
            count: 结果数量

        Returns:
            文章列表
        """
        # 使用web搜索而非新闻搜索，获取更广泛的结果
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.brave_api_key
        }

        # 计算日期范围（过去6个月）
        lookback_months = self.config.get('lookback_months', 6)
        freshness = f"{lookback_months * 30}d"

        params = {
            "q": query,
            "count": count,
            "freshness": freshness,
        }

        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None

        response = requests.get(url, headers=headers, params=params, timeout=15, proxies=proxies)
        response.raise_for_status()

        result = response.json()
        web_results = result.get("web", {}).get("results", [])

        articles = []
        for item in web_results:
            articles.append({
                "title": item.get("title", "N/A"),
                "snippet": item.get("description", ""),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
            })

        return articles

    async def _search_trending_papers(self) -> List[Dict[str, Any]]:
        """从arXiv获取近期热门论文"""
        papers = []

        # 使用arXiv API搜索最近6个月的高影响力论文
        lookback_months = self.config.get('lookback_months', 6)
        start_date = datetime.now() - timedelta(days=lookback_months * 30)

        # 构建arXiv查询
        categories = self.config.get('arxiv_categories', ['cs.CL', 'cs.AI', 'cs.LG'])

        for category in categories:
            try:
                results = self._fetch_arxiv_papers(category, start_date)
                papers.extend(results)
                await asyncio.sleep(2)  # arXiv API限制
            except Exception as e:
                print(f"   ⚠️  arXiv类别 '{category}' 搜索失败: {e}")

        # 按重要性排序（这里用更新时间作为代理）
        papers.sort(key=lambda x: x.get('published', ''), reverse=True)

        return papers[:self.config.get('max_papers_from_arxiv', 20)]

    def _fetch_arxiv_papers(self, category: str, start_date: datetime, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        从arXiv API获取论文

        Args:
            category: arXiv类别
            start_date: 起始日期
            max_results: 最大结果数

        Returns:
            论文列表
        """
        # arXiv API URL
        base_url = "http://export.arxiv.org/api/query"

        # 构建查询
        query = f"cat:{category}"
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }

        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None

        response = requests.get(base_url, params=params, timeout=30, proxies=proxies)
        response.raise_for_status()

        # 解析XML响应
        papers = self._parse_arxiv_response(response.text)

        return papers

    def _parse_arxiv_response(self, xml_text: str) -> List[Dict[str, Any]]:
        """解析arXiv API的XML响应"""
        import xml.etree.ElementTree as ET

        papers = []

        try:
            root = ET.fromstring(xml_text)

            # arXiv API使用Atom命名空间
            ns = {'atom': 'http://www.w3.org/2005/Atom',
                  'arxiv': 'http://arxiv.org/schemas/atom'}

            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns)
                summary = entry.find('atom:summary', ns)
                published = entry.find('atom:published', ns)
                link = entry.find('atom:id', ns)

                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns)
                    if name is not None:
                        authors.append(name.text)

                paper = {
                    'title': title.text.strip() if title is not None else 'N/A',
                    'abstract': summary.text.strip() if summary is not None else '',
                    'published': published.text[:10] if published is not None else '',
                    'url': link.text if link is not None else '',
                    'authors': authors[:5],
                    'source': 'arXiv'
                }

                papers.append(paper)

        except Exception as e:
            print(f"   ⚠️  解析arXiv响应失败: {e}")

        return papers

    async def _extract_topics_with_llm(self, articles: List[Dict], papers: List[Dict]) -> List[Dict[str, Any]]:
        """使用LLM从文章和论文中提取热门主题"""
        if not articles and not papers:
            print("   ⚠️  没有足够的内容进行分析")
            return self._get_default_topics()

        prompt = get_trend_extraction_prompt(articles, papers)

        try:
            result = await self.llm_client.call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=3000
            )

            if result.get('success'):
                content = result['content']
                # 提取JSON
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    data = json.loads(json_str)
                    return data.get('topics', [])

        except Exception as e:
            print(f"   ⚠️  LLM提取主题失败: {e}")

        return self._get_default_topics()

    def _get_default_topics(self) -> List[Dict[str, Any]]:
        """返回默认的热门主题"""
        return [
            {"topic": "LLM Agent", "description": "智能体系统，工具使用，自主决策", "keywords": ["LLM agent", "AI agent", "autonomous agent"], "priority": 9},
            {"topic": "Multimodal LLM", "description": "视觉语言模型，多模态理解与生成", "keywords": ["multimodal LLM", "vision language model"], "priority": 9},
            {"topic": "LLM Reasoning", "description": "推理能力提升，思维链，复杂问题求解", "keywords": ["LLM reasoning", "chain-of-thought"], "priority": 8},
            {"topic": "Test-Time Compute", "description": "推理时计算，思维时间优化", "keywords": ["test-time compute", "inference scaling"], "priority": 8},
            {"topic": "LLM Evaluation", "description": "模型评估基准，能力测试", "keywords": ["LLM evaluation", "LLM benchmark"], "priority": 7},
            {"topic": "AI Safety", "description": "AI安全，对齐，风险控制", "keywords": ["AI safety", "LLM alignment"], "priority": 7},
            {"topic": "Efficient Training", "description": "高效训练方法，参数优化", "keywords": ["efficient training", "parameter efficient"], "priority": 6},
            {"topic": "Code Generation", "description": "代码生成，编程助手", "keywords": ["code generation", "code LLM"], "priority": 6}
        ]

    def _get_fallback_articles(self) -> List[Dict[str, Any]]:
        """返回备用的文章数据（当Brave API不可用时）"""
        return [
            {"title": "LLM Agent Research Trends 2026", "snippet": "Latest developments in LLM agents, tool use, and autonomous systems", "source": "fallback"},
            {"title": "Multimodal LLM Breakthrough", "snippet": "Vision-language models continue to advance with new architectures", "source": "fallback"},
            {"title": "Reasoning Scaling in LLMs", "snippet": "Test-time compute and reasoning scaling become key research areas", "source": "fallback"}
        ]

    async def generate_keywords_from_topics(self, topics: List[Dict[str, Any]]) -> List[str]:
        """
        从热门主题生成搜索关键词

        Args:
            topics: 热门主题列表

        Returns:
            关键词列表
        """
        prompt = get_keyword_generation_from_trends_prompt(topics)

        try:
            result = await self.llm_client.call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=2000
            )

            if result.get('success'):
                content = result['content']
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    data = json.loads(json_str)
                    return data.get('keywords', [])

        except Exception as e:
            print(f"   ⚠️  LLM生成关键词失败: {e}")

        # 回退到直接从主题提取关键词
        keywords = []
        for topic in topics[:10]:
            keywords.extend(topic.get('keywords', [])[:2])
        return keywords[:20]


async def main():
    """测试热门主题发现"""
    # 初始化LLM客户端
    llm_client = LLMClient()

    # 创建发现器
    discovery = HotTopicDiscovery(llm_client)

    # 发现热门主题
    topics = await discovery.discover_trending_topics()

    # 生成关键词
    keywords = await discovery.generate_keywords_from_topics(topics)
    print(f"\n📝 生成的关键词: {keywords}")


if __name__ == "__main__":
    asyncio.run(main())