"""
Stock Analysis Prompts - 股票分析提示词
"""

from typing import List, Dict, Any


def get_query_planning_prompt(topic: str, search_engines: List[Dict[str, str]]) -> str:
    """生成查询规划提示词"""
    engines_info = "\n".join([
        f"- {e['name']}: {e['advantages']}" 
        for e in search_engines
    ])
    
    return f"""你是一位专业的美股投资分析师，需要规划如何搜索今晚最有投资价值的美股。

搜索主题: {topic}

可用搜索引擎:
{engines_info}

请规划最优的搜索策略，包括:
1. 选择最合适的搜索引擎
2. 设计精准的搜索关键词
3. 考虑如何获取实时行情和最新资讯

以 JSON 格式返回:
{{
    "engine": "搜索引擎名称",
    "query": "搜索关键词",
    "reason": "选择理由"
}}"""


def get_decision_making_prompt(
    context: Dict[str, Any],
    search_engines: List[Dict[str, str]],
    max_iterations: int,
    found_stocks_count: int,
    min_stocks: int
) -> str:
    """生成决策提示词"""
    
    current_url = context.get("current_url", "")
    page_content = context.get("page_content", "")[:2000]
    links = context.get("links", [])
    iteration = context.get("iteration", 0)
    
    engines_info = "\n".join([
        f"- {e['name']}: {e['advantages']}" 
        for e in search_engines
    ])
    
    links_info = "\n".join([
        f"{i+1}. {link['text'][:80]} -> {link['url'][:100]}"
        for i, link in enumerate(links[:10])
    ])
    
    return f"""你是一位专业的美股投资分析师，正在搜索今晚最有投资价值的美股。

当前状态:
- 当前 URL: {current_url}
- 迭代次数: {iteration}/{max_iterations}
- 已找到股票: {found_stocks_count} 只 (目标: 至少 {min_stocks} 只)

页面内容摘要:
{page_content}

可点击链接:
{links_info}

可用搜索引擎:
{engines_info}

可用操作:
1. click_link - 点击链接查看详情
   参数: {{"link_index": 链接序号}}

2. search - 执行新搜索
   参数: {{"query": "搜索词", "engine_index": 引擎索引}}

3. scroll - 向下滚动查看更多内容

4. back - 返回上一页

5. extract_stocks - 提取当前页面的股票信息并完成搜索

6. stop - 停止搜索

请分析当前情况，决定下一步操作。重点关注:
- 实时股价和涨跌幅
- 最新财经新闻和市场动态
- 分析师评级和目标价
- 交易量和市场情绪

以 JSON 格式返回:
{{
    "action": "操作类型",
    "params": {{"参数名": "参数值"}},
    "reason": "决策理由"
}}"""


def get_analysis_prompt(stocks: List[Dict[str, Any]]) -> str:
    """生成股票分析提示词"""
    
    stocks_info = "\n".join([
        f"{i+1}. {stock.get('symbol', 'N/A')} - 来源: {stock.get('source_url', 'N/A')[:80]}"
        for i, stock in enumerate(stocks)
    ])
    
    return f"""你是一位资深的美股投资分析师，请分析以下股票，选出今晚最有投资价值的 5 只股票。

找到的股票列表:
{stocks_info}

请基于以下维度进行综合分析:
1. **市场趋势**: 当前市场环境和板块轮动
2. **技术面**: 股价走势、支撑位、阻力位
3. **基本面**: 公司业绩、行业地位、增长潜力
4. **催化剂**: 近期是否有重大利好消息
5. **风险评估**: 潜在风险和下行空间
6. **投资价值**: 短期和中期投资价值

请以 JSON 格式返回分析结果:
{{
    "market_overview": "今晚美股市场整体分析（100字内）",
    "top_stocks": [
        {{
            "rank": 1,
            "symbol": "股票代码",
            "company_name": "公司名称（如果知道）",
            "recommendation": "买入/持有/观望",
            "target_price": "目标价（如果有）",
            "investment_score": 8.5,
            "key_reasons": [
                "推荐理由1",
                "推荐理由2",
                "推荐理由3"
            ],
            "catalysts": [
                "催化剂1",
                "催化剂2"
            ],
            "risks": [
                "风险1",
                "风险2"
            ],
            "time_horizon": "短期/中期/长期",
            "analysis": "详细分析（200字内）"
        }},
        {{
            "rank": 2,
            "symbol": "股票代码",
            "company_name": "公司名称（如果知道）",
            "recommendation": "买入/持有/观望",
            "target_price": "目标价（如果有）",
            "investment_score": 8.5,
            "key_reasons": [
                "推荐理由1",
                "推荐理由2",
                "推荐理由3"
            ],
            "catalysts": [
                "催化剂1",
                "催化剂2"
            ],
            "risks": [
                "风险1",
                "风险2"
            ],
            "time_horizon": "短期/中期/长期",
            "analysis": "详细分析（200字内）"
        }},
        {{
            "rank": 3,
            "symbol": "股票代码",
            "company_name": "公司名称（如果知道）",
            "recommendation": "买入/持有/观望",
            "target_price": "目标价（如果有）",
            "investment_score": 8.5,
            "key_reasons": [
                "推荐理由1",
                "推荐理由2",
                "推荐理由3"
            ],
            "catalysts": [
                "催化剂1",
                "催化剂2"
            ],
            "risks": [
                "风险1",
                "风险2"
            ],
            "time_horizon": "短期/中期/长期",
            "analysis": "详细分析（200字内）"
        }},
        {{
            "rank": 4,
            "symbol": "股票代码",
            "company_name": "公司名称（如果知道）",
            "recommendation": "买入/持有/观望",
            "target_price": "目标价（如果有）",
            "investment_score": 8.5,
            "key_reasons": [
                "推荐理由1",
                "推荐理由2",
                "推荐理由3"
            ],
            "catalysts": [
                "催化剂1",
                "催化剂2"
            ],
            "risks": [
                "风险1",
                "风险2"
            ],
            "time_horizon": "短期/中期/长期",
            "analysis": "详细分析（200字内）"
        }},
        {{
            "rank": 5,
            "symbol": "股票代码",
            "company_name": "公司名称（如果知道）",
            "recommendation": "买入/持有/观望",
            "target_price": "目标价（如果有）",
            "investment_score": 8.5,
            "key_reasons": [
                "推荐理由1",
                "推荐理由2",
                "推荐理由3"
            ],
            "catalysts": [
                "催化剂1",
                "催化剂2"
            ],
            "risks": [
                "风险1",
                "风险2"
            ],
            "time_horizon": "短期/中期/长期",
            "analysis": "详细分析（200字内）"
        }}
    ],
    "investment_strategy": "今晚的投资策略建议（150字内）",
    "risk_warning": "风险提示（100字内）"
}}

注意:
- 必须选出恰好 5 只股票
- 投资评分范围 0-10，越高越好
- 分析要客观、专业、有深度
- 考虑当前市场环境和时间节点（今晚）
- 如果股票信息不足，请基于股票代码和常识进行合理推断"""


def get_coarse_filtering_prompt(stocks: List[Dict[str, Any]]) -> str:
    """生成粗筛选提示词"""
    
    stocks_info = "\n".join([
        f"- {stock.get('symbol', 'N/A')}: 涨跌幅 {stock.get('change_percent', 'N/A')}"
        for stock in stocks
    ])
    
    return f"""你是一位高效的基金研究员，需要从以下列表中快速筛选出20只最有潜力的股票进行下一步深入分析。

候选股票列表 (超过100只):
{stocks_info}

筛选标准:
1.  **基本面**: 优先选择你所知道的、具有坚实基本面或处于热门行业的公司。
2.  **技术面**: 结合提供的涨跌幅信息，优先选择趋势强劲的股票。
3.  **多样性**: 确保选出的20只股票覆盖不同行业，避免过度集中。
4.  **潜力**: 挑出具备短期或中期增长催化剂的股票。

请以 JSON 格式返回你筛选出的20只股票代码。

格式示例:
{{
    "selected_stocks": [
        "AAPL", "GOOGL", "NVDA", "TSLA", "AMZN", "MSFT", "JPM", "V", "UNH", "PFE",
        "CRM", "ADBE", "NFLX", "INTC", "CSCO", "PYPL", "CMCSA", "DIS", "KO", "PG"
    ],
    "reasoning": "简要说明你的筛选逻辑，例如：综合考虑了科技龙头、金融、医疗等板块，并优先选择了近期表现强势且基本面稳固的公司。"
}}
"""

