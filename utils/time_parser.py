#!/usr/bin/env python3
"""
时间解析工具 - 解析相对时间和绝对时间
"""

from datetime import datetime, timedelta
import re


def parse_relative_time(time_str: str) -> str:
    """
    解析相对时间字符串，返回绝对日期
    
    Args:
        time_str: 相对时间字符串，如 "1 days ago", "2 weeks ago", "3 hours ago"
    
    Returns:
        格式化的日期字符串 "YYYY-MM-DD"
    """
    if not time_str:
        return ""
    
    time_str = time_str.lower().strip()
    now = datetime.now()
    
    # 匹配 "X days/weeks/months/years ago"
    patterns = [
        (r'(\d+)\s*days?\s*ago', 'days'),
        (r'(\d+)\s*weeks?\s*ago', 'weeks'),
        (r'(\d+)\s*months?\s*ago', 'months'),
        (r'(\d+)\s*years?\s*ago', 'years'),
        (r'(\d+)\s*hours?\s*ago', 'hours'),
        (r'(\d+)\s*minutes?\s*ago', 'minutes'),
    ]
    
    for pattern, unit in patterns:
        match = re.search(pattern, time_str)
        if match:
            value = int(match.group(1))
            
            if unit == 'days':
                date = now - timedelta(days=value)
            elif unit == 'weeks':
                date = now - timedelta(weeks=value)
            elif unit == 'months':
                date = now - timedelta(days=value * 30)  # 近似
            elif unit == 'years':
                date = now - timedelta(days=value * 365)  # 近似
            elif unit == 'hours':
                date = now - timedelta(hours=value)
            elif unit == 'minutes':
                date = now - timedelta(minutes=value)
            
            return date.strftime("%Y-%m-%d")
    
    # 如果已经是日期格式，直接返回
    if re.match(r'\d{4}', time_str):
        return time_str
    
    return ""


def is_within_days(date_str: str, days: int = 7) -> bool:
    """
    检查日期是否在指定天数内
    
    Args:
        date_str: 日期字符串，可以是相对时间或绝对日期
        days: 天数阈值
    
    Returns:
        True 如果在指定天数内，否则 False
    """
    if not date_str:
        return False
    
    # 解析相对时间
    parsed_date = parse_relative_time(date_str)
    if not parsed_date:
        return False
    
    try:
        # 解析日期
        if len(parsed_date) == 4:  # 只有年份
            paper_date = datetime.strptime(parsed_date, "%Y")
        elif len(parsed_date) == 7:  # YYYY-MM
            paper_date = datetime.strptime(parsed_date, "%Y-%m")
        else:  # YYYY-MM-DD
            paper_date = datetime.strptime(parsed_date, "%Y-%m-%d")
        
        # 计算天数差
        now = datetime.now()
        delta = now - paper_date
        
        return delta.days <= days
    except:
        return False


def get_days_ago(date_str: str) -> int:
    """
    计算日期距今多少天
    
    Args:
        date_str: 日期字符串
    
    Returns:
        距今天数，如果解析失败返回 999999
    """
    parsed_date = parse_relative_time(date_str)
    if not parsed_date:
        return 999999
    
    try:
        if len(parsed_date) == 4:
            paper_date = datetime.strptime(parsed_date, "%Y")
        elif len(parsed_date) == 7:
            paper_date = datetime.strptime(parsed_date, "%Y-%m")
        else:
            paper_date = datetime.strptime(parsed_date, "%Y-%m-%d")
        
        now = datetime.now()
        delta = now - paper_date
        return delta.days
    except:
        return 999999
