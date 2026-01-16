#!/usr/bin/env python3
"""
简单测试 arXiv 搜索和提取
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


async def test_arxiv_search():
    """测试 arXiv 搜索"""
    
    proxy = "http://127.0.0.1:7890"
    
    # 简单的查询
    queries = [
        "machine learning",
        "reinforcement learning",
        "large language models"
    ]
    
    async with async_playwright() as p:
        print("启动浏览器...")
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": proxy}
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        for query in queries:
            print(f"\n{'='*70}")
            print(f"测试查询: {query}")
            print("="*70)
            
            # 构建 arXiv URL（不带年份过滤）
            url = f"https://arxiv.org/search/?query={query.replace(' ', '+')}&searchtype=all&abstracts=show&order=-announced_date_first&size=50"
            print(f"URL: {url}")
            
            try:
                print("正在访问...")
                await page.goto(url, timeout=30000)
                await asyncio.sleep(2)
                
                html = await page.content()
                
                # 保存页面
                with open(f"debug_arxiv_{query.replace(' ', '_')}.html", 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"✅ 页面已保存")
                
                # 解析
                soup = BeautifulSoup(html, 'html.parser')
                
                # 尝试不同的选择器
                selectors = [
                    '.arxiv-result',
                    'li.arxiv-result',
                    'ol.breathe-horizontal li',
                    'li[class*="arxiv"]'
                ]
                
                for selector in selectors:
                    results = soup.select(selector)
                    if results:
                        print(f"✅ 选择器 '{selector}' 找到 {len(results)} 个结果")
                        
                        # 显示第一个结果的结构
                        if len(results) > 0:
                            first = results[0]
                            print(f"\n第一个结果的 HTML 结构:")
                            print(first.prettify()[:500])
                        break
                else:
                    print("❌ 所有选择器都没有找到结果")
                    
                    # 显示页面标题
                    title_elem = soup.select_one('title')
                    if title_elem:
                        print(f"页面标题: {title_elem.get_text()}")
                    
                    # 检查是否有错误信息
                    if "No results" in html or "没有结果" in html:
                        print("⚠️  页面显示没有结果")
                    
            except Exception as e:
                print(f"❌ 错误: {e}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_arxiv_search())
