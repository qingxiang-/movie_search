#!/usr/bin/env python3
"""
测试 yfinance 数据获取
"""

import sys
import os

# 检查 yfinance
try:
    import yfinance as yf
    print("✅ yfinance 已安装")
except ImportError:
    print("❌ yfinance 未安装")
    sys.exit(1)

# 测试数据获取
test_symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL']

print(f"\n📊 测试获取 {len(test_symbols)} 只股票数据...\n")

for symbol in test_symbols:
    print(f"[{symbol}]")
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # 尝试获取关键数据
        data = {
            'currentPrice': info.get('currentPrice'),
            'trailingPE': info.get('trailingPE'),
            'returnOnEquity': info.get('returnOnEquity'),
            'revenueGrowth': info.get('revenueGrowth'),
            'profitMargins': info.get('profitMargins'),
            'beta': info.get('beta'),
            'marketCap': info.get('marketCap'),
        }
        
        # 获取历史数据
        hist = stock.history(period="6mo")
        
        if hist.empty:
            print(f"   ❌ 无历史数据")
            continue
            
        current_price = hist['Close'].iloc[-1]
        start_price = hist['Close'].iloc[0]
        returns_6m = ((current_price / start_price) - 1) * 100
        
        print(f"   ✅ 当前价: ${current_price:.2f}")
        print(f"   ✅ 6个月收益: {returns_6m:.1f}%")
        print(f"   ✅ PE: {data['trailingPE']}")
        print(f"   ✅ ROE: {data['returnOnEquity']*100 if data['returnOnEquity'] else 'N/A':.1f}%")
        
    except Exception as e:
        print(f"   ❌ 错误: {e}")

print("\n✅ 测试完成")
