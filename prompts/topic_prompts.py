"""
Topic Prompts - 主题分析和聚类相关的提示词模板
用于从论文中提取热点主题、聚类论文、生成主题报告
"""

from typing import List, Dict, Any


def get_trend_extraction_prompt(articles: List[Dict[str, Any]], papers: List[Dict[str, Any]]) -> str:
    """
    从搜索结果中提取热门研究主题

    Args:
        articles: 文章列表 [{"title": str, "snippet": str, "source": str}]
        papers: 论文列表 [{"title": str, "abstract": str}]

    Returns:
        提示词字符串
    """
    articles_text = ""
    for i, article in enumerate(articles[:15], 1):
        articles_text += f"""
{i}. Title: {article.get('title', 'N/A')}
   Source: {article.get('source', 'N/A')}
   Snippet: {article.get('snippet', 'N/A')[:300]}
"""

    papers_text = ""
    for i, paper in enumerate(papers[:15], 1):
        papers_text += f"""
{i}. Title: {paper.get('title', 'N/A')}
   Abstract: {paper.get('abstract', 'N/A')[:300]}
"""

    return f"""你是一位AI研究趋势分析师。请分析以下近期LLM/AI/Agent领域的研究动态，提取出最热门的研究主题。

## 近期文章动态
{articles_text}

## 近期高影响力论文
{papers_text}

## 任务要求
1. 识别出3-8个最热门、最具影响力的研究主题
2. 每个主题需要:
   - topic: 主题名称（简洁明确，如 "Test-Time Compute"）
   - description: 主题简要描述（50字以内）
   - keywords: 2-4个可用于搜索的关键词（英文，适合在arXiv搜索）
   - priority: 优先级1-10（10最高，基于热度、影响力、新颖性）

## 输出格式（严格JSON）
{{
  "topics": [
    {{
      "topic": "Test-Time Compute",
      "description": "推理时增加计算量以提升模型性能",
      "keywords": ["test-time compute", "inference scaling", "reasoning compute"],
      "priority": 9
    }},
    ...
  ]
}}

请直接输出JSON，不要有其他内容。"""


def get_paper_clustering_prompt(papers: List[Dict[str, Any]]) -> str:
    """
    将论文聚类到不同研究主题

    Args:
        papers: 论文列表 [{"title": str, "abstract": str, "importance_score": float}]

    Returns:
        提示词字符串
    """
    papers_text = ""
    for i, paper in enumerate(papers, 1):
        score = paper.get('importance_score', 0)
        papers_text += f"""
[Paper {i}] (Score: {score:.1f})
Title: {paper.get('title', 'N/A')}
Abstract: {paper.get('abstract', 'N/A')[:400]}
Key Methods: {', '.join(paper.get('key_methods', [])[:3]) if paper.get('key_methods') else 'N/A'}
"""

    return f"""你是一位学术论文分析专家。请将以下论文按照研究主题进行聚类分组。

## 论文列表
{papers_text}

## 任务要求
1. 将论文分成2-5个主题组（根据论文实际内容决定组数）
2. 每组需要:
   - topic_id: 组编号（如 "topic_1"）
   - topic_name: 主题名称（简洁明确，如 "Multimodal Reasoning"）
   - topic_description: 主题简要描述（100字以内，说明这个主题研究什么、为什么重要）
   - key_insights: 该主题的关键洞察（2-3条）
   - paper_ids: 属于该组的论文编号列表（如 [1, 3, 5]）

3. 每篇论文必须且只能属于一个主题组
4. 如果论文内容差异太大，可以创建"Other Research"组

## 输出格式（严格JSON）
{{
  "clusters": [
    {{
      "topic_id": "topic_1",
      "topic_name": "Test-Time Compute & Reasoning Scaling",
      "topic_description": "研究如何在推理阶段增加计算来提升LLM推理能力，包括搜索策略、验证机制等",
      "key_insights": [
        "推理时计算可以显著提升复杂推理任务的性能",
        "搜索和验证策略是关键"
      ],
      "paper_ids": [1, 3, 5]
    }},
    ...
  ]
}}

请直接输出JSON，不要有其他内容。"""


def get_topic_summary_prompt(topic_name: str, topic_description: str, papers: List[Dict[str, Any]]) -> str:
    """
    生成主题摘要，包含论文的相关性解释

    Args:
        topic_name: 主题名称
        topic_description: 主题描述
        papers: 该主题下的论文列表

    Returns:
        提示词字符串
    """
    papers_text = ""
    for i, paper in enumerate(papers, 1):
        papers_text += f"""
[Paper {i}]
Title: {paper.get('title', 'N/A')}
Authors: {', '.join(paper.get('authors', [])[:3])}
Abstract: {paper.get('abstract', 'N/A')[:400]}
Key Methods: {', '.join(paper.get('key_methods', [])[:3]) if paper.get('key_methods') else 'N/A'}
Innovations: {', '.join(paper.get('innovations', [])[:3]) if paper.get('innovations') else 'N/A'}
Published: {paper.get('published_date', 'N/A')}
URL: {paper.get('url', 'N/A')}
"""

    return f"""你是一位学术研究分析师。请为主题"{topic_name}"生成一份详细的研究摘要报告。

## 主题信息
主题名称: {topic_name}
主题描述: {topic_description}

## 相关论文
{papers_text}

## 任务要求
请生成以下内容:

1. **主题概览** (overview): 100-150字，说明该主题的研究背景、核心问题、近期进展

2. **关键洞察** (key_insights): 3-5条该主题最重要的研究发现或趋势

3. **论文分析** (paper_analyses): 对每篇论文提供:
   - paper_id: 论文编号
   - relevance: 为什么这篇论文与该主题相关（50字以内）
   - main_contribution: 主要贡献（50字以内）
   - key_experiments: 关键实验/方法（50字以内）
   - key_insight: 这篇论文的核心洞察（50字以内）

## 输出格式（严格JSON）
{{
  "overview": "该主题研究...（100-150字）",
  "key_insights": [
    "洞察1",
    "洞察2",
    ...
  ],
  "paper_analyses": [
    {{
      "paper_id": 1,
      "relevance": "该论文直接解决了...问题",
      "main_contribution": "提出了...方法",
      "key_experiments": "在...数据集上验证",
      "key_insight": "证明了...的有效性"
    }},
    ...
  ]
}}

请直接输出JSON，不要有其他内容。"""


def get_keyword_generation_from_trends_prompt(topics: List[Dict[str, Any]]) -> str:
    """
    从热门主题生成搜索关键词

    Args:
        topics: 主题列表 [{"topic": str, "description": str, "keywords": List[str], "priority": int}]

    Returns:
        提示词字符串
    """
    topics_text = ""
    for i, topic in enumerate(topics, 1):
        topics_text += f"""
{i}. {topic.get('topic', 'N/A')}
   Description: {topic.get('description', 'N/A')}
   Suggested Keywords: {', '.join(topic.get('keywords', []))}
   Priority: {topic.get('priority', 5)}
"""

    return f"""你是一位学术搜索专家。请根据以下热门研究主题，生成最优的arXiv搜索关键词。

## 热门研究主题
{topics_text}

## 任务要求
1. 从每个主题提取1-2个最有效的搜索关键词
2. 优先选择高优先级主题的关键词
3. 关键词应适合在arXiv搜索，能够找到高质量相关论文
4. 总共生成15-25个关键词

## 输出格式（严格JSON）
{{
  "keywords": [
    "test-time compute",
    "reasoning scaling",
    "..."
  ],
  "topic_keyword_mapping": {{
    "Test-Time Compute": ["test-time compute", "inference scaling"],
    "...": "..."
  }}
}}

请直接输出JSON，不要有其他内容。"""


def get_daily_digest_intro_prompt(topic_summaries: List[Dict[str, Any]], date_str: str) -> str:
    """
    生成每日研究摘要的整体介绍

    Args:
        topic_summaries: 各主题的摘要列表
        date_str: 日期字符串

    Returns:
        提示词字符串
    """
    topics_overview = ""
    for summary in topic_summaries:
        topics_overview += f"- {summary.get('topic_name', 'N/A')}: {summary.get('paper_count', 0)} papers\n"

    return f"""请为以下AI研究日报生成一段简短的开场介绍。

## 日期: {date_str}

## 今日主题
{topics_overview}

## 任务要求
1. 生成50-100字的日报开场介绍
2. 说明今日覆盖的研究领域和论文数量
3. 语气专业但不失亲和

## 输出格式（严格JSON）
{{
  "intro": "Today's AI research digest covers..."
}}

请直接输出JSON，不要有其他内容。"""