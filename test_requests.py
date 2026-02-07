#!/usr/bin/env python3
"""
用 requests 测试 Yahoo Finance API
"""

import requests
import json

def get_stock_data(symbol):
    """获取股票数据"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        'range': '6mo',
        'interval': '1d',
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"   📡 状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            result = data.get('chart', {}).get('result', [])
            if result:
                meta = result[0].get('meta', {})
                print(f"   ✅ 当前价: ${meta.get('regularMarketPrice', 'N/A')}")
                print(f"   ✅ 6个月范围: ${meta.get('regularMarketStartPrice')} - ${meta.get('regularMarketPrice')}")
                return True
        else:
            print(f"   ❌ 响应错误")
            return False
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return False

test_symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL']

print("📊 测试 requests 获取股票数据...\n")

for symbol in test_symbols:
    print(f"[{symbol}]")
    get_stock_data(symbol)
    print()

print("✅ 测试完成")
