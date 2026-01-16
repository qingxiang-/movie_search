"""
Prompts module - LLM 提示词模板
"""

from .movie_prompts import (
    get_planning_prompt,
    get_analysis_prompt
)

from .paper_prompts import (
    get_query_planning_prompt,
    get_decision_making_prompt,
    get_summarization_prompt,
    get_topic_generation_prompt,
    get_topic_refinement_prompt
)

__all__ = [
    'get_planning_prompt',
    'get_analysis_prompt',
    'get_query_planning_prompt',
    'get_decision_making_prompt', 
    'get_summarization_prompt',
    'get_topic_generation_prompt',
    'get_topic_refinement_prompt'
]
