#!/usr/bin/env python3
"""
美股分析工具 - LLM 智能分析版
使用 LLM 分析最新资讯和行情，推荐最有投资价值的股票
"""

import os
import asyncio
from dotenv import load_dotenv

from agents.stock_agent import StockAnalysisAgent

# 加载环境变量
load_dotenv()


async def main():
    """主函数 - 分析美股并推荐投资机会"""
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
            print("LLM 智能分析功能需要 API Key 才能运行")
            print("提示: 复制 .env.example 为 .env 并填入真实的 API Key\n")
            return
    
    print("="*70)
    print("📈 美股智能分析系统")
    print("="*70)
    print()
    
    print("🎯 目标: 找出今晚最有投资价值的 5 只美股")
    print("📊 分析维度: 市场趋势、技术面、基本面、催化剂、风险")
    print()
    print("🌐 数据来源策略:")
    print("   ✅ 直接访问专业财经网站（Yahoo Finance, Finviz 等）")
    print("   ✅ 实时热门股票榜单")
    print("   ✅ 今日涨幅榜和成交量排行")
    print()
    print("🚀 开始分析...")
    print()
    
    # 获取代理配置
    proxy = os.getenv("HTTP_PROXY", "http://127.0.0.1:7890")
    
    # 创建股票分析 Agent
    agent = StockAnalysisAgent(
        max_iterations=20,
        min_stocks=3,
        max_stocks=5,
        max_retries=3,
        proxy=proxy
    )
    
    try:
        # 执行搜索和分析（使用直接访问财经网站策略）
        result = await agent.search_stocks(
            use_direct_sites=True,      # 直接访问专业财经网站
            use_search_engines=False    # 不使用搜索引擎
        )
        
        all_stocks = result.get('all_stocks', [])
        detailed_analysis = result.get('detailed_analysis', [])
        analysis = result.get('analysis', {})
        
        print(f"{'='*70}")
        print(f"📊 分析结果")
        print("="*70)
        print(f"\n初步筛选: {len(all_stocks)} 只股票")
        print(f"深度调研: {len(detailed_analysis)} 只股票")
        
        if not analysis.get('top_stocks'):
            print("\n❌ 未能生成投资推荐")
            return
        
        # 显示市场概览
        market_overview = analysis.get('market_overview', 'N/A')
        print(f"\n📈 市场概览:")
        print(f"   {market_overview}")
        
        # 显示推荐股票
        top_stocks = analysis.get('top_stocks', [])
        print(f"\n🏆 今晚最值得关注的 {len(top_stocks)} 只股票:\n")
        
        for stock in top_stocks:
            rank = stock.get('rank', 0)
            symbol = stock.get('symbol', 'N/A')
            company = stock.get('company_name', 'N/A')
            
            # 从新的嵌套结构中提取数据
            summary = stock.get('investment_summary', {})
            fundamental = stock.get('fundamental_analysis', {})
            technical = stock.get('technical_analysis', {})
            
            recommendation = summary.get('recommendation', 'N/A')
            score = summary.get('overall_score', 0)
            time_horizon = summary.get('time_horizon', 'N/A')

            print(f"{'─'*70}")
            print(f"🥇 Top {rank}: {symbol} - {company}")
            print(f"   推荐: {recommendation} | 评分: {score}/10 | 周期: {time_horizon}")
            
            # 选股理由
            if stock.get('selection_reason'):
                print(f"\n   🎯 选股理由:")
                print(f"      {stock.get('selection_reason')}")

            # 基本面分析
            print(f"\n   ** Fundamental Analysis:**")
            if fundamental.get('background'):
                print(f"   📋 **公司背景:** {fundamental.get('background')}")
            if fundamental.get('financial_health'):
                print(f"   💵 **财务状况:** {fundamental.get('financial_health')}")
            if fundamental.get('catalysts'):
                print(f"   🚀 **催化剂:** {', '.join(fundamental.get('catalysts', []))}")
            if fundamental.get('risks'):
                print(f"   ⚠️  **主要风险:** {', '.join(fundamental.get('risks', []))}")

            # 技术面分析
            print(f"\n   ** Technical Analysis:**")
            if technical.get('trend'):
                print(f"   📈 **当前趋势:** {technical.get('trend')}")
            if technical.get('support_levels'):
                print(f"   📉 **支撑位:** {', '.join(technical.get('support_levels', []))}")
            if technical.get('resistance_levels'):
                print(f"   📈 **阻力位:** {', '.join(technical.get('resistance_levels', []))}")
            if technical.get('volume_analysis'):
                print(f"   📊 **量价关系:** {technical.get('volume_analysis')}")

            # 综合投资建议
            if summary.get('conclusion'):
                print(f"\n   📝 **综合投资建议:**")
                print(f"      {summary.get('conclusion')}")
        
        print(f"\n{'─'*70}")
        
        # 投资策略
        strategy = analysis.get('investment_strategy', 'N/A')
        print(f"\n💡 投资策略:")
        print(f"   {strategy}")
        
        # 风险警告
        risk_warning = analysis.get('risk_warning', 'N/A')
        print(f"\n⚠️  风险提示:")
        print(f"   {risk_warning}")
        
        print("\n" + "="*70 + "\n")
        
        # 保存结果到文件
        os.makedirs('data', exist_ok=True)
        
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        result_file = f"data/stock_analysis_{date_str}.json"
        
        import json
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'search_time': result.get('search_time'),
                'all_stocks': all_stocks,
                'analysis': analysis
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 分析结果已保存到: {result_file}")
        
        # 发送邮件
        print("\n📧 正在发送邮件...")
        
        # 准备邮件数据（包含所有深度分析信息）
        email_stocks = []
        for stock in top_stocks:
            summary = stock.get('investment_summary', {})
            fundamental = stock.get('fundamental_analysis', {})
            
            email_stock = {
                'rank': stock.get('rank', 0),
                'symbol': stock.get('symbol', 'N/A'),
                'company_name': stock.get('company_name', 'N/A'),
                'recommendation': summary.get('recommendation', 'N/A'),
                'investment_score': summary.get('overall_score', 0),
                'background': fundamental.get('background', ''),
                'catalysts': fundamental.get('catalysts', []),
                'risks': fundamental.get('risks', []),
                'selection_reason': stock.get('selection_reason', ''),
                'detailed_analysis': summary.get('conclusion', ''),
                'time_horizon': summary.get('time_horizon', 'N/A'),
                'target_price': 'N/A' # 新结构中无此字段
            }
            email_stocks.append(email_stock)
        
        email_topic = "美股投资推荐"
        date_range_str = f"{date_str} 盘后分析"
        
        # 添加市场概览和策略到邮件
        email_data = {
            'stocks': email_stocks,
            'market_overview': market_overview,
            'investment_strategy': strategy,
            'risk_warning': risk_warning
        }
        
        success = agent.email_sender.send_stock_email(
            email_data,
            email_topic,
            date_range_str
        )
        
        if success:
            print("✅ 邮件发送成功！")
        else:
            print("❌ 邮件发送失败")
        
        print("\n" + "="*70)
        print("🎉 分析完成!")
        print("="*70)
        
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
