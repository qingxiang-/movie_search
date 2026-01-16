"""
Paper Search Prompts - 论文搜索相关的 LLM 提示词模板
"""

from typing import Dict, List, Any


def get_query_planning_prompt(context: Dict[str, Any]) -> str:
    """
    获取查询规划提示词
    
    Args:
        context: 包含 topic, candidate_count, avg_score, query_history, result_feedback 等
    
    Returns:
        格式化的提示词
    """
    topic = context.get("topic", "")
    candidate_count = context.get("candidate_count", 0)
    avg_score = context.get("avg_score", 0.0)
    query_history = context.get("query_history", [])
    result_feedback = context.get("result_feedback", {})
    
    # 构建查询历史
    history_str = ""
    if query_history:
        history_str = "\n".join([
            f"{i+1}. \"{q['query']}\" ({q['engine']}) - 找到 {q.get('relevant_count', 0)} 篇相关论文"
            for i, q in enumerate(query_history[-5:])  # 只显示最近5次
        ])
    else:
        history_str = "无（首次搜索）"
    
    from datetime import datetime
    current_year = datetime.now().year
    current_month = datetime.now().strftime("%B %Y")
    
    return f"""你是学术搜索查询优化专家。

【任务】
为学术论文搜索生成最优查询词，重点关注最新、最有洞察力的论文。

【输入信息】
搜索主题: {topic}
时间范围: 最近一周
当前时间: {current_month}
候选池状态: {candidate_count}/10 篇{f"，平均分: {avg_score:.1f}" if candidate_count > 0 else ""}

已尝试的查询:
{history_str}

当前搜索反馈:
- 结果数量: {result_feedback.get('result_count', 'N/A')}
- 相关论文数: {result_feedback.get('relevant_count', 'N/A')}
- 平均质量: {result_feedback.get('quality', 'N/A')}

【核心策略：超简短查询 + 按日期排序】
1. **强制使用 2-4 个单词**：查询必须极其简短
   - ✅ 完美例子: "LLM agent", "multimodal LLM", "code generation", "RLHF"
   - ✅ 可接受: "LLM reasoning", "vision language", "agent planning"
   - ❌ 太长: "multimodal reasoning", "reinforcement learning agents", "language model training"
   - ❌ 绝对禁止: 任何超过 4 个单词的查询

2. **单词数量限制**：
   - 最少 2 个单词
   - 最多 4 个单词
   - 优先 2-3 个单词

3. **不要在查询中加年份**：系统会自动按日期排序
   - ❌ 不要用: "LLM 2026", "agents 2026"
   - ✅ 只用: "LLM", "agents"

4. **优先 arXiv**：最新预印本，按提交日期排序
   - 系统会自动只看最近2页（最新20篇左右）
   - 从中挑选最有洞察力和影响力的论文

5. **关注点**：
   - Insight（洞察力）：提出新视角、新方法、新理解
   - Impact（影响力）：解决重要问题、可能产生广泛影响

【重要：如果连续多次找到 0 篇论文】
- 进一步简化：只用1-2个最核心的词
- 切换到 Google Scholar
- 使用更通用的领域术语

【可用搜索引擎】
- arXiv: **首选**，最新预印本，按日期排序
- Google Scholar: 覆盖面广，适合找不到结果时使用
- Semantic Scholar: AI 推荐，适合发现相关论文

【输出要求】
返回 JSON 格式:
{{
    "query": "2-4个单词的超简短查询",
    "engine": "推荐的搜索引擎（优先arXiv）",
    "reason": "选择理由（简短说明）",
    "expected_results": "预期找到什么类型的论文"
}}

【示例】
输入: topic="LLM推理能力", candidate_count=0
输出: {{
    "query": "LLM reasoning",
    "engine": "arXiv",
    "reason": "2个词，极简查询，系统按日期排序看最新20篇",
    "expected_results": "最新的LLM推理论文"
}}

输入: topic="多模态模型", candidate_count=2
输出: {{
    "query": "multimodal LLM",
    "engine": "arXiv",
    "reason": "3个词，聚焦多模态大模型",
    "expected_results": "视觉语言模型最新进展"
}}

输入: topic="强化学习代理", candidate_count=0
输出: {{
    "query": "RL agent",
    "engine": "arXiv",
    "reason": "2个词，最简洁，覆盖面广",
    "expected_results": "强化学习代理最新研究"
}}

**重要**：查询必须是 2-4 个单词，不能更长！

请生成下一个搜索查询。"""


def get_decision_making_prompt(context: Dict[str, Any]) -> str:
    """
    获取决策制定提示词
    
    Args:
        context: 包含 topic, candidate_count, avg_score, paper_info 等
    
    Returns:
        格式化的提示词
    """
    topic = context.get("topic", "")
    candidate_count = context.get("candidate_count", 0)
    avg_score = context.get("avg_score", 0.0)
    paper = context.get("paper_info", {})
    
    return f"""你是学术论文评估和决策专家。

【任务】
评估论文质量，决定是否加入候选池，并规划下一步操作。

【输入信息】
搜索主题: {topic}
候选池状态: {candidate_count}/10 篇{f"，平均分: {avg_score:.1f}" if candidate_count > 0 else ""}

当前论文:
标题: {paper.get('title', 'N/A')}
作者: {', '.join(paper.get('authors', [])[:5])}
单位: {', '.join(paper.get('affiliations', [])[:3])}
摘要: {paper.get('abstract', 'N/A')[:500]}...
引用数: {paper.get('citations', 'N/A')}
发表时间: {paper.get('published_date', 'N/A')}
来源: {paper.get('venue', 'N/A')}

【评估标准】(0-10分) - 重点关注洞察力和影响力
1. **洞察力 Insight (35%)**：是否提出新视角、新理解、新方法
   - 提出全新的问题框架或解决思路
   - 挑战现有假设或提供新的理论视角
   - 揭示之前被忽视的重要现象

2. **潜在影响力 Impact (30%)**：解决的问题重要性和应用价值
   - 解决领域内的关键挑战或瓶颈
   - 可能产生广泛影响或启发后续研究
   - 实际应用价值高

3. **相关性 (20%)**：与搜索主题的匹配度

4. **时效性 (10%)**：是否是最新研究（优先最近1-2周）

5. **质量 (5%)**：研究严谨性、摘要清晰度

**注意**：
- 最新论文（1-2周内）即使引用数为0也可能很有价值
- 不要过分看重引用数和作者声誉
- 关注论文是否提出了新的思考方式

【决策规则】
- 评分 >= 8.0: 高洞察力/高影响力，必须加入候选池
- 评分 6.0-8.0: 中等质量，根据候选池状态决定
- 评分 < 6.0: 低质量或相关性不足，跳过
- 信息不足: 需要查看详情页

【可用操作】
1. add_to_pool: 加入候选池
2. skip: 跳过该论文
3. view_details: 查看详情页（如果摘要不完整）
4. view_references: 查看引用文献
5. view_cited_by: 查看被引用情况
6. continue_search: 继续当前查询
7. change_query: 更换搜索查询
8. switch_engine: 切换搜索引擎
9. stop_search: 停止搜索（候选池已满且质量足够）

【输出要求】
返回 JSON 格式:
{{
    "decision": "add_to_pool/skip/need_more_info",
    "importance_score": 8.5,
    "reason": "详细评估理由",
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1"],
    "relevance": "高/中/低",
    "next_action": {{
        "action": "操作类型",
        "params": {{}},
        "reason": "操作理由"
    }},
    "pool_status": "继续收集/质量足够/需要更高质量"
}}

请评估该论文并决定下一步操作。"""


def get_summarization_prompt(paper: Dict[str, Any]) -> str:
    """
    获取论文总结提示词
    
    Args:
        paper: 论文信息字典
    
    Returns:
        格式化的提示词
    """
    return f"""你是学术论文解读专家。

【任务】
为论文生成简洁的核心观点总结。

【输入信息】
标题: {paper.get('title', 'N/A')}
作者: {', '.join(paper.get('authors', [])[:5])}
摘要: {paper.get('abstract', 'N/A')}
引用数: {paper.get('citations', 'N/A')}

【输出要求】
1. 核心观点: 2-3 句话概括主要贡献
2. 关键方法: 提取 2-3 个关键技术/方法
3. 创新点: 指出 2-3 个创新之处
4. 潜在应用: 列举 2-3 个应用场景

返回 JSON 格式:
{{
    "summary": "核心观点总结（100字以内）",
    "key_methods": ["方法1", "方法2", "方法3"],
    "innovations": ["创新点1", "创新点2"],
    "applications": ["应用1", "应用2"],
    "one_sentence": "一句话总结"
}}

【示例】
输入: "Chain-of-Thought Prompting Elicits Reasoning in LLMs"
输出: {{
    "summary": "提出链式思维提示方法，通过生成中间推理步骤显著提升大模型复杂推理能力，在数学、常识推理等任务上取得SOTA性能。",
    "key_methods": [
        "Few-shot prompting with reasoning chains",
        "Step-by-step decomposition",
        "Self-consistency decoding"
    ],
    "innovations": [
        "首次系统性研究思维链提示的有效性",
        "发现模型规模与推理能力的涌现关系"
    ],
    "applications": [
        "数学问题求解",
        "逻辑推理任务",
        "代码生成与调试"
    ],
    "one_sentence": "通过思维链提示激发大模型推理能力的开创性工作"
}}

请生成该论文的总结。"""


def get_topic_generation_prompt(context: Dict[str, Any]) -> str:
    """
    获取主题生成提示词（自主模式）
    
    Args:
        context: 包含 history_topics, sent_papers_stats, current_date 等
    
    Returns:
        格式化的提示词
    """
    current_date = context.get("current_date", "")
    history_topics = context.get("history_topics", [])
    total_sent = context.get("total_sent", 0)
    recent_topics = context.get("recent_topics", [])
    
    # 构建历史主题列表
    history_str = ""
    if history_topics:
        history_str = "\n".join([f"- {topic}" for topic in history_topics[-10:]])
    else:
        history_str = "无（首次运行）"
    
    recent_str = ""
    if recent_topics:
        recent_str = ", ".join(recent_topics[:5])
    else:
        recent_str = "无"
    
    return f"""你是AI研究趋势分析专家。

【任务】
为学术论文搜索生成最有价值的研究主题。

【基础方向】
- AI (人工智能)
- LLM (大语言模型)
- RL (强化学习)
- Agent (AI智能体)

【当前时间】
{current_date}

【历史搜索主题】
{history_str}

【已发送论文统计】
- 总数: {total_sent}
- 最近主题: {recent_str}

【热点方向参考】
1. LLM 推理 (reasoning, chain-of-thought)
2. 多模态 (multimodal, vision-language)
3. AI Agent (agents, tool use)
4. 强化学习 (reinforcement learning, RLHF)
5. 模型优化 (efficient training, quantization)
6. RAG (retrieval, long context)
7. 代码生成 (code generation)
8. 模型安全 (safety, robustness)

【重要：主题必须超级简短】
- **强制要求：每个主题最多 2-3 个单词**
- ✅ 完美例子: "LLM agent", "multimodal LLM", "code generation", "RLHF"
- ✅ 可接受: "LLM reasoning", "RL agent"
- ❌ 太长禁止: "multimodal reasoning", "LLM agents", "reinforcement learning"
- ❌ 绝对禁止: "autonomous reasoning agents", "dynamic tool orchestration"
- **不要在主题中包含年份**，系统会自动按日期排序

【生成策略】
1. 主题必须极简：2-3 个单词，不能更多
2. 避免与历史主题重复
3. 关注最有洞察力和影响力的方向
4. 优先使用缩写（如 RLHF, RL, VLM）

【输出要求】
返回 JSON 格式（包含 3-5 个不同主题）:
{{
    "topics": [
        {{
            "topic": "具体的搜索主题（英文）",
            "topic_zh": "主题中文翻译",
            "reason": "选择该主题的理由",
            "expected_papers": "预期找到什么类型的论文",
            "keywords": ["关键词1", "关键词2", "关键词3"],
            "priority": "high/medium/low",
            "novelty_score": 8.5,
            "related_topics": ["相关主题1", "相关主题2"]
        }},
        ...
    ]
}}

【主题多样性要求】
- 生成 3-5 个不同的主题
- 每个主题应覆盖不同的研究方向
- 确保主题之间有差异性，避免重复
- 优先级从高到低排序

【示例】
输入: history_topics=["LLM reasoning"]
输出: {{
    "topics": [
        {{
            "topic": "LLM agent",
            "topic_zh": "大模型智能体",
            "reason": "Agent是当前最热门方向，2-3个词最简洁",
            "keywords": ["agent", "tool use", "planning"],
            "priority": "high",
            "novelty_score": 8.5
        }},
        {{
            "topic": "multimodal LLM",
            "topic_zh": "多模态大模型",
            "reason": "视觉语言模型是前沿热点",
            "keywords": ["multimodal", "vision", "VLM"],
            "priority": "high",
            "novelty_score": 8.2
        }},
        {{
            "topic": "code generation",
            "topic_zh": "代码生成",
            "reason": "实用价值高，2个词极简",
            "keywords": ["code", "programming", "synthesis"],
            "priority": "medium",
            "novelty_score": 7.8
        }},
        {{
            "topic": "RLHF",
            "topic_zh": "人类反馈强化学习",
            "reason": "模型对齐核心技术，1个词最简",
            "keywords": ["alignment", "feedback", "preference"],
            "priority": "medium",
            "novelty_score": 7.5
        }}
    ]
}}

**重要**：每个主题必须是 2-3 个单词，最多不超过 3 个单词！

请生成 3-5 个最有价值的研究主题。"""


def get_topic_refinement_prompt(context: Dict[str, Any]) -> str:
    """
    获取主题优化提示词
    
    Args:
        context: 包含 current_topic, search_results, quality_feedback 等
    
    Returns:
        格式化的提示词
    """
    current_topic = context.get("current_topic", "")
    papers_found = context.get("papers_found", 0)
    relevant_papers = context.get("relevant_papers", 0)
    avg_score = context.get("avg_score", 0.0)
    pool_status = context.get("pool_status", "")
    issues = context.get("issues", "")
    
    return f"""你是AI研究趋势分析专家。

【当前主题】
{current_topic}

【搜索结果反馈】
- 找到论文数: {papers_found}
- 相关论文数: {relevant_papers}
- 平均质量分: {avg_score:.1f}
- 候选池状态: {pool_status}

【问题分析】
{issues if issues else '无明显问题'}

【任务】
根据搜索结果反馈，决定下一步主题策略。

【可选策略】
1. continue_current: 继续当前主题，结果质量好
2. refine_topic: 细化当前主题，结果太宽泛
3. expand_topic: 扩展当前主题，结果太窄
4. switch_related: 切换到相关主题，当前主题效果一般
5. switch_new: 切换到全新方向，当前主题效果差

【输出要求】
返回 JSON 格式:
{{
    "strategy": "continue_current/refine_topic/expand_topic/switch_related/switch_new",
    "reason": "决策理由",
    "new_topic": "新主题（如果需要切换）",
    "expected_improvement": "预期改进效果"
}}

请分析并给出建议。"""
