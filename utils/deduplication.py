"""
Deduplication Manager - 论文去重管理
"""

import json
import os
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime


class DeduplicationManager:
    """去重管理器"""
    
    def __init__(self, records_file: str = "sent_papers.json"):
        """
        初始化去重管理器
        
        Args:
            records_file: 已发送记录文件路径
        """
        self.records_file = records_file
        self.records = self._load_records()
    
    def _load_records(self) -> Dict[str, Any]:
        """加载已发送记录"""
        if os.path.exists(self.records_file):
            try:
                with open(self.records_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  加载记录文件失败: {e}")
                return self._create_empty_records()
        else:
            return self._create_empty_records()
    
    @staticmethod
    def _create_empty_records() -> Dict[str, Any]:
        """创建空记录"""
        return {
            "papers": [],
            "metadata": {
                "total_sent": 0,
                "last_update": None
            }
        }
    
    def _save_records(self):
        """保存记录到文件"""
        try:
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存记录文件失败: {e}")
    
    @staticmethod
    def _normalize_title(title: str) -> str:
        """标题归一化"""
        title = title.lower()
        title = re.sub(r'[^\w\s]', '', title)
        title = ' '.join(title.split())
        return title
    
    @staticmethod
    def _calculate_similarity(str1: str, str2: str) -> float:
        """计算字符串相似度"""
        if not str1 or not str2:
            return 0.0
        
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def is_duplicate(self, paper: Dict[str, Any]) -> Tuple[bool, str]:
        """
        检查论文是否已发送
        
        Args:
            paper: 论文信息
            
        Returns:
            (是否重复, 重复原因)
        """
        new_title = paper.get('title', '')
        new_title_norm = self._normalize_title(new_title)
        new_url = paper.get('url', '')
        
        for sent in self.records['papers']:
            # URL 完全匹配
            if new_url and new_url == sent.get('url', ''):
                return True, f"URL 完全匹配 (已于 {sent.get('sent_date', 'N/A')} 发送)"
            
            # 标题完全匹配
            if new_title_norm and new_title_norm == sent.get('title_normalized', ''):
                return True, f"标题完全匹配 (已于 {sent.get('sent_date', 'N/A')} 发送)"
            
            # 标题高度相似
            similarity = self._calculate_similarity(new_title_norm, sent.get('title_normalized', ''))
            if similarity > 0.9:
                return True, f"标题高度相似 ({similarity:.1%}, 已于 {sent.get('sent_date', 'N/A')} 发送)"
        
        return False, ""
    
    def filter_duplicates(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤重复论文
        
        Args:
            papers: 论文列表
            
        Returns:
            去重后的论文列表
        """
        filtered = []
        duplicates = []
        
        for paper in papers:
            is_dup, reason = self.is_duplicate(paper)
            if is_dup:
                duplicates.append({
                    'title': paper.get('title', 'N/A'),
                    'reason': reason
                })
            else:
                filtered.append(paper)
        
        if duplicates:
            print(f"\n🔍 去重检查: 过滤了 {len(duplicates)} 篇已发送论文")
            for dup in duplicates[:3]:  # 只显示前3个
                print(f"  - {dup['title'][:60]}... ({dup['reason']})")
        
        return filtered
    
    def add_sent_papers(self, papers: List[Dict[str, Any]], topic: str):
        """
        添加已发送论文记录
        
        Args:
            papers: 论文列表
            topic: 搜索主题
        """
        sent_date = datetime.now().isoformat()
        
        for paper in papers:
            self.records['papers'].append({
                'title': paper.get('title', ''),
                'title_normalized': self._normalize_title(paper.get('title', '')),
                'url': paper.get('url', ''),
                'sent_date': sent_date,
                'topic': topic,
                'email_subject': f"学术论文推荐: {topic} ({datetime.now().strftime('%Y-%m-%d')})"
            })
        
        self.records['metadata']['total_sent'] = len(self.records['papers'])
        self.records['metadata']['last_update'] = sent_date
        
        self._save_records()
        print(f"✅ 已更新发送记录: {len(papers)} 篇论文")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_sent': self.records['metadata']['total_sent'],
            'last_update': self.records['metadata']['last_update'],
            'unique_topics': len(set(p.get('topic', '') for p in self.records['papers']))
        }
