"""
Candidate Pool - 候选论文池管理
"""

import json
from typing import List, Dict, Any
from datetime import datetime


class CandidatePool:
    """候选论文池管理器"""
    
    def __init__(self, min_papers: int = 5, max_papers: int = 10, min_quality_score: float = 7.0):
        """
        初始化候选池
        
        Args:
            min_papers: 最少论文数量
            max_papers: 最多论文数量
            min_quality_score: 最低质量分数
        """
        self.min_papers = min_papers
        self.max_papers = max_papers
        self.min_quality_score = min_quality_score
        self.papers = []
        self.metadata = {
            "topic": "",
            "date_range": "",
            "total_papers_seen": 0,
            "queries_tried": [],
            "search_engines_used": [],
            "search_start_time": datetime.now().isoformat(),
            "search_end_time": None
        }
    
    def add_paper(self, paper: Dict[str, Any]) -> bool:
        """
        添加论文到候选池
        
        Args:
            paper: 论文信息字典
            
        Returns:
            是否成功添加
        """
        # 检查质量分数
        if paper.get('importance_score', 0) < self.min_quality_score:
            return False
        
        # 检查是否已满
        if len(self.papers) >= self.max_papers:
            # 如果新论文质量更高，替换最低分的论文
            min_score_paper = min(self.papers, key=lambda p: p.get('importance_score', 0))
            if paper.get('importance_score', 0) > min_score_paper.get('importance_score', 0):
                self.papers.remove(min_score_paper)
            else:
                return False
        
        # 去重检查
        if self._is_duplicate(paper):
            return False
        
        # 添加时间戳
        paper['added_time'] = datetime.now().isoformat()
        
        # 添加到候选池
        self.papers.append(paper)
        
        # 按重要性排序
        self.papers.sort(key=lambda p: p.get('importance_score', 0), reverse=True)
        
        return True
    
    def _is_duplicate(self, paper: Dict[str, Any]) -> bool:
        """检查是否重复"""
        new_title = self._normalize_title(paper.get('title', ''))
        new_url = paper.get('url', '')
        
        for existing in self.papers:
            # URL 匹配
            if new_url and new_url == existing.get('url', ''):
                return True
            
            # 标题匹配
            existing_title = self._normalize_title(existing.get('title', ''))
            if new_title and new_title == existing_title:
                return True
            
            # 标题相似度检查
            if self._calculate_similarity(new_title, existing_title) > 0.9:
                return True
        
        return False
    
    @staticmethod
    def _normalize_title(title: str) -> str:
        """标题归一化"""
        import re
        title = title.lower()
        title = re.sub(r'[^\w\s]', '', title)
        title = ' '.join(title.split())
        return title
    
    @staticmethod
    def _calculate_similarity(str1: str, str2: str) -> float:
        """计算字符串相似度（简单版本）"""
        if not str1 or not str2:
            return 0.0
        
        # 使用集合交集计算相似度
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def get_papers(self) -> List[Dict[str, Any]]:
        """获取所有论文（按重要性排序）"""
        return self.papers.copy()
    
    def get_count(self) -> int:
        """获取论文数量"""
        return len(self.papers)
    
    def get_average_score(self) -> float:
        """获取平均分数"""
        if not self.papers:
            return 0.0
        scores = [p.get('importance_score', 0) for p in self.papers]
        return sum(scores) / len(scores)
    
    def is_sufficient(self) -> bool:
        """判断候选池是否足够"""
        return (len(self.papers) >= self.min_papers and 
                self.get_average_score() >= self.min_quality_score)
    
    def is_full(self) -> bool:
        """判断候选池是否已满"""
        return len(self.papers) >= self.max_papers
    
    def get_status(self) -> str:
        """获取候选池状态描述"""
        count = self.get_count()
        avg_score = self.get_average_score()
        
        if count == 0:
            return "空"
        elif count < self.min_papers:
            return f"继续收集 ({count}/{self.min_papers})"
        elif self.is_sufficient():
            return f"质量足够 ({count}篇, 平均{avg_score:.1f}分)"
        else:
            return f"需要更高质量 ({count}篇, 平均{avg_score:.1f}分)"
    
    def update_metadata(self, **kwargs):
        """更新元数据"""
        self.metadata.update(kwargs)
    
    def finalize(self):
        """完成搜索，更新结束时间"""
        self.metadata['search_end_time'] = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "papers": self.papers,
            "metadata": self.metadata
        }
    
    def save_to_file(self, filepath: str):
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'CandidatePool':
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        pool = cls()
        pool.papers = data.get('papers', [])
        pool.metadata = data.get('metadata', {})
        return pool
