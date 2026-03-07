"""
Paper Search Agent - 学术论文搜索 Agent
"""

import json
import re
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import quote
from datetime import datetime, timedelta

from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_agent import BaseBrowserAgent
from prompts.paper_prompts import (
    get_query_planning_prompt,
    get_decision_making_prompt,
    get_summarization_prompt,
    get_topic_generation_prompt,
    get_topic_refinement_prompt,
    get_keyword_generation_prompt,
    get_keyword_refinement_prompt,
    get_keyword_discovery_prompt
)
from utils.candidate_pool import CandidatePool
from utils.deduplication import DeduplicationManager
from utils.email_sender import EmailSender
from utils.paper_keyword_config import PaperKeywordConfig, KeywordRotation


class PaperSearchAgent(BaseBrowserAgent):
    """学术论文搜索 Agent"""
    
    # 学术搜索引擎配置
    SEARCH_ENGINES = [
        {
            "name": "Google Scholar",
            "url": "https://scholar.google.com/scholar?q=",
            "advantages": "覆盖面最广，索引最全"
        },
        {
            "name": "arXiv",
            "url": "https://arxiv.org/search/?query=",
            "advantages": "预印本，最新研究"
        },
        {
            "name": "Semantic Scholar",
            "url": "https://www.semanticscholar.org/search?q=",
            "advantages": "AI 驱动，推荐相关论文"
        },
        {
            "name": "Google",
            "url": "https://www.google.com/search?q=",
            "advantages": "查找项目页面、代码仓库"
        }
    ]
    
    def __init__(self, 
                 max_iterations: int = 30,
                 min_papers: int = 5,
                 max_papers: int = 10,
                 min_quality_score: float = 7.0,
                 date_range_days: int = 7,
                 max_retries: int = 3,
                 proxy: str = None):
        """
        初始化论文搜索 Agent
        
        Args:
            max_iterations: 最大迭代次数
            min_papers: 最少论文数量
            max_papers: 最多论文数量
            min_quality_score: 最低质量分数
            date_range_days: 日期范围（天）
            max_retries: 最大重试次数
            proxy: 代理服务器地址（如 "http://127.0.0.1:7890"）
        """
        super().__init__(max_iterations, max_retries)
        
        self.candidate_pool = CandidatePool(min_papers, max_papers, min_quality_score)
        self.dedup_manager = DeduplicationManager()
        self.email_sender = EmailSender()
        
        self.date_range_days = date_range_days
        self.query_history = []
        self.topic = ""
        self.proxy = proxy

        # 关键词配置
        self.keyword_config = PaperKeywordConfig()
        self.keyword_rotation = None
        self.current_keywords = []
        self.llm_generated_keywords = []

    def initialize_keyword_rotation(self):
        """初始化关键词轮换"""
        # 使用关键词池（种子词 + 发现的词）
        self.current_keywords = self.keyword_config.get_keyword_pool()

        keywords_per_day = self.keyword_config.get_keywords_per_day()
        self.keyword_rotation = KeywordRotation(self.current_keywords, keywords_per_day)
    
    def get_date_range(self) -> tuple:
        """获取日期范围"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.date_range_days)
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
    
    def build_search_url(self, engine_name: str, query: str) -> str:
        """
        构建带日期参数的搜索 URL
        
        Args:
            engine_name: 搜索引擎名称
            query: 搜索查询
            
        Returns:
            完整的搜索 URL
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.date_range_days)
        current_year = end_date.year

        engine = next((e for e in self.SEARCH_ENGINES if e['name'] == engine_name), self.SEARCH_ENGINES[0])
        base_url = engine['url']
        
        if engine_name == "Google Scholar":
            # Google Scholar 日期参数: as_ylo (year low) 和 as_yhi (year high)
            start_year = current_year
            # 如果是 1 月，同时也搜索去年的论文
            if end_date.month == 1:
                start_year = current_year - 1
            url = f"{base_url}{quote(query)}&as_ylo={start_year}&as_yhi={current_year}"
        
        elif engine_name == "arXiv":
            # arXiv 搜索参数 - 按日期排序 (不再强制限制 submittedDate，避免漏掉刚发布的论文)
            # start_date_str = start_date.strftime('%Y%m%d%H%M%S')
            # end_date_str = end_date.strftime('%Y%m%d%H%M%S')
            # date_query = f"submittedDate:[{start_date_str} TO {end_date_str}]"
            
            # 仅使用关键词搜索，依靠排序获取最新
            full_query = f"{query}"
            url = f"{base_url}{quote(full_query)}&searchtype=all&abstracts=show&order=-announced_date_first&size=50"
        
        elif engine_name == "Semantic Scholar":
            # Semantic Scholar 支持年份过滤
            start_year = current_year
            if end_date.month == 1:
                start_year = current_year - 1
            
            # 如果年份跨度大于1，构造年份参数列表（SS 参数格式为 year[0]=2025&year[1]=2026 或 year=2025-2026）
            if start_year != current_year:
                url = f"{base_url}{quote(query)}&year={start_year}-{current_year}"
            else:
                url = f"{base_url}{quote(query)}&year={current_year}"
        
        else:
            # Google 或其他搜索引擎，使用基本 URL
            url = f"{base_url}{quote(query)}"
        
        return url
    
    async def plan_query(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 LLM 规划搜索查询
        
        Args:
            context: 上下文信息
            
        Returns:
            {"success": bool, "query_plan": dict} 或 {"success": bool, "error": str}
        """
        prompt = get_query_planning_prompt(context)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "请生成下一个搜索查询"}
        ]
        
        result = await self.llm_client.call(messages, temperature=0.7)
        
        if result["success"]:
            content = result["content"]
            try:
                # 提取 JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                query_plan = json.loads(content)
                return {"success": True, "query_plan": query_plan}
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"JSON 解析失败: {e}"}
        else:
            return {"success": False, "error": result["error"]}
    
    async def plan_next_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 LLM 规划下一步操作（评估论文并决策）
        
        Args:
            context: 上下文信息
            
        Returns:
            {"success": bool, "decision": dict} 或 {"success": bool, "error": str}
        """
        prompt = get_decision_making_prompt(context)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "请评估该论文并决定下一步操作"}
        ]
        
        result = await self.llm_client.call(messages, temperature=0.3)
        
        if result["success"]:
            content = result["content"]
            try:
                # 提取 JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                decision = json.loads(content)
                return {"success": True, "decision": decision}
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"JSON 解析失败: {e}"}
        else:
            return {"success": False, "error": result["error"]}
    
    async def summarize_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 LLM 总结论文
        
        Args:
            paper: 论文信息
            
        Returns:
            总结信息字典
        """
        prompt = get_summarization_prompt(paper)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "请生成该论文的总结"}
        ]
        
        result = await self.llm_client.call(messages, temperature=0.5)
        
        if result["success"]:
            content = result["content"]
            try:
                # 提取 JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    "summary": content[:200],
                    "key_methods": [],
                    "innovations": [],
                    "applications": []
                }
        else:
            return {
                "summary": "总结生成失败",
                "key_methods": [],
                "innovations": [],
                "applications": []
            }

    async def generate_keywords_with_llm(self, recent_papers: list = None) -> List[str]:
        """
        使用 LLM 生成搜索关键词

        Args:
            recent_papers: 近期已发送的论文列表（用于避免重复）

        Returns:
            生成的关键词列表
        """
        print("\n🤖 正在使用 LLM 生成搜索关键词...")

        # 获取历史关键词（处理可能的 dict 格式）
        history_keywords = []
        for kw in self.current_keywords:
            if isinstance(kw, dict):
                # 如果是 dict 格式，提取 keywords 字段
                history_keywords.extend(kw.get('keywords', []))
            elif isinstance(kw, str):
                history_keywords.append(kw)

        # 构建上下文
        context = {
            "user_interests": self.keyword_config.get_user_interests(),
            "num_keywords": self.keyword_config.get_num_keywords(),
            "keywords_per_topic": self.keyword_config.get_keywords_per_topic(),
            "history_keywords": history_keywords,
            "recent_papers": recent_papers or []
        }

        prompt = get_keyword_generation_prompt(context)

        try:
            response = await self.call_llm(prompt)

            # 解析 JSON 响应
            import json
            try:
                result = json.loads(response)
                keywords = []

                for item in result.get("keywords", []):
                    # 每个主题的关键词
                    topic_keywords = item.get("keywords", [])
                    keywords.extend(topic_keywords)

                print(f"✅ LLM 生成了 {len(keywords)} 个关键词")

                # 保存到配置
                self.keyword_config.update_keywords_from_llm(keywords)
                self.llm_generated_keywords = keywords
                self.current_keywords = keywords

                return keywords

            except json.JSONDecodeError as e:
                print(f"⚠️  关键词解析失败: {e}")
                # 降级使用默认关键词
                return self.keyword_config.get_keywords()

        except Exception as e:
            print(f"⚠️  LLM 关键词生成失败: {e}")
            return self.keyword_config.get_keywords()

    def _flatten_keywords(self, keywords: List) -> List[str]:
        """
        将关键词列表展平为字符串列表

        Args:
            keywords: 可能包含 dict 或 str 的列表

        Returns:
            展平后的字符串列表
        """
        result = []
        for kw in keywords:
            if isinstance(kw, dict):
                result.extend(kw.get('keywords', []))
            elif isinstance(kw, str):
                result.append(kw)
        return result

    def get_today_keywords(self) -> List[str]:
        """
        获取今天应该使用的关键词

        Returns:
            关键词列表
        """
        if not self.keyword_rotation:
            self.initialize_keyword_rotation()

        keywords = self.keyword_rotation.get_keywords_for_today() if self.keyword_config.is_rotation_enabled() else self.current_keywords
        return self._flatten_keywords(keywords)

    def get_all_keywords(self) -> List[str]:
        """
        获取所有关键词（用于完整搜索）

        Returns:
            关键词列表
        """
        if not self.current_keywords:
            self.initialize_keyword_rotation()

        return self._flatten_keywords(self.current_keywords)

    async def discover_keywords_from_results(self, current_keyword: str, papers: List[Dict]) -> List[str]:
        """
        从搜索结果中发现新关键词

        Args:
            current_keyword: 当前搜索的关键词
            papers: 搜索到的论文列表

        Returns:
            发现的关键词列表
        """
        if not papers:
            return []

        print(f"\n🔍 正在从 '{current_keyword}' 搜索结果中发现新关键词...")

        # 获取已有的关键词池
        existing_keywords = self.keyword_config.get_keyword_pool()

        # 构建上下文
        context = {
            "current_keyword": current_keyword,
            "papers": papers,
            "existing_keywords": existing_keywords
        }

        prompt = get_keyword_discovery_prompt(context)

        try:
            response = await self.call_llm(prompt)

            # 解析 JSON 响应
            import json
            try:
                result = json.loads(response)
                discovered = result.get("discovered_keywords", [])

                if discovered:
                    print(f"✅ 从 '{current_keyword}' 发现了 {len(discovered)} 个新关键词")
                    # 添加到配置池
                    self.keyword_config.add_discovered_keywords(discovered)
                    # 更新当前关键词池
                    self.current_keywords = self.keyword_config.get_keyword_pool()
                    # 重新初始化轮换
                    self.keyword_rotation = KeywordRotation(
                        self.current_keywords,
                        self.keyword_config.get_keywords_per_day()
                    )

                return discovered

            except json.JSONDecodeError as e:
                print(f"⚠️  关键词发现解析失败: {e}")
                return []

        except Exception as e:
            print(f"⚠️  关键词发现失败: {e}")
            return []

    def clean_html(self, html: str, source: str = "Google Scholar") -> str:
        """
        清理 HTML，只保留主要内容，去掉边框、banner、广告等
        
        Args:
            html: 原始 HTML
            source: 来源
            
        Returns:
            清理后的 HTML 字符串
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除不需要的元素
        for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'noscript']):
            tag.decompose()
        
        # 移除广告和导航相关的 class
        for tag in soup.find_all(class_=re.compile(r'(ad|banner|nav|menu|sidebar|footer|header)', re.I)):
            tag.decompose()
        
        # 根据来源提取主要内容区域
        main_content = None
        if source == "Google Scholar":
            # 只保留搜索结果区域
            main_content = soup.find('div', id='gs_res_ccl_mid')
            if not main_content:
                main_content = soup.find_all(class_='gs_ri')
        elif source == "arXiv":
            # 只保留论文列表
            main_content = soup.find('ol', class_='breathe-horizontal')
            if not main_content:
                main_content = soup.find_all(class_='arxiv-result')
        
        if main_content:
            if isinstance(main_content, list):
                # 如果是列表，创建一个容器
                container = soup.new_tag('div')
                for item in main_content[:10]:  # 只保留前10个结果
                    container.append(item)
                return str(container)
            return str(main_content)
        
        return str(soup)
    
    async def extract_papers_with_llm(self, html: str, source: str, topic: str) -> List[Dict[str, Any]]:
        """
        使用 LLM 从 HTML 中提取论文信息
        
        Args:
            html: 清理后的 HTML
            source: 来源
            topic: 搜索主题
            
        Returns:
            论文信息列表
        """
        prompt = f"""你是论文信息提取专家。请从以下 HTML 中提取论文信息。

【当前时间】
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

【HTML 内容】
{html[:8000]}

【提取要求】
1. 提取每篇论文的以下信息：
   - title: 论文标题
   - authors: 作者列表（最多5个）
   - abstract: 摘要（如果有）
   - url: 论文链接
   - published_date: 发表日期（YYYY-MM-DD 格式）
   - citations: 引用数（如果有）
   - venue: 发表场所/会议/期刊（如果有）

2. **时间解析规则（重要）**：
   - 相对时间：
     * "1 days ago" → 当前日期减 1 天
     * "2 weeks ago" → 当前日期减 14 天
     * "3 hours ago" → 当前日期（同一天）
   - 绝对时间：
     * "Submitted on 10 Jan 2026" → "2026-01-10"
     * "arXiv:2601.xxxxx" → 2026年1月（26表示2026年，01表示1月）
     * "2025" → "2025-01-01"
   
3. **优先提取最新论文**：
   - 优先提取 2026 年的论文
   - 其次提取 2025 年的论文
   - 忽略 2024 年及更早的论文

4. 只提取与主题 "{topic}" 相关的论文

【输出格式】
返回 JSON 数组，按发表日期从新到旧排序：
[
  {{
    "title": "论文标题",
    "authors": ["作者1", "作者2"],
    "abstract": "摘要内容",
    "url": "https://...",
    "published_date": "2026-01-10",
    "citations": 0,
    "venue": "arXiv"
  }},
  ...
]

最多返回 10 篇最新论文。如果 HTML 中没有论文信息，返回空数组 []。
"""
        
        result = await self.llm_client.call([{"role": "user", "content": prompt}])
        
        if not result.get("success"):
            return []
        
        try:
            import json
            papers_data = json.loads(result.get("content", "[]"))
            
            # 补充字段
            papers = []
            for paper in papers_data:
                paper['affiliations'] = []
                paper['pdf_url'] = ''
                paper['crawl_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                paper['source'] = source
                papers.append(paper)
            
            return papers
        except:
            return []
    
    def extract_paper_info(self, html: str, source: str = "Google Scholar") -> List[Dict[str, Any]]:
        """
        从页面提取论文信息（保留旧方法作为后备）
        
        Args:
            html: HTML 内容
            source: 来源（搜索引擎名称）
            
        Returns:
            论文信息列表
        """
        soup = BeautifulSoup(html, 'html.parser')
        papers = []
        
        if source == "Google Scholar":
            papers = self._extract_from_google_scholar(soup)
        elif source == "arXiv":
            papers = self._extract_from_arxiv(soup)
        elif source == "Semantic Scholar":
            papers = self._extract_from_semantic_scholar(soup)
        
        return papers
    
    def _extract_from_google_scholar(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """从 Google Scholar 提取论文信息"""
        papers = []
        
        for result in soup.select('.gs_ri')[:10]:
            try:
                title_elem = result.select_one('.gs_rt a')
                title = title_elem.get_text(strip=True) if title_elem else ""
                url = title_elem.get('href', '') if title_elem else ""
                
                authors_elem = result.select_one('.gs_a')
                authors_text = authors_elem.get_text(strip=True) if authors_elem else ""
                authors = [a.strip() for a in authors_text.split('-')[0].split(',')[:5]]
                
                # 提取发表年份（从 authors_text 中提取，格式如 "Author - Journal, 2024"）
                published_date = ''
                year_match = re.search(r'\b(20\d{2})\b', authors_text)
                if year_match:
                    published_date = year_match.group(1)
                
                abstract_elem = result.select_one('.gs_rs')
                abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""
                
                citations_elem = result.select_one('.gs_fl a')
                citations_text = citations_elem.get_text() if citations_elem else "0"
                citations = int(re.search(r'\d+', citations_text).group()) if re.search(r'\d+', citations_text) else 0
                
                if title:
                    papers.append({
                        'title': title,
                        'authors': authors,
                        'affiliations': [],
                        'abstract': abstract,
                        'url': url,
                        'pdf_url': '',
                        'published_date': published_date,
                        'crawl_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'citations': citations,
                        'venue': '',
                        'source': 'Google Scholar'
                    })
            except Exception as e:
                continue
        
        return papers
    
    def _extract_from_arxiv(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """从 arXiv 提取论文信息"""
        papers = []
        
        # 尝试多个可能的选择器
        results = soup.select('.arxiv-result')
        if not results:
            results = soup.select('li.arxiv-result')
        if not results:
            results = soup.select('ol.breathe-horizontal li')
        if not results:
            results = soup.select('li[class*="arxiv"]')
        
        print(f"   🐛 arXiv 选择器找到 {len(results)} 个结果元素")
        
        for result in results[:10]:
            try:
                title_elem = result.select_one('.title')
                title = title_elem.get_text(strip=True) if title_elem else ""
                
                authors_elem = result.select_one('.authors')
                authors_text = authors_elem.get_text(strip=True) if authors_elem else ""
                authors = [a.strip() for a in authors_text.replace('Authors:', '').split(',')[:5]]
                
                # 提取提交日期（arXiv 通常显示 "Submitted 4 Jan 2024"）
                published_date = ''
                date_elem = result.select_one('.is-size-7')
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    year_match = re.search(r'\b(20\d{2})\b', date_text)
                    if year_match:
                        published_date = year_match.group(1)
                        # 尝试提取完整日期
                        full_date_match = re.search(r'(\d{1,2}\s+\w+\s+20\d{2})', date_text)
                        if full_date_match:
                            published_date = full_date_match.group(1)
                
                abstract_elem = result.select_one('.abstract-full')
                abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""
                
                link_elem = result.select_one('a[href*="/abs/"]')
                url = f"https://arxiv.org{link_elem.get('href', '')}" if link_elem else ""
                pdf_url = url.replace('/abs/', '/pdf/') + '.pdf' if url else ""
                
                if title:
                    papers.append({
                        'title': title,
                        'authors': authors,
                        'affiliations': [],
                        'abstract': abstract,
                        'url': url,
                        'pdf_url': pdf_url,
                        'published_date': published_date,
                        'crawl_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'citations': 0,
                        'venue': 'arXiv',
                        'source': 'arXiv'
                    })
            except Exception as e:
                continue
        
        return papers
    
    def _extract_from_semantic_scholar(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """从 Semantic Scholar 提取论文信息"""
        papers = []
        
        for result in soup.select('.cl-paper-row')[:10]:
            try:
                title_elem = result.select_one('.cl-paper-title')
                title = title_elem.get_text(strip=True) if title_elem else ""
                url = title_elem.get('href', '') if title_elem else ""
                
                authors_elem = result.select_one('.cl-paper-authors')
                authors_text = authors_elem.get_text(strip=True) if authors_elem else ""
                authors = [a.strip() for a in authors_text.split(',')[:5]]
                
                abstract_elem = result.select_one('.cl-paper-abstract')
                abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""
                
                citations_elem = result.select_one('.cl-paper-stats__citations')
                citations_text = citations_elem.get_text() if citations_elem else "0"
                citations = int(re.search(r'\d+', citations_text).group()) if re.search(r'\d+', citations_text) else 0
                
                if title:
                    papers.append({
                        'title': title,
                        'authors': authors,
                        'affiliations': [],
                        'abstract': abstract,
                        'url': url if url.startswith('http') else f"https://www.semanticscholar.org{url}",
                        'pdf_url': '',
                        'published_date': '',
                        'crawl_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'citations': citations,
                        'venue': '',
                        'source': 'Semantic Scholar'
                    })
            except Exception as e:
                continue
        
        return papers
    
    async def execute_action(self, 
                           page: Page, 
                           action: Dict[str, Any], 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行操作
        
        Args:
            page: Playwright Page 对象
            action: 操作信息
            context: 上下文信息
            
        Returns:
            执行结果
        """
        action_type = action.get("action")
        params = action.get("params", {})
        
        # 先尝试执行通用操作
        result = await self._execute_common_action(page, action_type, params, context)
        if result is not None:
            return result
        
        # 执行论文特定操作
        try:
            if action_type == "add_to_pool":
                paper = context.get("current_paper", {})
                if self.candidate_pool.add_paper(paper):
                    print(f"✅ 已加入候选池: {paper.get('title', 'N/A')[:60]}...")
                    return {"success": True, "action_taken": "add_to_pool"}
                else:
                    return {"success": False, "error": "无法加入候选池（质量不足或重复）"}
            
            elif action_type == "extract_papers":
                print("📄 提取当前页面的论文信息...")
                return {"success": True, "action_taken": "extract_papers"}
            
            elif action_type == "view_details":
                paper_index = params.get("paper_index", 0)
                papers = context.get("papers", [])
                if 0 <= paper_index < len(papers):
                    paper_url = papers[paper_index].get('url', '')
                    if paper_url:
                        print(f"🔍 查看论文详情...")
                        success = await self._goto_with_retry(page, paper_url)
                        if success:
                            return {"success": True, "action_taken": "view_details"}
                return {"success": False, "error": "无法查看详情"}
            
            elif action_type == "change_query":
                # 这个操作会在主循环中处理，这里只是标记
                new_query = params.get("query", "")
                print(f"🔄 LLM 建议更换查询: {new_query}")
                return {"success": True, "action_taken": "change_query", "new_query": new_query}
            
            else:
                return {"success": False, "error": f"未知操作类型: {action_type}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def search_papers(self, topic: str) -> Dict[str, Any]:
        """
        搜索学术论文（主流程）
        
        Args:
            topic: 搜索主题
            
        Returns:
            搜索结果
        """
        self.topic = topic
        start_date, end_date = self.get_date_range()
        
        print(f"\n{'='*70}")
        print(f"📚 学术论文搜索系统")
        print(f"{'='*70}")
        print(f"搜索主题: {topic}")
        print(f"时间范围: {start_date} ~ {end_date}")
        print(f"目标数量: {self.candidate_pool.min_papers}-{self.candidate_pool.max_papers} 篇")
        print(f"{'='*70}\n")
        
        # 更新候选池元数据
        self.candidate_pool.update_metadata(
            topic=topic,
            date_range=f"{start_date} ~ {end_date}"
        )
        
        async with async_playwright() as p:
            # 配置浏览器启动参数
            launch_options = {"headless": True}
            if self.proxy:
                launch_options["proxy"] = {"server": self.proxy}
                print(f"🌐 使用代理: {self.proxy}")
            
            browser = await p.chromium.launch(**launch_options)
            browser_context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await browser_context.new_page()
            
            iteration = 0
            
            try:
                # 主搜索循环
                for iteration in range(1, self.max_iterations + 1):
                    print(f"\n{'─'*70}")
                    print(f"📍 迭代 {iteration}/{self.max_iterations}")
                    print(f"{'─'*70}")
                    print(f"候选池: {self.candidate_pool.get_count()}/{self.candidate_pool.max_papers} 篇")
                    
                    # 检查是否已满足条件
                    if self.candidate_pool.is_sufficient():
                        print(f"\n✅ 候选池已满足条件: {self.candidate_pool.get_status()}")
                        break
                    
                    # 检查连续 0 结果次数
                    consecutive_zeros = 0
                    if len(self.query_history) >= 3:
                        consecutive_zeros = sum(1 for q in self.query_history[-3:] if q.get('relevant_count', 0) == 0)
                    
                    # LLM 规划查询
                    print("\n🤖 正在规划搜索查询...")
                    
                    # 如果连续 3 次找到 0 结果，使用简化策略
                    if consecutive_zeros >= 3:
                        print(f"⚠️  检测到连续 {consecutive_zeros} 次找到 0 结果，使用简化策略")
                        
                        # 简化策略：使用核心关键词，不带年份，切换引擎
                        simple_queries = [
                            {"query": "reinforcement learning agents", "engine": "Google Scholar"},
                            {"query": "large language models", "engine": "Google Scholar"},
                            {"query": "AI agents", "engine": "Google Scholar"},
                            {"query": "machine learning", "engine": "arXiv"},
                        ]
                        
                        fallback_idx = (iteration - 1) % len(simple_queries)
                        query_plan = simple_queries[fallback_idx]
                        query_plan["reason"] = "简化查询以获取结果"
                        print(f"   使用简化查询: {query_plan['query']}")
                    else:
                        query_context = {
                            "topic": topic,
                            "candidate_count": self.candidate_pool.get_count(),
                            "avg_score": self.candidate_pool.get_average_score(),
                            "query_history": self.query_history,
                            "result_feedback": {}
                        }
                        
                        query_result = await self.plan_query(query_context)
                        
                        if not query_result["success"]:
                            print(f"❌ 查询规划失败: {query_result.get('error')}")
                            # 使用默认查询
                            query_plan = {
                                "query": f"{topic} recent papers",
                                "engine": "Google Scholar",
                                "reason": "默认查询"
                            }
                        else:
                            query_plan = query_result["query_plan"]
                    
                    print(f"📋 LLM 建议: \"{query_plan.get('query')}\" ({query_plan.get('engine')})")
                    print(f"   理由: {query_plan.get('reason', 'N/A')}")
                    
                    # 执行搜索
                    engine_name = query_plan.get('engine', 'Google Scholar')
                    query = query_plan.get('query', topic)
                    
                    # 使用带日期参数的搜索 URL
                    search_url = self.build_search_url(engine_name, query)
                    print(f"\n🔍 正在搜索...")
                    
                    success = await self._goto_with_retry(page, search_url, timeout=30000)
                    if not success:
                        print("❌ 搜索页面加载失败")
                        continue
                    
                    # 记录查询历史
                    self.query_history.append({
                        "query": query_plan.get('query'),
                        "engine": engine_name,
                        "relevant_count": 0
                    })
                    
                    # 提取论文信息 - 使用 LLM 理解 HTML
                    await asyncio.sleep(2)
                    html = await page.content()
                    
                    # 清理 HTML，只保留主要内容
                    cleaned_html = self.clean_html(html, engine_name)
                    
                    # 使用 LLM 从 HTML 中提取论文信息（包括时间解析）
                    print(f"   🤖 使用 LLM 理解 HTML 并提取论文信息...")
                    papers = await self.extract_papers_with_llm(cleaned_html, engine_name, topic)
                    print(f"   ✅ LLM 提取到 {len(papers)} 篇论文")
                    
                    # 如果 LLM 提取失败，尝试使用传统规则提取
                    if not papers:
                        print(f"   ⚠️ LLM 未提取到论文，尝试使用规则提取...")
                        papers = self.extract_paper_info(html, engine_name)
                        print(f"   ✅ 规则提取到 {len(papers)} 篇论文")
                    
                    # 显示提取的论文时间信息（调试用）
                    if papers:
                        print(f"   📅 论文时间范围:")
                        for p in papers[:3]:
                            print(f"      - {p.get('title', 'N/A')[:40]}... ({p.get('published_date', '未知')})")
                    
                    print(f"📄 找到 {len(papers)} 篇论文")
                    
                    if not papers:
                        print("⚠️  未找到论文，尝试下一个查询")
                        continue
                    
                    # 评估每篇论文
                    relevant_count = 0
                    for i, paper in enumerate(papers[:5], 1):  # 只评估前5篇
                        print(f"\n🤖 评估论文 {i}/{len(papers[:5])}: {paper.get('title', 'N/A')[:50]}...")
                        
                        decision_context = {
                            "topic": topic,
                            "candidate_count": self.candidate_pool.get_count(),
                            "avg_score": self.candidate_pool.get_average_score(),
                            "paper_info": paper
                        }
                        
                        decision_result = await self.plan_next_action(decision_context)
                        
                        if not decision_result["success"]:
                            print(f"   ❌ 评估失败，跳过")
                            continue
                        
                        decision = decision_result["decision"]
                        score = decision.get('importance_score', 0)
                        decision_type = decision.get('decision', 'skip')
                        
                        print(f"   评分: {score:.1f}/10 - {decision.get('reason', 'N/A')[:80]}")
                        
                        # Allow "need_more_info" if score is high enough to ensure we collect papers
                        if (decision_type == "add_to_pool" or decision_type == "need_more_info") and score >= self.candidate_pool.min_quality_score:
                            paper['importance_score'] = score
                            paper['reason'] = decision.get('reason', '')
                            paper['strengths'] = decision.get('strengths', [])
                            paper['relevance'] = decision.get('relevance', '中')
                            paper['query_used'] = query_plan.get('query')
                            
                            if self.candidate_pool.add_paper(paper):
                                print(f"   ✅ 已加入候选池")
                                relevant_count += 1
                            else:
                                print(f"   ⚠️  无法加入（可能重复或已满）")
                        else:
                            print(f"   ⏭️  跳过（{decision_type}）")
                        
                        # 避免过快请求
                        await asyncio.sleep(1)
                    
                    # 更新查询历史
                    if self.query_history:
                        self.query_history[-1]['relevant_count'] = relevant_count
                    
                    print(f"\n当前候选池状态: {self.candidate_pool.get_status()}")
                    
                    # 避免过快操作
                    await asyncio.sleep(2)
                
            finally:
                await browser.close()
        
        # 完成搜索
        self.candidate_pool.finalize()
        
        print(f"\n{'='*70}")
        print(f"✅ 搜索完成")
        print(f"{'='*70}")
        print(f"候选池: {self.candidate_pool.get_count()} 篇，平均分: {self.candidate_pool.get_average_score():.1f}")
        print(f"迭代次数: {iteration}/{self.max_iterations}")
        print(f"查询尝试: {len(self.query_history)} 个")
        print(f"{'='*70}\n")
        
        return {
            "topic": topic,
            "papers": self.candidate_pool.get_papers(),
            "iterations": iteration,
            "query_history": self.query_history
        }
    
    def _get_recent_topics(self, days: int = 7) -> List[str]:
        """
        获取最近的搜索主题
        
        Args:
            days: 天数
            
        Returns:
            主题列表
        """
        records = self.dedup_manager.records
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_topics = []
        for paper in records.get('papers', []):
            try:
                sent_date_str = paper.get('sent_date', '')
                if sent_date_str:
                    sent_date = datetime.fromisoformat(sent_date_str)
                    if sent_date >= cutoff_date:
                        topic = paper.get('topic', '')
                        if topic and topic not in recent_topics:
                            recent_topics.append(topic)
            except:
                continue
        
        return recent_topics
    
    async def generate_topic(self) -> Dict[str, Any]:
        """
        LLM 自主生成搜索主题
        
        Returns:
            {"success": bool, "topic_info": dict}
        """
        # 获取历史统计
        history = self.dedup_manager.get_statistics()
        
        context = {
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "history_topics": self._get_recent_topics(days=30),
            "total_sent": history.get('total_sent', 0),
            "recent_topics": self._get_recent_topics(days=7)
        }
        
        prompt = get_topic_generation_prompt(context)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "请生成 3-5 个最有价值的研究主题"}
        ]
        
        result = await self.llm_client.call(messages, temperature=0.8)
        
        if result["success"]:
            content = result["content"]
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                topics_data = json.loads(content)
                
                # 确保返回的是包含 topics 列表的格式
                if "topics" in topics_data:
                    return {"success": True, "topics": topics_data["topics"]}
                else:
                    # 兼容旧格式（单个主题）
                    return {"success": True, "topics": [topics_data]}
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"JSON 解析失败: {e}"}
        else:
            return {"success": False, "error": result["error"]}
    
    async def refine_topic(self, current_topic: str, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据搜索结果反馈优化主题
        
        Args:
            current_topic: 当前主题
            feedback: 搜索结果反馈
            
        Returns:
            {"success": bool, "refinement": dict}
        """
        context = {
            "current_topic": current_topic,
            "papers_found": feedback.get('papers_found', 0),
            "relevant_papers": feedback.get('relevant_papers', 0),
            "avg_score": feedback.get('avg_score', 0.0),
            "pool_status": feedback.get('pool_status', ''),
            "issues": feedback.get('issues', '')
        }
        
        prompt = get_topic_refinement_prompt(context)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "请分析并给出建议"}
        ]
        
        result = await self.llm_client.call(messages, temperature=0.7)
        
        if result["success"]:
            content = result["content"]
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                refinement = json.loads(content)
                return {"success": True, "refinement": refinement}
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"JSON 解析失败: {e}"}
        else:
            return {"success": False, "error": result["error"]}
    
    async def autonomous_search(self) -> Dict[str, Any]:
        """
        自主搜索流程（无需用户输入主题）- 支持多主题搜索
        
        Returns:
            搜索结果
        """
        print(f"\n{'='*70}")
        print(f"📚 自主学术论文搜索系统（多主题模式）")
        print(f"{'='*70}")
        print(f"🎯 基础方向: AI / LLM / RL / Agent")
        print(f"🤖 LLM 将自主生成多个搜索主题")
        print(f"{'='*70}\n")
        
        # 1. LLM 生成多个主题
        print("🤖 正在分析研究趋势，生成搜索主题...")
        topic_result = await self.generate_topic()
        
        if not topic_result["success"]:
            print(f"❌ 主题生成失败: {topic_result.get('error')}")
            # 使用默认主题
            topics = [
                {
                    "topic": "large language model reasoning",
                    "topic_zh": "大语言模型推理",
                    "reason": "默认主题（主题生成失败）",
                    "novelty_score": 7.0,
                    "keywords": ["LLM", "reasoning"]
                }
            ]
        else:
            topics = topic_result.get("topics", [])
        
        print(f"\n✨ LLM 生成了 {len(topics)} 个主题:")
        for i, topic_info in enumerate(topics, 1):
            print(f"\n{i}. {topic_info.get('topic')}")
            print(f"   中文: {topic_info.get('topic_zh', 'N/A')}")
            print(f"   新颖度: {topic_info.get('novelty_score', 0)}/10")
            print(f"   关键词: {', '.join(topic_info.get('keywords', [])[:5])}")
        
        # 2. 对每个主题执行搜索（限制迭代次数）
        all_papers = []
        seen_urls = set()  # 用于跨主题去重
        max_iterations_per_topic = max(5, self.max_iterations // len(topics))
        
        for i, topic_info in enumerate(topics, 1):
            topic = topic_info.get('topic')
            
            print(f"\n{'='*70}")
            print(f"🔍 主题 {i}/{len(topics)}: {topic}")
            print(f"{'='*70}")
            
            # 为每个主题重置候选池（每个主题只收集 1-2 篇）
            from utils.candidate_pool import CandidatePool
            self.candidate_pool = CandidatePool(
                min_papers=1,  # 每个主题最少 1 篇
                max_papers=2,  # 每个主题最多 2 篇
                min_quality_score=self.candidate_pool.min_quality_score
            )
            
            # 临时调整迭代次数
            original_max_iterations = self.max_iterations
            self.max_iterations = max_iterations_per_topic
            
            # 执行搜索
            result = await self.search_papers(topic)
            
            # 恢复原始迭代次数
            self.max_iterations = original_max_iterations
            
            # 收集论文并去重
            papers = result.get('papers', [])
            new_papers = 0
            for paper in papers:
                url = paper.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_papers.append(paper)
                    new_papers += 1
            
            print(f"✅ 主题 {i} 完成: 收集到 {len(papers)} 篇论文（{new_papers} 篇新论文）")
        
        # 3. 合并结果并重建最终候选池
        print(f"\n{'='*70}")
        print(f"📊 多主题搜索完成")
        print(f"{'='*70}")
        print(f"总共搜索了 {len(topics)} 个主题")
        print(f"收集到 {len(all_papers)} 篇去重后的论文")
        print(f"{'='*70}\n")
        
        # 重建候选池以包含所有论文
        from utils.candidate_pool import CandidatePool
        self.candidate_pool = CandidatePool(
            min_papers=len(all_papers),  # 允许容纳所有论文
            max_papers=max(len(all_papers), self.candidate_pool.max_papers),
            min_quality_score=self.candidate_pool.min_quality_score
        )
        self.candidate_pool.papers = all_papers
        
        result = {
            "topics": [t.get('topic') for t in topics],
            "papers": all_papers,
            "topic_count": len(topics)
        }
        
        return result
