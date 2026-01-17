"""
Stock Analysis Agent - 美股分析 Agent
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
from prompts.stock_prompts import (
    get_query_planning_prompt,
    get_decision_making_prompt,
    get_analysis_prompt,
    get_coarse_filtering_prompt
)
from utils.email_sender import EmailSender


class StockAnalysisAgent(BaseBrowserAgent):
    """美股分析 Agent"""
    
    # 财经信息搜索引擎配置
    SEARCH_ENGINES = [
        {
            "name": "Google Finance",
            "url": "https://www.google.com/search?q=",
            "advantages": "实时行情，新闻聚合"
        },
        {
            "name": "Yahoo Finance",
            "url": "https://finance.yahoo.com/quote/",
            "advantages": "详细财务数据，分析师评级"
        },
        {
            "name": "MarketWatch",
            "url": "https://www.marketwatch.com/search?q=",
            "advantages": "市场分析，专业评论"
        },
        {
            "name": "Seeking Alpha",
            "url": "https://seekingalpha.com/search?q=",
            "advantages": "投资者观点，深度分析"
        }
    ]
    
    # 专业财经网站直接访问配置
    DIRECT_SITES = [
        {
            "name": "Yahoo Finance Trending",
            "url": "https://finance.yahoo.com/trending-tickers",
            "type": "trending",
            "description": "实时热门股票榜单"
        },
        {
            "name": "Yahoo Finance Gainers",
            "url": "https://finance.yahoo.com/gainers",
            "type": "gainers",
            "description": "今日涨幅榜"
        },
        {
            "name": "Yahoo Finance Most Active",
            "url": "https://finance.yahoo.com/most-active",
            "type": "active",
            "description": "成交量最活跃股票"
        },
        {
            "name": "MarketWatch Market Data",
            "url": "https://www.marketwatch.com/tools/stockresearch/globalmarkets",
            "type": "market_data",
            "description": "全球市场数据"
        },
        {
            "name": "Finviz Screener",
            "url": "https://finviz.com/screener.ashx?v=111&o=-change",
            "type": "screener",
            "description": "股票筛选器（按涨幅排序）"
        },
        {
            "name": "Investing.com Top Stocks",
            "url": "https://www.investing.com/equities/trending-stocks",
            "type": "trending",
            "description": "热门股票"
        }
    ]
    
    def __init__(self, 
                 max_iterations: int = 20,
                 min_stocks: int = 3,
                 max_stocks: int = 5,
                 max_retries: int = 3,
                 proxy: str = None):
        """
        初始化股票分析 Agent
        
        Args:
            max_iterations: 最大迭代次数
            min_stocks: 最少股票数量
            max_stocks: 最多股票数量
            max_retries: 最大重试次数
            proxy: 代理服务器地址
        """
        super().__init__(max_iterations, max_retries)
        
        self.email_sender = EmailSender()
        self.min_stocks = min_stocks
        self.max_stocks = max_stocks
        self.query_history = []
        self.found_stocks = []
        self.stock_details = {}  # 存储股票详细信息
        self.proxy = proxy
        self.visited_sites = []  # 记录已访问的网站
    
    async def _goto_with_retry(self, page: Page, url: str, timeout: int = 30000, max_retries: int = 3) -> bool:
        """带重试的页面导航"""
        for attempt in range(max_retries):
            try:
                await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                return True
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    print(f"⚠️  导航失败 (尝试 {attempt + 1}/{max_retries}): {type(e).__name__}")
                    # 超时错误等待更长时间
                    if 'Timeout' in error_msg:
                        await asyncio.sleep(5)
                    else:
                        await asyncio.sleep(2)
                else:
                    print(f"❌ 导航失败，已重试 {max_retries} 次: {type(e).__name__}")
                    return False
        return False
    
    def build_search_url(self, engine_name: str, query: str) -> str:
        """构建搜索 URL"""
        for engine in self.SEARCH_ENGINES:
            if engine["name"] == engine_name:
                return f"{engine['url']}{quote(query)}"
        return f"{self.SEARCH_ENGINES[0]['url']}{quote(query)}"
    
    async def plan_next_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """使用 LLM 规划下一步操作"""
        system_prompt = get_decision_making_prompt(
            context, 
            self.SEARCH_ENGINES, 
            self.max_iterations,
            len(self.found_stocks),
            self.min_stocks
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请规划下一步操作"}
        ]
        
        result = await self.llm_client.call(messages, temperature=0.7)
        
        if result["success"]:
            content = result["content"]
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                decision = json.loads(content)
                return {"success": True, "decision": decision}
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"JSON 解析失败: {e}",
                    "raw_response": content
                }
        else:
            return {"success": False, "error": result["error"]}
    
    async def execute_action(self, 
                           page: Page, 
                           action: Dict[str, Any], 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 LLM 规划的操作"""
        action_type = action.get("action")
        params = action.get("params", {})
        
        print(f"\n📋 LLM 决策: {action.get('reason', action_type)}")
        
        # 先尝试执行通用操作
        result = await self._execute_common_action(page, action_type, params, context)
        if result is not None:
            return result
        
        # 股票特定操作
        try:
            if action_type == "extract_stocks":
                print("✅ 提取股票信息并完成搜索")
                return {"success": True, "action_taken": "extract_stocks", "done": True}
            
            elif action_type == "analyze_stock":
                stock_symbol = params.get("symbol", "")
                if stock_symbol:
                    print(f"📊 分析股票: {stock_symbol}")
                    # 搜索该股票的详细信息
                    search_url = self.build_search_url("Google Finance", f"{stock_symbol} stock today")
                    success = await self._goto_with_retry(page, search_url, timeout=30000)
                    if success:
                        return {"success": True, "action_taken": "analyze_stock"}
                    else:
                        return {"success": False, "error": "股票信息页面加载失败"}
                else:
                    return {"success": False, "error": "未提供股票代码"}
            
            else:
                return {"success": False, "error": f"未知操作类型: {action_type}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def extract_stock_info(self, html: str, page_url: str) -> List[Dict[str, Any]]:
        """从页面中提取股票信息（增强版，支持更多数据）"""
        soup = BeautifulSoup(html, 'html.parser')
        stocks = []
        
        # 尝试从表格中提取（Yahoo Finance, Finviz 等）
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # 跳过表头
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # 尝试提取股票代码
                    for cell in cells[:3]:  # 检查前3列
                        text = cell.get_text(strip=True)
                        # 匹配股票代码
                        if re.match(r'^[A-Z]{1,5}$', text):
                            stock_info = {
                                "symbol": text,
                                "source_url": page_url,
                                "found_time": datetime.now().isoformat(),
                                "extraction_method": "table"
                            }
                            
                            # 尝试提取价格和涨跌幅
                            try:
                                for i, c in enumerate(cells):
                                    c_text = c.get_text(strip=True)
                                    if '%' in c_text:
                                        stock_info['change_percent'] = c_text
                                    elif '$' in c_text or re.match(r'^\d+\.\d+$', c_text):
                                        if 'price' not in stock_info:
                                            stock_info['price'] = c_text
                            except:
                                pass
                            
                            if not any(s["symbol"] == text for s in stocks):
                                stocks.append(stock_info)
                                if len(stocks) >= 15:
                                    return stocks
        
        # 回退到文本匹配
        if not stocks:
            text = soup.get_text()
            stock_pattern = r'\b([A-Z]{1,5})\b'
            potential_symbols = re.findall(stock_pattern, text)
            
            exclude_words = {'THE', 'AND', 'FOR', 'ARE', 'NOT', 'BUT', 'CAN', 'YOU', 'ALL', 
                            'NEW', 'GET', 'HAS', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'USE',
                            'HER', 'TWO', 'WAY', 'HOW', 'OIL', 'MAY', 'ITS', 'SAY', 'SHE',
                            'HIM', 'HIS', 'HAD', 'SEE', 'NOW', 'TOP', 'BIG', 'WHY', 'LET',
                            'PUT', 'END', 'WHY', 'TRY', 'ASK', 'MAN', 'OLD', 'TOO', 'ANY',
                            'USA', 'CEO', 'CFO', 'IPO', 'ETF', 'SEC', 'FDA', 'API', 'URL',
                            'RSS', 'PDF', 'CSV', 'XML', 'HTML', 'HTTP', 'HTTPS', 'WWW'}
            
            for symbol in potential_symbols:
                if symbol not in exclude_words and len(symbol) <= 5:
                    stock_info = {
                        "symbol": symbol,
                        "source_url": page_url,
                        "found_time": datetime.now().isoformat(),
                        "extraction_method": "text"
                    }
                    
                    if not any(s["symbol"] == symbol for s in stocks):
                        stocks.append(stock_info)
        
        return stocks[:40]  # 最多返回40个
    
    async def research_stock_details(self, page: Page, stock: Dict[str, Any]) -> Dict[str, Any]:
        """深度调研单个股票的详细信息"""
        symbol = stock['symbol']
        print(f"\n🔍 深度调研: {symbol}")
        
        details = {
            "symbol": symbol,
            "news": [],
            "price_info": {},
            "company_info": "",
            "analyst_rating": ""
        }
        
        # 1. 访问 Yahoo Finance 个股页面
        yahoo_url = f"https://finance.yahoo.com/quote/{symbol}"
        print(f"   访问: {yahoo_url}")
        
        success = await self._goto_with_retry(page, yahoo_url, timeout=45000)  # 增加超时
        if success:
            await asyncio.sleep(3)
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取价格信息
            text = soup.get_text()
            
            # 提取公司信息
            company_section = soup.find('section', {'data-testid': 'quote-profile'})
            if company_section:
                details['company_info'] = company_section.get_text(strip=True)[:500]
            
            # 提取关键数据
            details['page_content'] = text[:2000]
        
        # 2. 搜索最新新闻 - 使用搜索引擎而不是直接访问新闻页
        print(f"   搜索新闻: {symbol} stock news")
        
        # 尝试从主页提取新闻
        if success:
            # 在主页上查找新闻链接
            news_links = soup.find_all('a', href=True, limit=10)
            for link in news_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                # 查找包含 news 或 story 的链接
                if ('news' in href or 'story' in href) and len(text) > 20:
                    if text not in details['news']:
                        details['news'].append(text)
                        if len(details['news']) >= 5:
                            break
        
        # 如果主页没有足够新闻，尝试访问新闻页
        if len(details['news']) < 3:
            news_url = f"https://finance.yahoo.com/quote/{symbol}/news"
            print(f"   访问新闻页: {news_url}")
            
            success = await self._goto_with_retry(page, news_url, timeout=45000, max_retries=2)
            if success:
                await asyncio.sleep(3)
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 更精确的新闻提取 - 查找文章标题
                # 方法1: 查找包含新闻的 div
                news_items = soup.find_all(['h3', 'h2'], limit=20)
                for item in news_items:
                    title = item.get_text(strip=True)
                    # 过滤掉导航栏和短标题
                    if title and len(title) > 20 and title not in ['News', 'Life', 'Entertainment', 'Finance', 'Sports']:
                        if title not in details['news']:
                            details['news'].append(title)
                            if len(details['news']) >= 5:
                                break
        
        print(f"   ✅ 收集到 {len(details['news'])} 条新闻")
        
        return details
    
    async def coarse_filter_with_llm(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用 LLM 粗筛选股票"""
        print(f"🤖 LLM 正在进行粗筛选 (从 {len(stocks)} 只中选出20只)...")
        
        prompt = get_coarse_filtering_prompt(stocks)
        messages = [{"role": "user", "content": prompt}]
        result = await self.llm_client.call(messages, temperature=0.3, max_tokens=1000)
        
        if result["success"]:
            content = result["content"]
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                selection = json.loads(content)
                selected_symbols = selection.get("selected_stocks", [])
                
                if selected_symbols:
                    print(f"✅ LLM 筛选出 {len(selected_symbols)} 只股票: {', '.join(selected_symbols)}")
                    # 按LLM返回的顺序过滤
                    filtered_stocks = [s for symbol in selected_symbols for s in stocks if s['symbol'] == symbol]
                    return filtered_stocks
                    
            except json.JSONDecodeError as e:
                print(f"   ⚠️  粗筛选JSON解析失败: {e}")
        else:
            print(f"   ⚠️  粗筛选LLM调用失败: {result.get('error')}")

        # Fallback: 如果LLM失败，则按涨跌幅选择前20
        print("⚠️  LLM粗筛选失败，将按涨跌幅选择前20只")
        return stocks[:20]
    
    async def deep_analysis_with_llm(self, stock_details: Dict[str, Any]) -> Dict[str, Any]:
        """使用 LLM 对单个股票进行深度分析"""
        symbol = stock_details['symbol']
        
        news_list = stock_details.get('news', [])[:5]
        news_text = "".join([f"- {news}\n" for news in news_list])
        page_content = stock_details.get('page_content', 'N/A')[:1500]
        
        prompt = f"""你是一位资深的美股分析师，请对以下股票进行深入、专业的分析，需要同时覆盖技术面和基本面。

**股票代码: {symbol}**

**最新新闻:**
{news_text if news_text else "无"}

**页面信息摘要:**
{page_content}

**分析要求:**

请基于以上信息，结合你对该公司的知识，提供以下两方面的分析：

1.  **基本面分析 (Fundamental Analysis):**
    *   **公司背景**: 核心业务、行业地位及护城河。
    *   **财务状况**: 基于常识判断其营收、利润、现金流的健康状况。
    *   **增长催化剂**: 未来可能驱动增长的关键因素。
    *   **主要风险**: 公司面临的核心风险点。

2.  **技术面分析 (Technical Analysis):**
    *   **当前趋势**: 处于上升、下降还是盘整趋势？
    *   **关键价位**: 分析关键的支撑位和阻力位。
    *   **量价关系**: 成交量是否配合价格走势？
    *   **技术指标**: （基于常识推断）RSI、MACD等指标可能处于什么状态？

**输出结果:**

请严格按照以下 JSON 格式返回，确保所有字段都存在：
{{
    "symbol": "{symbol}",
    "company_name": "公司名称",
    "fundamental_analysis": {{
        "background": "公司背景和核心业务分析 (100字内)",
        "financial_health": "财务健康状况评估 (80字内)",
        "catalysts": ["增长催化剂1", "增长催化剂2"],
        "risks": ["主要风险1", "主要风险2"]
    }},
    "technical_analysis": {{
        "trend": "当前趋势判断 (例如: '处于周线级别上升趋势中的日线级别盘整')",
        "support_levels": ["支撑位1", "支撑位2"],
        "resistance_levels": ["阻力位1", "阻力位2"],
        "volume_analysis": "量价关系分析 (50字内)"
    }},
    "investment_summary": {{
        "overall_score": 8.5,
        "recommendation": "买入/持有/观望/卖出",
        "time_horizon": "短期/中期/长期",
        "conclusion": "综合投资建议 (150字内)"
    }}
}}
"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.llm_client.call(messages, temperature=0.2, max_tokens=2500)
        
        if result["success"]:
            content = result["content"]
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                analysis = json.loads(content)
                # 确保 symbol 字段存在
                analysis['symbol'] = symbol
                return analysis
            except json.JSONDecodeError as e:
                print(f"   ⚠️  深度分析JSON解析失败: {e}")
                return {
                    "symbol": symbol,
                    "error": "JSON 解析失败",
                    "raw_content": content[:500]
                }
        else:
            return {
                "symbol": symbol,
                "error": result.get('error')
            }
    
    async def select_top_stocks_with_llm(self, analyzed_stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """使用 LLM 从分析过的股票中选出最佳的5只"""
        
        stocks_summary = "\n\n".join([
            f"**{i+1}. {s.get('symbol')} - {s.get('company_name', 'N/A')}**\n"
            f"  评分: {s.get('investment_summary', {}).get('overall_score', 0)}/10\n"
            f"  推荐: {s.get('investment_summary', {}).get('recommendation', 'N/A')}\n"
            f"  背景: {s.get('fundamental_analysis', {}).get('background', 'N/A')}\n"
            f"  催化剂: {', '.join(s.get('fundamental_analysis', {}).get('catalysts', []))}"
            for i, s in enumerate(analyzed_stocks)
        ])
        
        prompt = f"""你是一位资深的投资组合管理人，请从以下已分析的股票中选出今晚最值得投资的5只：

{stocks_summary}

请基于以下维度进行综合评估：
1. **综合评分**: LLM给出的投资分数。
2.  **基本面**: 公司质量、增长前景和风险。
3.  **技术面**: 当前趋势和关键价位。
4.  **催化剂**: 近期事件驱动的可能性。
5.  **投资组合**: 确保选出的股票具有一定的多样性。

请选出5只股票，并提供：
- 市场整体分析（100字内）
- 投资策略建议（150字内）
- 风险警告（100字内）

以 JSON 格式返回：
{{
    "market_overview": "市场整体分析",
    "top_stocks": [
        {{
            "rank": 1,
            "symbol": "股票代码",
            "selection_reason": "选择该股的核心理由（80字内）"
        }},
        {{
            "rank": 2,
            "symbol": "股票代码",
            "selection_reason": "选择该股的核心理由（80字内）"
        }},
        {{
            "rank": 3,
            "symbol": "股票代码",
            "selection_reason": "选择该股的核心理由（80字内）"
        }},
        {{
            "rank": 4,
            "symbol": "股票代码",
            "selection_reason": "选择该股的核心理由（80字内）"
        }},
        {{
            "rank": 5,
            "symbol": "股票代码",
            "selection_reason": "选择该股的核心理由（80字内）"
        }}
    ],
    "investment_strategy": "投资策略",
    "risk_warning": "风险警告"
}}
"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.llm_client.call(messages, temperature=0.3, max_tokens=2000)
        
        if result["success"]:
            content = result["content"]
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                selection = json.loads(content)
                
                # 合并详细分析
                top_stocks_full = []
                for top in selection.get('top_stocks', []):
                    symbol = top.get('symbol')
                    # 从 analyzed_stocks 中找到对应的详细分析
                    full_analysis = next((s for s in analyzed_stocks if s.get('symbol') == symbol), None)
                    if full_analysis:
                        full_analysis['rank'] = top.get('rank')
                        full_analysis['selection_reason'] = top.get('selection_reason')
                        top_stocks_full.append(full_analysis)
                
                # 如果LLM返回的股票数量不足5个，从备选中补充
                if len(top_stocks_full) < 5:
                    backup_symbols = [s['symbol'] for s in top_stocks_full]
                    remaining_stocks = [s for s in analyzed_stocks if s['symbol'] not in backup_symbols]
                    top_stocks_full.extend(remaining_stocks[:5 - len(top_stocks_full)])

                return {
                    "market_overview": selection.get('market_overview'),
                    "top_stocks": top_stocks_full,
                    "investment_strategy": selection.get('investment_strategy'),
                    "risk_warning": selection.get('risk_warning')
                }
            except json.JSONDecodeError as e:
                print(f"\n⚠️  选股 JSON 解析失败: {e}")
        
        # Fallback
        print("⚠️  LLM选股失败或返回格式错误，将按评分选择前5只")
        top_five = sorted(analyzed_stocks, key=lambda s: s.get('investment_summary', {}).get('overall_score', 0), reverse=True)[:5]
        return {
            "market_overview": "LLM 调用失败或解析错误",
            "top_stocks": top_five,
            "investment_strategy": "请基于列表手动分析",
            "risk_warning": "由于LLM处理失败，该列表仅基于初步评分生成，未经最终筛选。"
        }
    
    async def visit_direct_site(self, page: Page, site: Dict[str, str]) -> List[Dict[str, Any]]:
        """直接访问专业财经网站获取数据"""
        print(f"\n🌐 访问: {site['name']}")
        print(f"   URL: {site['url']}")
        print(f"   类型: {site['description']}")
        
        success = await self._goto_with_retry(page, site['url'], timeout=30000)
        
        if not success:
            print(f"❌ 访问失败: {site['name']}")
            return []
        
        # 等待页面加载
        await asyncio.sleep(4)
        
        # 提取股票信息
        html = await page.content()
        stocks = self.extract_stock_info(html, page.url)
        
        # 标记来源
        for stock in stocks:
            stock['source_site'] = site['name']
            stock['source_type'] = site['type']
        
        print(f"✅ 提取到 {len(stocks)} 只股票")
        
        self.visited_sites.append(site['name'])
        return stocks
    
    async def intelligent_browse(self, page: Page, max_sites: int = 8) -> List[Dict[str, Any]]:
        """智能浏览策略：优先访问最有价值的财经网站"""
        print(f"\n{'='*70}")
        print(f"🎯 智能浏览策略：直接访问专业财经网站")
        print(f"{'='*70}\n")
        
        all_stocks = []
        
        # 优先访问的网站顺序
        priority_sites = [
            site for site in self.DIRECT_SITES 
            if site['type'] in ['trending', 'gainers', 'active']
        ]
        
        visited_count = 0
        for site in priority_sites:
            if visited_count >= max_sites:
                break
            
            stocks = await self.visit_direct_site(page, site)
            
            for stock in stocks:
                # 去重
                if not any(s['symbol'] == stock['symbol'] for s in all_stocks):
                    all_stocks.append(stock)
            
            visited_count += 1
            
            # 如果已经找到足够的股票，提前结束
            if len(all_stocks) >= 200:
                print(f"\n✅ 已收集足够股票 ({len(all_stocks)} 只)，停止浏览")
                break
            
            await asyncio.sleep(2)
        
        return all_stocks
    
    async def search_stocks(self, 
                          keywords: List[str] = None, 
                          use_direct_sites: bool = True,
                          use_search_engines: bool = False) -> Dict[str, Any]:
        """
        搜索并分析美股
        
        Args:
            keywords: 搜索关键词（用于搜索引擎）
            use_direct_sites: 是否直接访问专业财经网站
            use_search_engines: 是否使用搜索引擎
        """
        if keywords is None:
            keywords = [
                "best US stocks today",
                "top performing stocks now",
                "stocks to buy today"
            ]
        
        print(f"\n{'='*70}")
        print(f"📈 开始美股分析")
        print(f"🎯 阶段1: 数据收集")
        if use_direct_sites:
            print(f"   策略: 直接访问专业财经网站")
        if use_search_engines:
            print(f"   策略: 搜索引擎 - {', '.join(keywords)}")
        print(f"{'='*70}\n")
        
        detailed_stocks = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # --- 数据收集 ---
            try:
                if use_direct_sites:
                    direct_stocks = await self.intelligent_browse(page)
                    for stock in direct_stocks:
                        if not any(s['symbol'] == stock['symbol'] for s in self.found_stocks):
                            self.found_stocks.append(stock)
                
                if use_search_engines and len(self.found_stocks) < 200: # Changed from 100 to 200
                    print(f"\n{'─'*70}\n🔍 补充搜索：使用搜索引擎\n{'─'*70}")
                    for keyword in keywords:
                        if len(self.found_stocks) >= 200: break # Changed from 120 to 200
                        print(f"\n🔍 搜索: {keyword}")
                        search_url = self.build_search_url("Google Finance", keyword)
                        if await self._goto_with_retry(page, search_url, timeout=60000, max_retries=3):
                            await asyncio.sleep(3)
                            html = await page.content()
                            stocks = self.extract_stock_info(html, page.url)
                            print(f"📊 找到 {len(stocks)} 个潜在股票代码")
                            for stock in stocks:
                                if not any(s['symbol'] == stock['symbol'] for s in self.found_stocks):
                                    self.found_stocks.append(stock)
                            await asyncio.sleep(2)
                        else:
                            print(f"❌ 搜索失败: {keyword}")

            finally:
                print(f"\n{'='*70}")
                print(f"📊 数据收集完成")
                print(f"   总共找到: {len(self.found_stocks)} 只备选股票")
                print(f"   访问网站: {len(self.visited_sites)} 个 ({', '.join(self.visited_sites)})")
                print(f"{'='*70}\n")

            # --- 粗筛选 ---
            print(f"\n{'='*70}")
            print(f"🔬 阶段2: 粗筛选 (从 {len(self.found_stocks)} 只中选出 Top 20)")
            print(f"{'='*70}\n")
            
            top_candidates = sorted(
                self.found_stocks, 
                key=lambda x: float(x.get('change_percent', '0').replace('%', '').replace('+', '')),
                reverse=True
            )[:200] # Changed from 100 to 200
            screened_candidates = await self.coarse_filter_with_llm(top_candidates)

            # --- 深度调研 ---
            print(f"\n{'='*70}")
            print(f"🔬 阶段3: 深度调研 (分析 Top 20)")
            print(f"{'='*70}\n")
            
            for i, stock in enumerate(screened_candidates, 1):
                print(f"{'─'*70}\n[{i}/{len(screened_candidates)}] 调研: {stock['symbol']}\n{'─'*70}")
                details = await self.research_stock_details(page, stock)
                
                print(f"   🤖 LLM 深度分析中...")
                analysis = await self.deep_analysis_with_llm(details)
                
                if 'error' not in analysis:
                    detailed_stocks.append(analysis)
                    summary = analysis.get('investment_summary', {})
                    print(f"   ✅ 分析完成: {analysis.get('company_name', 'N/A')}")
                    print(f"      评分: {summary.get('overall_score', 0)}/10 | 推荐: {summary.get('recommendation', 'N/A')}")
                else:
                    print(f"   ⚠️  分析失败: {analysis.get('error')}")
                await asyncio.sleep(1) # 避免请求过快
            
            await browser.close()

        print(f"\n{'='*70}")
        print(f"✅ 深度调研完成，成功分析 {len(detailed_stocks)} 只股票")
        print(f"{'='*70}\n")
        
        # --- 智能选股 ---
        final_selection = {}
        if detailed_stocks:
            print(f"\n{'='*70}")
            print(f"🎯 阶段4: 智能选股 (从 {len(detailed_stocks)} 只中选出最佳3只)")
            print(f"{'='*70}\n")
            print("🤖 LLM 正在进行最终综合评估...")
            final_selection = await self.select_top_stocks_with_llm(detailed_stocks)
            print(f"✅ 选股完成! 推荐股票: {len(final_selection.get('top_stocks', []))} 只")
        else:
            print("⚠️  没有成功分析的股票，无法进行最终选股。")
            final_selection = {
                "market_overview": "数据收集或分析失败",
                "top_stocks": [],
                "investment_strategy": "建议检查日志并重新运行分析",
                "risk_warning": "分析数据不完整，无最终推荐。"
            }
        
        return {
            "all_stocks": self.found_stocks,
            "detailed_analysis": detailed_stocks,
            "analysis": final_selection,
            "search_time": datetime.now().isoformat(),
            "visited_sites": self.visited_sites
        }
