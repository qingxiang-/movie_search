#!/usr/bin/env python3
"""
测试新的搜索策略：简单关键词 + 按日期排序 + 只看前2页
"""

import sys
import os

# 添加父目录到路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from agents.paper_agent import PaperSearchAgent
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


async def test_simple_search():
    """测试简单关键词搜索"""
    print("\n" + "="*70)
    print("🧪 测试新搜索策略")
    print("="*70)
    print("\n策略说明：")
    print("  1. 使用简单关键词（2-3个核心词）")
    print("  2. arXiv 按日期排序，只看最新20篇（前2页）")
    print("  3. 评估标准：洞察力(35%) + 影响力(30%) > 引用数")
    print("  4. 优先最新论文（1-2周内）\n")
    
    # 检查 API Key
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("❌ 未设置 DASHSCOPE_API_KEY")
        return
    
    agent = PaperSearchAgent(api_key=api_key)
    
    try:
        # 测试简单主题
        test_topics = [
            "multimodal reasoning",
            "LLM agents",
            "code generation"
        ]
        
        print("="*70)
        print("📋 测试主题")
        print("="*70)
        for i, topic in enumerate(test_topics, 1):
            print(f"{i}. {topic}")
        
        # 只测试第一个主题
        topic = test_topics[0]
        print(f"\n{'='*70}")
        print(f"🔍 测试主题: {topic}")
        print("="*70)
        
        # 执行搜索（限制迭代次数为3次）
        result = await agent.search_papers_for_topic(
            topic=topic,
            max_iterations=3,
            target_papers=2
        )
        
        papers = result.get('papers', [])
        
        print(f"\n{'='*70}")
        print("📊 搜索结果")
        print("="*70)
        print(f"找到论文: {len(papers)} 篇\n")
        
        if papers:
            # 按评分排序
            sorted_papers = sorted(papers, key=lambda x: x.get('importance_score', 0), reverse=True)
            
            for i, paper in enumerate(sorted_papers[:3], 1):
                score = paper.get('importance_score', 0)
                date = paper.get('published_date', 'N/A')
                print(f"{i}. [{score:.1f}分] {paper.get('title', 'N/A')[:60]}...")
                print(f"   发表: {date} | 来源: {paper.get('source', 'N/A')}")
                if paper.get('summary'):
                    print(f"   观点: {paper.get('summary', '')[:80]}...")
                print()
        else:
            print("⚠️  未找到符合条件的论文")
            print("\n可能原因：")
            print("  - 主题太新，还没有相关论文")
            print("  - 需要调整关键词")
            print("  - 评估标准过于严格")
        
        print("="*70)
        print("✅ 测试完成")
        print("="*70)
        
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(test_simple_search())
