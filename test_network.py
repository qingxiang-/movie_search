#!/usr/bin/env python3
"""
测试网络连接和 Playwright 访问
诊断 Yahoo Finance 访问失败的原因
"""

import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()


async def test_basic_connection():
    """测试基本的网络连接"""
    print("="*70)
    print("测试 1: 基本网络连接")
    print("="*70)
    
    import httpx
    
    test_urls = [
        "https://www.google.com",
        "https://finance.yahoo.com",
        "https://finance.yahoo.com/trending-tickers"
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for url in test_urls:
            try:
                print(f"\n测试 {url}")
                response = await client.get(url)
                print(f"  ✅ 状态码: {response.status_code}")
                print(f"  ✅ 响应长度: {len(response.text)} 字符")
            except Exception as e:
                print(f"  ❌ 失败: {e}")


async def test_playwright_basic():
    """测试 Playwright 基本功能"""
    print("\n" + "="*70)
    print("测试 2: Playwright 基本访问")
    print("="*70)
    
    async with async_playwright() as p:
        print("\n启动浏览器...")
        browser = await p.chromium.launch(headless=True)
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        test_urls = [
            "https://www.google.com",
            "https://finance.yahoo.com"
        ]
        
        for url in test_urls:
            try:
                print(f"\n访问 {url}")
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                title = await page.title()
                print(f"  ✅ 页面标题: {title}")
                print(f"  ✅ URL: {page.url}")
            except Exception as e:
                print(f"  ❌ 失败: {e}")
        
        await browser.close()


async def test_playwright_with_proxy():
    """测试带代理的 Playwright 访问"""
    print("\n" + "="*70)
    print("测试 3: Playwright 带代理访问")
    print("="*70)
    
    proxy = os.getenv("HTTP_PROXY", "http://127.0.0.1:7890")
    print(f"\n使用代理: {proxy}")
    
    async with async_playwright() as p:
        print("\n启动浏览器...")
        browser = await p.chromium.launch(headless=True)
        
        context = await browser.new_context(
            proxy={"server": proxy},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        test_urls = [
            "https://finance.yahoo.com",
            "https://finance.yahoo.com/trending-tickers",
            "https://finance.yahoo.com/quote/AAPL"
        ]
        
        for url in test_urls:
            try:
                print(f"\n访问 {url}")
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(3)
                title = await page.title()
                content = await page.content()
                print(f"  ✅ 页面标题: {title}")
                print(f"  ✅ 内容长度: {len(content)} 字符")
                print(f"  ✅ URL: {page.url}")
            except Exception as e:
                print(f"  ❌ 失败: {type(e).__name__}: {e}")
        
        await browser.close()


async def test_yahoo_stock_page():
    """测试访问 Yahoo Finance 个股页面"""
    print("\n" + "="*70)
    print("测试 4: Yahoo Finance 个股页面详细测试")
    print("="*70)
    
    proxy = os.getenv("HTTP_PROXY", "http://127.0.0.1:7890")
    print(f"\n使用代理: {proxy}")
    
    test_symbols = ["AAPL", "MSFT", "TSLA", "NVDA"]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        context = await browser.new_context(
            proxy={"server": proxy},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        for symbol in test_symbols:
            print(f"\n{'─'*70}")
            print(f"测试股票: {symbol}")
            print(f"{'─'*70}")
            
            # 测试主页
            url = f"https://finance.yahoo.com/quote/{symbol}"
            try:
                print(f"\n1. 访问主页: {url}")
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(3)
                
                title = await page.title()
                content = await page.content()
                
                print(f"   ✅ 标题: {title}")
                print(f"   ✅ 内容长度: {len(content)} 字符")
                
                # 检查是否有价格信息
                if symbol in content or "quote" in content.lower():
                    print(f"   ✅ 页面包含股票信息")
                else:
                    print(f"   ⚠️  页面可能不包含股票信息")
                
            except Exception as e:
                print(f"   ❌ 主页访问失败: {type(e).__name__}: {e}")
            
            # 测试新闻页
            news_url = f"https://finance.yahoo.com/quote/{symbol}/news"
            try:
                print(f"\n2. 访问新闻页: {news_url}")
                await page.goto(news_url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                
                content = await page.content()
                print(f"   ✅ 内容长度: {len(content)} 字符")
                
                # 检查新闻标题
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                headlines = soup.find_all('h3', limit=5)
                print(f"   ✅ 找到 {len(headlines)} 个 h3 标签")
                
                for i, h in enumerate(headlines[:3], 1):
                    title = h.get_text(strip=True)
                    if title:
                        print(f"      {i}. {title[:60]}...")
                
            except Exception as e:
                print(f"   ❌ 新闻页访问失败: {type(e).__name__}: {e}")
            
            await asyncio.sleep(2)
        
        await browser.close()


async def test_connection_settings():
    """测试不同的连接设置"""
    print("\n" + "="*70)
    print("测试 5: 不同连接设置对比")
    print("="*70)
    
    proxy = os.getenv("HTTP_PROXY", "http://127.0.0.1:7890")
    test_url = "https://finance.yahoo.com/trending-tickers"
    
    settings = [
        {
            "name": "默认设置",
            "options": {}
        },
        {
            "name": "带代理",
            "options": {"proxy": {"server": proxy}}
        },
        {
            "name": "带代理 + 自定义 User-Agent",
            "options": {
                "proxy": {"server": proxy},
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        },
        {
            "name": "带代理 + 忽略 HTTPS 错误",
            "options": {
                "proxy": {"server": proxy},
                "ignore_https_errors": True
            }
        }
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for setting in settings:
            print(f"\n测试配置: {setting['name']}")
            try:
                context = await browser.new_context(**setting['options'])
                page = await context.new_page()
                
                await page.goto(test_url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                
                title = await page.title()
                content = await page.content()
                
                print(f"  ✅ 成功")
                print(f"     标题: {title}")
                print(f"     内容长度: {len(content)} 字符")
                
                await context.close()
                
            except Exception as e:
                print(f"  ❌ 失败: {type(e).__name__}: {e}")
        
        await browser.close()


async def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("🔍 网络连接诊断工具")
    print("="*70)
    
    tests = [
        ("基本网络连接", test_basic_connection),
        ("Playwright 基本访问", test_playwright_basic),
        ("Playwright 带代理访问", test_playwright_with_proxy),
        ("Yahoo Finance 个股页面", test_yahoo_stock_page),
        ("不同连接设置对比", test_connection_settings)
    ]
    
    for name, test_func in tests:
        try:
            await test_func()
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 出错: {e}")
        
        print("\n" + "─"*70)
        await asyncio.sleep(1)
    
    print("\n" + "="*70)
    print("✅ 所有测试完成")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
