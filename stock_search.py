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
    
    print("🎯 目标: 分析用户关注列表中的股票")
    print("📊 分析维度: 市场趋势、技术面、基本面、催化剂、风险")
    print()
    print("🌐 策略: 固定关注列表深度调研")
    print()
    print("🚀 开始分析...")
    print()
    
    # 获取代理配置
    proxy = os.getenv("HTTP_PROXY", "http://127.0.0.1:7890")
    
    # 用户的关注列表
    watchlist = [
        "GOOGL", "TSLA", "MSFT", "AAPL", "NVDA", "NFLX", "BABA", 
        "TCEHY", "LKNCY", "ASML", "PLTR", "XPEV", "LI", "NIO", "BYDDY", 
        "CVNA", "HTHT", "JD", "BILI", "PDD"
    ]
    
    # 创建股票分析 Agent
    agent = StockAnalysisAgent()
    
    try:
        # 执行分析（使用固定关注列表）
        results = await agent.analyze_stocks(symbols=watchlist)

        if not results:
            print("\n❌ 分析失败")
            return

        print(f"{'='*70}")
        print(f"📊 分析结果")
        print("="*70)
        print(f"\n完成分析：{len(results)} 只股票")

        # 生成 HTML 报告
        print(f"\n{'='*70}")
        print("📊 生成报告...")
        html = agent.format_result_html(results)

        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        html_file = f"data/stock_analysis_enhanced_{date_str}.html"

        os.makedirs('data', exist_ok=True)
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ HTML 已保存：{html_file}")

        # 发送邮件
        print(f"\n{'='*70}")
        print("📧 发送邮件...")
        subject = f"美股多因子分析 {date_str}"
        agent.send_email(html, subject)

        # 汇总
        print(f"\n{'='*70}")
        print("📊 因子评分汇总")
        print("="*70)

        for r in results:
            if 'stock_data' in r:
                data = r.get('stock_data', {})
                score = data.get('composite_score', 0)
                pred = r.get('prediction', {})
                rec = pred.get('recommendation', 'N/A')
                pred_ret = pred.get('predicted_return', 'N/A')
                print(f"   {r['symbol']:6s}: ${data.get('current_price', 'N/A'):>7} | 综合:{score:+2d} | 预测:{pred_ret} | {rec}")
            else:
                print(f"   {r['symbol']:6s}: ❌ 分析失败")

        print(f"\n{'='*70}\n")
        print("🎉 分析完成!")

    except Exception as e:
        print(f"\n❌ 分析过程出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
