"""
配置文件加载器 - 论文搜索关键词动态化
基于种子词 + LLM 动态发现
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path


class PaperKeywordConfig:
    """论文搜索关键词配置类 - 种子词 + 动态发现模式"""

    DEFAULT_SEED_KEYWORDS = [
        "LLM agent",
        "multimodal LLM",
        "code generation",
        "LLM reasoning",
        "RL"
    ]

    def __init__(self, config_path: str = None):
        """
        初始化配置加载器

        Args:
            config_path: 配置文件路径，默认查找 config/paper_keywords.json
        """
        if config_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(os.path.dirname(script_dir), 'config', 'paper_keywords.json')

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def is_dynamic_mode(self) -> bool:
        """是否启用动态模式"""
        return self.config.get('dynamic_mode', True)

    def is_rotation_enabled(self) -> bool:
        """是否启用关键词轮换"""
        return self.config.get('rotation', {}).get('enabled', True)

    def get_keywords_per_day(self) -> int:
        """获取每天使用的关键词数量"""
        return self.config.get('rotation', {}).get('keywords_per_day', 4)

    def get_max_keywords_pool(self) -> int:
        """获取关键词池最大数量"""
        return self.config.get('rotation', {}).get('max_keywords_pool', 50)

    def get_seed_keywords(self) -> List[str]:
        """获取种子关键词"""
        return self.config.get('seed_keywords', self.DEFAULT_SEED_KEYWORDS)

    def get_keyword_pool(self) -> List[str]:
        """获取当前关键词池（包含种子词 + 发现的词）"""
        # 种子词
        seed = self.get_seed_keywords()
        # LLM 发现的词
        discovered = self.config.get('discovered_keywords', [])
        # 合并去重
        pool = list(dict.fromkeys(seed + discovered))
        return pool

    def add_discovered_keywords(self, keywords: List[str]):
        """添加 LLM 发现的关键词到池中"""
        discovered = self.config.get('discovered_keywords', [])

        # 添加新关键词，去重
        for kw in keywords:
            if kw not in discovered and kw not in self.get_seed_keywords():
                discovered.append(kw)

        # 限制池大小
        max_pool = self.get_max_keywords_pool()
        if len(discovered) > max_pool:
            discovered = discovered[-max_pool:]

        self.config['discovered_keywords'] = discovered
        self.config['keywords_last_updated'] = datetime.now().strftime('%Y-%m-%d')
        self.save_config()

    def get_all_keywords(self) -> List[str]:
        """获取所有关键词"""
        return self.get_keyword_pool()

    def save_config(self):
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def reset_discovered_keywords(self):
        """重置发现的关键词"""
        self.config['discovered_keywords'] = []
        self.save_config()


class KeywordRotation:
    """关键词轮换管理器"""

    def __init__(self, keywords: List[str], keywords_per_day: int = 4):
        """
        初始化轮换管理器

        Args:
            keywords: 关键词列表
            keywords_per_day: 每天使用的关键词数量
        """
        self.keywords = keywords
        self.keywords_per_day = keywords_per_day

    def get_keywords_for_today(self) -> List[str]:
        """获取今天应该使用的关键词"""
        if not self.keywords:
            return []

        today = datetime.now()
        day_of_year = today.timetuple().tm_yday

        # 使用日期作为种子，实现每日轮换
        start_idx = (day_of_year - 1) * self.keywords_per_day % len(self.keywords)

        selected = []
        for i in range(self.keywords_per_day):
            idx = (start_idx + i) % len(self.keywords)
            selected.append(self.keywords[idx])

        return selected

    def get_keywords_for_date(self, date: datetime) -> List[str]:
        """获取指定日期应该使用的关键词"""
        if not self.keywords:
            return []

        day_of_year = date.timetuple().tm_yday
        start_idx = (day_of_year - 1) * self.keywords_per_day % len(self.keywords)

        selected = []
        for i in range(self.keywords_per_day):
            idx = (start_idx + i) % len(self.keywords)
            selected.append(self.keywords[idx])

        return selected


def load_keyword_config(config_path: str = None) -> PaperKeywordConfig:
    """便捷函数：加载关键词配置"""
    return PaperKeywordConfig(config_path)


if __name__ == "__main__":
    # 测试
    config = load_keyword_config()
    print("种子关键词:", config.get_seed_keywords())
    print("动态模式:", config.is_dynamic_mode())
    print("关键词池:", config.get_keyword_pool())

    rotation = KeywordRotation(config.get_keyword_pool(), config.get_keywords_per_day())
    print("今日关键词:", rotation.get_keywords_for_today())
