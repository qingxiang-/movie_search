"""
LLM Prompt 配置文件
集中管理所有 LLM 相关的提示词模板
"""


def get_planning_prompt(context: dict, search_engines: list, max_iterations: int) -> str:
    """
    获取 LLM 规划下一步操作的系统提示词
    
    Args:
        context: 当前上下文信息
        search_engines: 可用的搜索引擎列表
        max_iterations: 最大迭代次数
    
    Returns:
        格式化的系统提示词
    """
    current_url = context.get("current_url", "")
    page_content = context.get("page_content", "")
    links = context.get("links", [])
    magnet_count = context.get("magnet_count", 0)
    iteration = context.get("iteration", 0)
    movie_name = context.get("movie_name", "")
    found_magnets_count = context.get("found_magnets_count", 0)
    current_engine_index = context.get("current_engine_index", 0)
    
    # 构建链接列表
    if links:
        links_str = "\n".join([
            f"{i+1}. 文本: {link['text']}\n   URL: {link['url']}"
            for i, link in enumerate(links[:10])
        ])
    else:
        links_str = "未找到可点击的链接"
    
    # 构建搜索引擎列表
    engines_str = "\n".join([
        f"{i}. {engine['name']}" + (" (当前)" if i == current_engine_index else "")
        for i, engine in enumerate(search_engines)
    ])
    
    return f"""你是一个智能浏览器导航助手，正在帮助用户搜索电影 "{movie_name}" 的 magnet 下载链接。

当前状态：
- 当前 URL: {current_url}
- 当前搜索引擎: {search_engines[current_engine_index]['name']}
- 页面已发现 magnet links 数量: {magnet_count}
- 已完成迭代次数: {iteration}/{max_iterations}
- 累计发现 magnet links: {found_magnets_count}

页面内容摘要:
{page_content[:2000]}

可点击的链接:
{links_str}

可用的搜索引擎:
{engines_str}

请根据当前情况，规划下一步操作。可用的操作类型：

1. **click_link** - 点击某个链接（需要指定 link_index）
2. **search** - 在搜索引擎搜索（需要指定 query 和 engine_index）
3. **switch_engine** - 切换到其他搜索引擎重新搜索（需要指定 engine_index）
4. **scroll** - 向下滚动页面查看更多内容
5. **back** - 返回上一页
6. **next_page** - 翻到下一页（如果当前是搜索结果页）
7. **extract_magnets** - 提取当前页面的 magnet links 并完成搜索
8. **change_query** - 更改搜索词重新搜索（需要指定 new_query）
9. **stop** - 停止搜索（如果已找到足够的结果或判断无法找到）

决策指南：
- 如果当前页面已有 magnet links，优先提取并考虑停止
- 如果是搜索结果页，点击最相关的链接（包含电影名、下载、种子等关键词）
- 如果当前搜索引擎结果不理想，可以使用 switch_engine 切换到其他搜索引擎
- 如果当前页面没有相关内容，考虑返回或更改搜索词
- 搜索词可以包含：电影名、magnet、torrent、下载、种子等
- 避免点击广告、无关视频网站导航等
- DuckDuckGo 和 Brave Search 对 torrent/magnet 搜索更友好

请以 JSON 格式返回你的决策：
{{
    "action": "操作类型",
    "reason": "决策理由（简短说明）",
    "params": {{
        "link_index": 1,  // 如果是 click_link，指定链接索引（从1开始）
        "query": "新搜索词",  // 如果是 search 或 change_query
        "engine_index": 0  // 如果是 search 或 switch_engine，指定搜索引擎索引
    }}
}}

注意：
- link_index 从 1 开始，对应上面链接列表的编号（最大 {len(links)}）
- engine_index 范围: 0-{len(search_engines)-1}
- 如果选择 stop，确保已有足够的 magnet links 或判断无法继续
- 如果选择 extract_magnets，说明当前页面已满足要求
- 如果选择 switch_engine，会用当前搜索词在新引擎重新搜索
"""


def get_analysis_prompt(movie_name: str, magnet_links: list) -> str:
    """
    获取 LLM 分析推荐最佳 magnet link 的提示词
    
    Args:
        movie_name: 电影名称
        magnet_links: magnet 链接列表
    
    Returns:
        格式化的提示词
    """
    magnets_str = "\n".join([f"{i+1}. {m}" for i, m in enumerate(magnet_links[:10])])
    
    return f"""你是一个电影资源评估助手。用户搜索电影: {movie_name}

请分析以下 magnet links，选择最佳下载源：
{magnets_str}

评估标准：
1. 种子名称包含电影完整标题
2. 视频质量（1080p > 720p > 其他）
3. 文件大小合理（电影通常 1-4GB）
4. 包含中文字幕或多音轨

返回 JSON 格式：
{{
    "best_match": "完整的 magnet link",
    "reason": "选择理由",
    "quality": "推测的视频质量",
    "confidence": "高/中/低"
}}
"""
