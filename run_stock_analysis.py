#!/usr/bin/env python3
"""
股票分析完整测试 - 数据 + LLM预测 + 邮件发送
"""

import asyncio
import json
from datetime import datetime
import sys
import os

# 加载.env
from dotenv import load_dotenv
load_dotenv('.env')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.stock_agent import StockAnalysisAgent, CANDIDATE_STOCKS


async def main():
    """测试完整流程"""
    
    print("\n" + "="*70)
    print("📈 股票分析完整测试 - 20只候选股票")
    print("="*70)
    
    agent = StockAnalysisAgent()
    
    # 1. 分析全部20只股票
    symbols = CANDIDATE_STOCKS
    results = await agent.analyze_stocks(symbols)
    
    # 2. 生成 HTML
    print(f"\n{'='*70}")
    print("📊 生成 HTML 报告...")
    html = agent.format_result_html(results)
    
    html_file = f"data/stock_analysis_{datetime.now().strftime('%Y-%m-%d')}.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ HTML已保存: {html_file}")
    
    # 3. 打印详细结果
    print(f"\n{'='*70}")
    print("📋 详细结果")
    print("="*70)
    
    for r in results:
        symbol = r['symbol']
        pred = r.get('prediction', {})
        data = r.get('stock_data', {})
        
        if 'error' in pred:
            print(f"\n{symbol}: ⚠️ {pred['error']}")
            continue
        
        print(f"\n{'='*50}")
        print(f"🔮 {symbol}")
        print(f"{'='*50}")
        print(f"当前价格: ${data.get('current_price', 'N/A')}")
        print(f"历史收益: 1M={data.get('returns', {}).get('1m', 0):+.1f}%, 3M={data.get('returns', {}).get('3m', 0):+.1f}%")
        print(f"趋势: {data.get('trend', 'N/A')} | RSI: {data.get('rsi', 'N/A')}")
        
        if 'predicted_return' in pred:
            print(f"\n🔮 LLM预测")
            print(f"   6个月收益: {pred['predicted_return']:+.1f}%")
            print(f"   置信度: {pred.get('confidence', 'N/A')}")
            print(f"   风险等级: {pred.get('risk_level', 'N/A')}")
            print(f"   建议: {pred.get('recommendation', 'N/A')}")
            
            if 'reasoning' in pred:
                print(f"\n📝 分析:")
                print(f"   {pred['reasoning'][:200]}...")
    
    # 4. 发送邮件
    print(f"\n{'='*70}")
    print("📧 发送邮件...")
    agent.send_email(html)
    
    # 5. 汇总
    print(f"\n{'='*70}")
    print("📊 汇总")
    print("="*70)
    
    buy = [r['symbol'] for r in results if r.get('prediction', {}).get('recommendation') == '买入']
    hold = [r['symbol'] for r in results if r.get('prediction', {}).get('recommendation') in ['持有', '观望']]
    sell = [r['symbol'] for r in results if r.get('prediction', {}).get('recommendation') in ['卖出', '减仓']]
    
    print(f"🟢 买入 ({len(buy)}): {', '.join(buy) or '无'}")
    print(f"🟡 持有 ({len(hold)}): {', '.join(hold) or '无'}")
    print(f"🔴 卖出 ({len(sell)}): {', '.join(sell) or '无'}")
    
    # 保存 JSON
    json_file = f"data/stock_analysis_{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'results': results,
            'summary': {
                'buy': buy,
                'hold': hold,
                'sell': sell
            },
            'date': datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 JSON已保存: {json_file}")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
