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
            "key_statistics": {},
            "analyst_rating": ""
        }
        
        # 1. 访问 Yahoo Finance 个股页面
        yahoo_url = f"https://finance.yahoo.com/quote/{symbol}"
        print(f"   访问: {yahoo_url}")
        
        success = await self._goto_with_retry(page, yahoo_url, timeout=45000)
        if success:
            await asyncio.sleep(3)
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取公司信息
            company_section = soup.find('section', {'data-testid': 'quote-profile'})
            if company_section:
                details['company_info'] = company_section.get_text(strip=True)[:800]
            
            # 提取当前价格
            # 优先使用 data-testid="qsp-price" (Yahoo Finance 新版)
            price_element = soup.select_one('[data-testid="qsp-price"]')
            if price_element:
                details['current_price'] = price_element.get_text(strip=True)
            else:
                # 备选: fin-streamer (注意: 可能有多个，需要找对 context)
                # 查找位于 quote-header 或 price section 内的 fin-streamer
                price_element = soup.select_one('fin-streamer[data-field="regularMarketPrice"][data-symbol="{}"]'.format(symbol))
                if not price_element:
                     price_element = soup.select_one('fin-streamer[data-field="regularMarketPrice"]')
                
                if price_element:
                    details['current_price'] = price_element.get_text(strip=True)

            # 提取关键统计数据 (Key Statistics)
            # Yahoo Finance 新版使用 ul/li 结构
            # 查找包含特定 title 的 span，然后找其后的 value
            
            key_map = {
                'Previous Close': 'previous_close',
                'Open': 'open',
                'Day\'s Range': 'day_range',
                '52 Week Range': 'year_range',
                'Volume': 'volume',
                'Avg. Volume': 'avg_volume',
                'Market Cap': 'market_cap',
                'Beta (5Y Monthly)': 'beta',
                'PE Ratio (TTM)': 'pe_ratio',
                'EPS (TTM)': 'eps',
                'Forward Dividend & Yield': 'dividend',
                'Ex-Dividend Date': 'ex_dividend_date',
                '1y Target Est': 'target_est'
            }

            # 查找所有的 li 元素，然后尝试从中提取标签和值
            # 这种方法更通用，不依赖特定的 class
            list_items = soup.find_all('li')
            for li in list_items:
                # 尝试找到 label 和 value
                # 通常 label 在一个 span 或 div 中，value 在另一个
                texts = list(li.stripped_strings)
                if len(texts) >= 2:
                    label_text = texts[0]
                    value_text = texts[1]
                    
                    # 检查 label 是否是我们需要的
                    for k, v in key_map.items():
                        if k in label_text:
                            # 有时候 value 会包含一些额外信息，只取第一个主要部分
                            details['key_statistics'][v] = value_text.split(' ')[0] if ' ' in value_text and v != 'day_range' and v != 'year_range' else value_text
                            break
            
            # 如果没找到 current_price，用 previous_close 兜底
            if 'current_price' not in details and 'previous_close' in details['key_statistics']:
                details['current_price'] = details['key_statistics']['previous_close']

            # 备用方案：通过 title 属性查找 (针对新版 Yahoo)
            if not details['key_statistics']:
                 for k, v in key_map.items():
                    element = soup.find(attrs={"title": k})
                    if element:
                        # 找到 title 对应的 label 元素后，尝试找它的父级 li，再找 value
                        parent_li = element.find_parent('li')
                        if parent_li:
                            value_element = parent_li.find(class_="value")
                            if value_element:
                                details['key_statistics'][v] = value_element.get_text(strip=True)
            
            print(f"   📊 价格: {details.get('current_price', 'N/A')} | 目标价: {details['key_statistics'].get('target_est', 'N/A')}")
            
            # 提取页面文本作为补充
            details['page_content'] = soup.get_text()[:3000]
        
        # 2. 搜索最新新闻
        print(f"   搜索新闻: {symbol} stock news")
        
        # 尝试访问专门的新闻页
        news_url = f"https://finance.yahoo.com/quote/{symbol}/news"
        print(f"   访问新闻页: {news_url}")
        
        success = await self._goto_with_retry(page, news_url, timeout=45000, max_retries=2)
        if success:
            await asyncio.sleep(3)
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            news_items = soup.find_all(['h3', 'h2'], limit=30)
            for item in news_items:
                title = item.get_text(strip=True)
                if title and len(title) > 20 and title not in ['News', 'Life', 'Entertainment', 'Finance', 'Sports', 'Videos']:
                    if title not in details['news']:
                        details['news'].append(title)
                        if len(details['news']) >= 15: # 增加到 15 条
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
    
    async def _analyze_fundamentals(self, symbol: str, stock_details: Dict[str, Any]) -> Dict[str, Any]:
        """专门进行基本面分析"""
        print(f"   📘 [{symbol}] 正在进行基本面分析...")
        
        news_list = stock_details.get('news', [])
        news_text = "\n".join([f"- {news}" for news in news_list])
        
        stats = stock_details.get('key_statistics', {})
        stats_text = "\n".join([f"- {k}: {v}" for k, v in stats.items()])
        stats_text += f"\n- Current Price: {stock_details.get('current_price', 'N/A')}"
        
        company_info = stock_details.get('company_info', 'N/A')
        
        prompt = f"""你是一位顶级美股基本面分析师 (Fundamental Analyst)。请对 {symbol} 进行深入的基本面分析。

**公司资料:**
{company_info}

**关键财务指标:**
{stats_text}

**近期新闻与舆情:**
{news_text}

请分析以下维度:
1.  **商业模式与护城河**: 公司的核心竞争力是什么？
2.  **财务健康度**: 基于 PE, EPS, 市值等数据评估。
3.  **增长驱动力**: 近期新闻中提到的新产品、新市场或战略合作。
4.  **宏观与行业环境**: 当前环境对该公司的影响。
5.  **风险因素**: 监管、竞争或执行风险。

请返回 JSON 格式:
{{
    "background": "公司核心业务简述 (50字)",
    "financial_health": "财务状况评估 (100字)",
    "catalysts": ["增长催化剂1", "增长催化剂2", "增长催化剂3"],
    "risks": ["主要风险1", "主要风险2"],
    "fundamental_score": 8.0,
    "summary": "基本面综合评价 (100字)"
}}
"""
        messages = [{"role": "user", "content": prompt}]
        result = await self.llm_client.call(messages, temperature=0.3, max_tokens=1500)
        
        try:
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception as e:
            print(f"   ⚠️  基本面分析解析失败: {e}")
            return {"fundamental_score": 0, "summary": "分析失败"}

    async def _analyze_technicals(self, symbol: str, stock_details: Dict[str, Any]) -> Dict[str, Any]:
        """专门进行技术面分析"""
        print(f"   📈 [{symbol}] 正在进行技术面分析...")
        
        stats = stock_details.get('key_statistics', {})
        price_info = f"""
        - 当前价格: {stock_details.get('current_price', 'N/A')}
        - 昨收/开盘: {stats.get('previous_close')} / {stats.get('open')}
        - 日内范围: {stats.get('day_range')}
        - 52周范围: {stats.get('year_range')}
        - 成交量: {stats.get('volume')} (平均: {stats.get('avg_volume')})
        - 1年目标价: {stats.get('target_est')}
        """
        
        # 尝试从 page_content 中提取更多即时价格行为描述（如果有）
        page_snippet = stock_details.get('page_content', '')[:1000]
        
        prompt = f"""你是一位顶级美股技术面分析师 (Technical Analyst)。请对 {symbol} 进行深入的技术面分析。

**市场数据:**
{price_info}

**页面摘要 (辅助判断):**
{page_snippet}

请分析以下维度:
1.  **趋势识别**: 结合 52周范围 和 当前价格，判断长期和中期趋势。
2.  **支撑与阻力**: 基于日内范围和历史数据估算关键位。
3.  **量价分析**: 成交量是否异常？是否存在量价背离？
4.  **波动性**: 基于 Beta 和近期范围评估。
5.  **目标价潜力**: 对比当前价格与 1年目标价。

请返回 JSON 格式:
{{
    "trend": "当前趋势判断 (例如: 上升/下降/盘整)",
    "support_levels": ["支撑位1", "支撑位2"],
    "resistance_levels": ["阻力位1", "阻力位2"],
    "volume_analysis": "量价分析 (50字)",
    "technical_score": 7.5,
    "summary": "技术面综合评价 (100字)"
}}
"""
        messages = [{"role": "user", "content": prompt}]
        result = await self.llm_client.call(messages, temperature=0.3, max_tokens=1500)
        
        try:
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception as e:
            print(f"   ⚠️  技术面分析解析失败: {e}")
            return {"technical_score": 0, "summary": "分析失败"}

    async def deep_analysis_with_llm(self, stock_details: Dict[str, Any]) -> Dict[str, Any]:
        """使用 LLM 对单个股票进行深度分析 (分步进行)"""
        symbol = stock_details['symbol']
        
        # 1. 基本面分析
        fundamental = await self._analyze_fundamentals(symbol, stock_details)
        
        # 2. 技术面分析
        technical = await self._analyze_technicals(symbol, stock_details)
        
        # 3. 综合评分与建议
        f_score = float(fundamental.get('fundamental_score', 0))
        t_score = float(technical.get('technical_score', 0))
        
        # 简单加权: 基本面 60%, 技术面 40% (或者 50/50，视偏好而定)
        overall_score = round(f_score * 0.6 + t_score * 0.4, 1)
        
        recommendation = "观望"
        if overall_score >= 8.5:
            recommendation = "强力买入"
        elif overall_score >= 7.5:
            recommendation = "买入"
        elif overall_score >= 6.0:
            recommendation = "持有"
        elif overall_score < 4.0:
            recommendation = "卖出"

        # 构造符合原有结构的返回结果
        analysis = {
            "symbol": symbol,
            "company_name": stock_details.get('symbol'), # 暂时用 symbol 代替
            "current_price": stock_details.get('current_price', 'N/A'),
            "target_price": stock_details.get('key_statistics', {}).get('target_est', 'N/A'),
            "fundamental_analysis": fundamental,
            "technical_analysis": technical,
            "investment_summary": {
                "overall_score": overall_score,
                "recommendation": recommendation,
                "time_horizon": "中长期" if f_score > t_score else "短期",
                "conclusion": f"基本面评分 {f_score}, 技术面评分 {t_score}。{fundamental.get('summary')} {technical.get('summary')}"
            }
        }
        
        return analysis
    
    async def select_top_stocks_with_llm(self, analyzed_stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成市场概览并对所有股票进行排序返回 (不再仅选Top 5)
        """
        
        # 按评分排序
        sorted_stocks = sorted(
            analyzed_stocks, 
            key=lambda s: s.get('investment_summary', {}).get('overall_score', 0), 
            reverse=True
        )
        
        # 为每只股票添加排名
        for i, stock in enumerate(sorted_stocks, 1):
            stock['rank'] = i
            # 如果没有 selection_reason，使用 conclusion 填充
            if 'selection_reason' not in stock:
                stock['selection_reason'] = stock.get('investment_summary', {}).get('conclusion', '')

        # 只把 Top 10 的简要信息发给 LLM 生成市场概览，避免 Context 过长
        top_10_summary = "\n\n".join([
            f"**{s.get('symbol')}**\n"
            f"  评分: {s.get('investment_summary', {}).get('overall_score', 0)}/10\n"
            f"  推荐: {s.get('investment_summary', {}).get('recommendation', 'N/A')}\n"
            f"  结论: {s.get('investment_summary', {}).get('conclusion', 'N/A')}"
            for s in sorted_stocks[:10]
        ])
        
        prompt = f"""你是一位资深的投资组合管理人。请基于以下分析过的热门股票（展示前10名），撰写一份简短的市场概览和投资策略。

{top_10_summary}

请提供：
1. **市场整体分析**: 观察这些股票的整体表现，总结当前市场情绪（100字内）。
2. **投资策略建议**: 基于这些股票的评级分布，给出操作建议（150字内）。
3. **风险警告**: 提示当前市场的核心风险（100字内）。

以 JSON 格式返回：
{{
    "market_overview": "市场整体分析...",
    "investment_strategy": "投资策略...",
    "risk_warning": "风险警告..."
}}
"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.llm_client.call(messages, temperature=0.3, max_tokens=1000)
        
        market_overview = "分析完成"
        investment_strategy = "请参考个股评级"
        risk_warning = "股市有风险，投资需谨慎"

        if result["success"]:
            content = result["content"]
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                selection = json.loads(content)
                market_overview = selection.get('market_overview', market_overview)
                investment_strategy = selection.get('investment_strategy', investment_strategy)
                risk_warning = selection.get('risk_warning', risk_warning)
                
            except json.JSONDecodeError as e:
                print(f"\n⚠️  概览 JSON 解析失败: {e}")
        
        return {
            "market_overview": market_overview,
            "top_stocks": sorted_stocks, # 返回所有股票
            "investment_strategy": investment_strategy,
            "risk_warning": risk_warning
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
                          use_search_engines: bool = False,
                          fixed_symbols: List[str] = None) -> Dict[str, Any]:
        """
        搜索并分析美股
        
        Args:
            keywords: 搜索关键词（用于搜索引擎）
            use_direct_sites: 是否直接访问专业财经网站
            use_search_engines: 是否使用搜索引擎
            fixed_symbols: 指定分析的股票代码列表
        """
        if keywords is None:
            keywords = [
                "best US stocks today",
                "top performing stocks now",
                "stocks to buy today"
            ]
        
        print(f"\n{'='*70}")
        print(f"📈 开始美股分析")
        
        detailed_stocks = []
        screened_candidates = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            if fixed_symbols:
                print(f"🎯 模式: 固定关注列表分析")
                print(f"   关注列表: {', '.join(fixed_symbols)}")
                print(f"{'='*70}\n")
                
                # 直接构造候选列表
                for symbol in fixed_symbols:
                    screened_candidates.append({
                        "symbol": symbol,
                        "source_url": "User Watchlist",
                        "found_time": datetime.now().isoformat()
                    })
                
                # 更新 found_stocks 以便记录
                self.found_stocks = screened_candidates
                
            else:
                print(f"🎯 阶段1: 数据收集")
                if use_direct_sites:
                    print(f"   策略: 直接访问专业财经网站")
                if use_search_engines:
                    print(f"   策略: 搜索引擎 - {', '.join(keywords)}")
                print(f"{'='*70}\n")
                
                # --- 数据收集 ---
                try:
                    if use_direct_sites:
                        direct_stocks = await self.intelligent_browse(page)
                        for stock in direct_stocks:
                            if not any(s['symbol'] == stock['symbol'] for s in self.found_stocks):
                                self.found_stocks.append(stock)
                    
                    if use_search_engines and len(self.found_stocks) < 200: 
                        print(f"\n{'─'*70}\n🔍 补充搜索：使用搜索引擎\n{'─'*70}")
                        for keyword in keywords:
                            if len(self.found_stocks) >= 200: break 
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
                print(f"🔬 阶段2: 粗筛选 (从 {len(self.found_stocks)} 只中选出最有潜力的股票)...")
                print(f"{'='*70}\n")
                
                top_candidates = sorted(
                    self.found_stocks, 
                    key=lambda x: float(x.get('change_percent', '0').replace('%', '').replace('+', '')),
                    reverse=True
                )[:200]
                screened_candidates = await self.coarse_filter_with_llm(top_candidates)

            # --- 深度调研 ---
            print(f"\n{'='*70}")
            if fixed_symbols:
                print(f"🔬 阶段: 深度调研 (分析关注列表)")
            else:
                print(f"🔬 阶段: 深度调研")
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
        
        # --- 智能分析报告 ---
        final_selection = {}
        if detailed_stocks:
            print(f"\n{'='*70}")
            print(f"🎯 阶段: 智能分析报告汇总")
            print(f"{'='*70}\n")
            print("🤖 LLM 正在进行最终综合评估...")
            final_selection = await self.select_top_stocks_with_llm(detailed_stocks)
            print(f"✅ 报告生成完成! 共分析 {len(final_selection.get('top_stocks', []))} 只股票")
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
