#!/usr/bin/env python3
"""
学术论文搜索工具 - LLM 智能导航版
使用 LLM 规划查询、评估论文、决策下一步操作
"""

import os
import asyncio
from dotenv import load_dotenv

from agents.paper_agent import PaperSearchAgent

# 加载环境变量
load_dotenv()


async def main():
    """主函数 - 使用8组预定义关键词搜索"""
    # 检查环境变量
    llm_provider = os.getenv("LLM_PROVIDER", "qwen").lower()
    
    if llm_provider == "azure":
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        if not api_key or api_key == "your_azure_api_key_here":
            print("⚠️  警告: 未设置 AZURE_OPENAI_API_KEY 环境变量")
            print("Azure OpenAI 功能需要 API Key 才能运行")
            print("提示: 复制 .env.example 为 .env 并填入真实的 API Key\n")
            return
    else:
        api_key = os.getenv("DASHSCOPE_API_KEY", "")
        if not api_key or api_key == "your_api_key_here":
            print("⚠️  警告: 未设置 DASHSCOPE_API_KEY 环境变量")
            print("LLM 智能导航功能需要 API Key 才能运行")
            print("提示: 复制 .env.example 为 .env 并填入真实的 API Key\n")
            return
    
    print("="*70)
    print("📚 学术论文搜索系统 - 8组关键词模式")
    print("="*70)
    print()
    
    # 8组预定义的超简短搜索关键词
    search_keywords = [
        "LLM agent",
        "multimodal LLM",
        "code generation",
        "LLM reasoning",
        "RLHF",
        "RL agent",
        "vision language",
        "LLM training"
    ]
    
    print("🔍 搜索关键词:")
    for i, keyword in enumerate(search_keywords, 1):
        print(f"   {i}. {keyword}")
    print()
    print("📅 时间范围: 最近一周")
    print("🎯 目标: 从所有结果中选出最好的 3 篇论文")
    print("📊 策略: arXiv 按日期排序，只看最新20篇")
    print()
    print("🚀 开始搜索...")
    print()
    
    # 获取代理配置
    proxy = os.getenv("HTTP_PROXY", "http://127.0.0.1:7890")
    
    # 创建搜索 Agent（每个关键词收集3篇）
    agent = PaperSearchAgent(
        max_iterations=10,
        min_papers=1,
        max_papers=3,  # 每个关键词最多3篇
        min_quality_score=7.0,
        date_range_days=7,
        max_retries=3,
        proxy=proxy
    )
    
    try:
        # 对每组关键词进行搜索
        all_papers = []
        
        for i, keyword in enumerate(search_keywords, 1):
            print(f"{'='*70}")
            print(f"🔍 [{i}/{len(search_keywords)}] 搜索关键词: {keyword}")
            print("="*70)
            
            # 为每个关键词重置候选池，确保独立收集 3 篇
            from utils.candidate_pool import CandidatePool
            agent.candidate_pool = CandidatePool(
                min_papers=1,
                max_papers=3,
                min_quality_score=7.0
            )
            
            result = await agent.search_papers(topic=keyword)
            
            papers = result.get('papers', [])
            print(f"✅ 找到 {len(papers)} 篇论文\n")
            
            all_papers.extend(papers)
            
            # 短暂延迟避免请求过快
            await asyncio.sleep(2)
        
        print(f"{'='*70}")
        print(f"📊 搜索汇总")
        print("="*70)
        print(f"总共找到: {len(all_papers)} 篇论文")
        
        if not all_papers:
            print("\n❌ 未找到符合条件的论文")
            return
        
        # 去重
        print("\n🔍 正在去重...")
        from utils.candidate_pool import CandidatePool
        pool = CandidatePool(min_papers=3, max_papers=100, min_quality_score=7.0)
        for paper in all_papers:
            pool.add_paper(paper)
        
        unique_papers = pool.get_papers()
        print(f"✅ 去重后剩余: {len(unique_papers)} 篇论文")
        
        papers = unique_papers
        
        if not papers:
            print("\n❌ 未找到符合条件的论文")
            return
        
        # 为每篇论文生成总结
        print("\n🤖 正在生成论文总结...")
        for i, paper in enumerate(papers, 1):
            print(f"  处理 {i}/{len(papers)}: {paper.get('title', 'N/A')[:50]}...")
            summary = await agent.summarize_paper(paper)
            paper.update(summary)
            await asyncio.sleep(1)  # 避免过快请求
        
        print("✅ 总结完成\n")
        
        # 去重检查
        print("🔍 正在检查去重...")
        filtered_papers = agent.dedup_manager.filter_duplicates(papers)
        
        if not filtered_papers:
            print("\n⚠️  所有论文都已发送过，无需重复发送")
            return
        
        print(f"✅ 去重完成，剩余 {len(filtered_papers)} 篇论文\n")
        
        # 时间过滤：只保留 1 周内的论文（LLM 已经解析了时间）
        print("📅 正在过滤时间（只保留 1 周内的论文）...")
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=7)
        recent_papers = []
        
        for paper in filtered_papers:
            date_str = paper.get('published_date', '')
            if not date_str:
                continue
            
            try:
                # LLM 已经将时间转换为 YYYY-MM-DD 格式
                if len(date_str) == 10:  # YYYY-MM-DD
                    paper_date = datetime.strptime(date_str, "%Y-%m-%d")
                elif len(date_str) == 4:  # YYYY
                    paper_date = datetime.strptime(date_str + "-01-01", "%Y-%m-%d")
                else:
                    continue
                
                if paper_date >= cutoff_date:
                    days_ago = (datetime.now() - paper_date).days
                    paper['days_ago'] = days_ago
                    recent_papers.append(paper)
            except:
                continue
        
        print(f"✅ 时间过滤完成，剩余 {len(recent_papers)} 篇最近 1 周内的论文\n")
        
        if not recent_papers:
            print("\n⚠️  没有找到 1 周内的论文")
            print("提示：LLM 可能未能正确解析时间，或确实没有最新论文")
            # 如果没有 1 周内的论文，使用所有论文
            print("📝 使用所有去重后的论文...")
            recent_papers = filtered_papers
            for paper in recent_papers:
                paper['days_ago'] = 999
        
        # 按重要性评分排序，选择最有价值的前3篇
        sorted_papers = sorted(recent_papers, key=lambda x: x.get('importance_score', 0), reverse=True)
        top_papers = sorted_papers[:3]
        
        print("="*70)
        print("📊 搜索结果 - 选出最有价值的 3 篇论文")
        print("="*70)
        
        print(f"\n搜索关键词: {', '.join(search_keywords[:3])} 等 {len(search_keywords)} 组")
        print(f"总共找到: {len(filtered_papers)} 篇论文")
        print(f"精选推荐: {len(top_papers)} 篇最有价值的论文\n")
        
        for i, paper in enumerate(top_papers, 1):
            days_ago = paper.get('days_ago', 999)
            time_info = f"{days_ago} 天前" if days_ago < 999 else "时间未知"
            print(f"\n🏆 Top {i}: {paper.get('title', 'N/A')}")
            print(f"   评分: {paper.get('importance_score', 0):.1f}/10 | 发表: {time_info}")
            print(f"   作者: {', '.join(paper.get('authors', [])[:3])}")
            print(f"   核心观点: {paper.get('summary', 'N/A')[:100]}...")
        print("\n" + "="*70 + "\n")
        
        # 1. 先保存搜索结果到文件（保存到 data 文件夹）
        os.makedirs('data', exist_ok=True)
        
        start_date, end_date = agent.get_date_range()
        pool_file = f"data/paper_pool_8keywords_{end_date}.json"
        
        # 将 top_papers 放回 pool 以便保存
        pool.papers = filtered_papers  # 保存所有去重后的论文
        pool.save_to_file(pool_file)
        print(f"\n💾 搜索结果已保存到: {pool_file}")

        # 2. 自动发送邮件（只发送最有价值的前3篇）
        email_topic = "AI/LLM 最新研究精选"
        date_range_str = f"{start_date} ~ {end_date}"

        success = agent.email_sender.send_email(
            top_papers,
            email_topic,
            date_range_str
        )

        if success:
            # 更新已发送记录（只记录发送的3篇）
            agent.dedup_manager.add_sent_papers(top_papers, email_topic)
        
        print("\n" + "="*70)
        print("🎉 搜索完成!")
        print("="*70)
        
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
