"""
Utils module - 工具函数和辅助类
"""

from .candidate_pool import CandidatePool
from .deduplication import DeduplicationManager
from .email_sender import EmailSender

__all__ = ['CandidatePool', 'DeduplicationManager', 'EmailSender']
