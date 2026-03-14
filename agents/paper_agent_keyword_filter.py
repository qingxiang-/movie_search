"""
关键词过滤模块 - P1 优化
"""
import re
from typing import List, Dict


# 排除的应用领域关键词 (医疗、临床等应用类)
EXCLUSION_DOMAINS = {
    "clinical", "medical", "healthcare", "hospital", "patient",
    "diagnosis", "treatment", "disease", "drug", "medicine",
    "biosignal", "ecg", "ehr", "icu", "wearable",
    "sleep monitoring", "federated medical", "cancer", "tumor",
    "surgery", "therapeutic", "clinical trial", "health monitoring"
}


def filter_keywords(keywords: List[str]) -> List[str]:
    """
    P1 优化：过滤低质量关键词

    过滤规则:
    1. 只接受英文 (允许少数特定中文术语)
    2. 长度在 2-6 个单词之间
    3. 排除过于宽泛的词
    4. 排除医疗/临床等应用领域

    Args:
        keywords: 待过滤的关键词列表

    Returns:
        过滤后的关键词列表
    """
    # 允许的特殊中文术语 (领域内标准术语)
    ALLOWED_CN_TERMS = {
        "大模型", "强化学习", "蒸馏", "多模态", "生成式",
    }

    # 过于宽泛的词 (排除)
    TOO_BROAD_TERMS = {
        "ai", "ml", "dl", "llm", "deep learning", "machine learning",
        "artificial intelligence", "neural network", "neural networks",
        "模型", "学习", "训练", "优化", "算法"
    }

    filtered = []
    for kw in keywords:
        kw_clean = kw.strip().lower()
        kw_words = kw_clean.split()

        # 规则 1: 检查是否为允许的中文术语（直接放行）
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', kw))
        if has_chinese and kw in ALLOWED_CN_TERMS:
            filtered.append(kw)
            continue

        # 规则 2: 英文关键词长度检查 (2-6 个单词)
        if len(kw_words) < 2 or len(kw_words) > 6:
            continue

        # 规则 3: 检查是否包含中文（不在允许列表中）
        if has_chinese:
            # 只允许特定中文术语
            if kw not in ALLOWED_CN_TERMS:
                continue

        # 规则 4: 排除过于宽泛的词
        if kw_clean in TOO_BROAD_TERMS:
            continue

        # 规则 5: 检查是否包含无意义的词
        meaningless_words = {"study", "analysis", "based", "approach", "method", "new", "novel"}
        if all(w in meaningless_words for w in kw_words):
            continue

        # 规则 6: 排除医疗/临床等应用领域关键词
        if any(excl in kw_clean for excl in EXCLUSION_DOMAINS):
            continue

        filtered.append(kw)

    return filtered


def is_excluded_paper(paper: Dict) -> bool:
    """
    检查论文是否属于排除的应用领域

    Args:
        paper: 论文信息字典，包含 title, abstract 等

    Returns:
        True 如果应该排除，False 如果保留
    """
    title = paper.get("title", "").lower()
    abstract = paper.get("abstract", "").lower()
    text = f"{title} {abstract}"

    # 检查是否包含排除领域关键词
    exclusion_count = 0
    for excl in EXCLUSION_DOMAINS:
        if excl in text:
            exclusion_count += 1

    # 如果包含 2 个或以上排除关键词，则排除
    return exclusion_count >= 2
