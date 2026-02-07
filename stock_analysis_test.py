#!/usr/bin/env python3
"""
股票分析测试 - 真实数据
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.stock_agent import StockAnalysisAgent


async def main():
    """测试股票分析"""
    
    print("\n" + "="*70)
    print("📈 6个月持仓分析测试 (真实数据)")
    print("="*70 + "\n")
    
    agent = StockAnalysisAgent(hold_period="6mo")
    
    # 测试股票
    test_symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META']
    
    result = await agent.analyze_symbols(test_symbols)
    
    report = result['holding_report']
    
    # 打印汇总
    print(f"\n{'='*70}")
    print("📊 分析汇总")
    print("="*70)
    print(f"   总计: {report['summary']['total']} 只")
    print(f"   🟢 买入: {report['summary']['buy']} 只")
    print(f"   🟡 持有: {report['summary']['hold']} 只")
    print(f"   🔴 卖出: {report['summary']['sell']} 只")
    
    # 打印推荐
    print(f"\n{'='*70}")
    print("🟢 买入推荐")
    print("="*70)
    for stock in report['buy_recommendations']:
        data = stock['quant_data']
        print(f"   {stock['symbol']}: ${data['current_price']} | 6个月: {data['returns_6m']:+.1f}% | PE: {data.get('pe_ratio') or 'N/A'} | 评分: {stock['total_score']}")
    
    print(f"\n{'='*70}")
    print("🟡 持有")
    print("="*70)
    for stock in report['hold_recommendations']:
        data = stock['quant_data']
        print(f"   {stock['symbol']}: ${data['current_price']} | 6个月: {data['returns_6m']:+.1f}% | 评分: {stock['total_score']}")
    
    # 生成 HTML 报告
    html = agent.generate_html_report(report)
    report_file = f"data/holding_report_{report['report_date']}.html"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n{'='*70}")
    print("📄 报告已保存")
    print("="*70)
    print(f"   {report_file}")
    
    print("\n" + "="*70)
    print("✅ 测试完成")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
