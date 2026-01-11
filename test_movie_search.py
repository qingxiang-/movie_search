#!/usr/bin/env python3
"""
单元测试 - 测试搜索引擎调用和结果获取
"""

import asyncio
from playwright.async_api import async_playwright
from movie_search import MovieSearcher


class TestSearchEngines:
    """测试各个搜索引擎的调用"""

    async def test_duckduckgo_search(self):
        """测试 DuckDuckGo 搜索引擎调用"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                # 测试搜索 URL 构建
                searcher = MovieSearcher()
                engine = searcher.SEARCH_ENGINES[0]  # DuckDuckGo
                assert engine["name"] == "DuckDuckGo"
                
                # 测试页面加载
                test_query = "test movie magnet"
                from urllib.parse import quote
                search_url = f"{engine['url']}{quote(test_query)}"
                
                await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                
                # 验证页面加载成功
                current_url = page.url
                assert "duckduckgo.com" in current_url
                
                # 验证页面有内容
                html = await page.content()
                assert len(html) > 0
                assert "test" in html.lower() or "movie" in html.lower()
                
                print(f"✅ DuckDuckGo 测试通过 - URL: {current_url}")
                
            finally:
                await browser.close()

    async def test_brave_search(self):
        """测试 Brave Search 搜索引擎调用"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                # 测试搜索 URL 构建
                searcher = MovieSearcher()
                engine = searcher.SEARCH_ENGINES[1]  # Brave Search
                assert engine["name"] == "Brave Search"
                
                # 测试页面加载
                test_query = "test movie torrent"
                from urllib.parse import quote
                search_url = f"{engine['url']}{quote(test_query)}"
                
                await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                
                # 验证页面加载成功
                current_url = page.url
                assert "brave.com" in current_url
                
                # 验证页面有内容
                html = await page.content()
                assert len(html) > 0
                
                print(f"✅ Brave Search 测试通过 - URL: {current_url}")
                
            finally:
                await browser.close()

    async def test_bing_search(self):
        """测试 Bing 搜索引擎调用"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                # 测试搜索 URL 构建
                searcher = MovieSearcher()
                engine = searcher.SEARCH_ENGINES[2]  # Bing
                assert engine["name"] == "Bing"
                
                # 测试页面加载
                test_query = "test movie download"
                from urllib.parse import quote
                search_url = f"{engine['url']}{quote(test_query)}"
                
                await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                
                # 验证页面加载成功
                current_url = page.url
                assert "bing.com" in current_url
                
                # 验证页面有内容
                html = await page.content()
                assert len(html) > 0
                
                print(f"✅ Bing 测试通过 - URL: {current_url}")
                
            finally:
                await browser.close()

    async def test_search_engine_switching(self):
        """测试搜索引擎切换功能"""
        searcher = MovieSearcher()
        
        # 验证初始引擎
        assert searcher.current_engine_index == 0
        assert searcher.SEARCH_ENGINES[0]["name"] == "DuckDuckGo"
        
        # 模拟切换到 Brave Search
        searcher.current_engine_index = 1
        assert searcher.current_engine_index == 1
        assert searcher.SEARCH_ENGINES[1]["name"] == "Brave Search"
        
        # 模拟切换到 Bing
        searcher.current_engine_index = 2
        assert searcher.current_engine_index == 2
        assert searcher.SEARCH_ENGINES[2]["name"] == "Bing"
        
        print("✅ 搜索引擎切换测试通过")

    async def test_retry_mechanism(self):
        """测试重试机制"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                searcher = MovieSearcher(max_retries=2)
                
                # 测试有效 URL（应该成功）
                valid_url = "https://www.bing.com"
                success = await searcher._goto_with_retry(page, valid_url, timeout=15000)
                assert success == True
                
                # 测试无效 URL（应该失败但不抛异常）
                invalid_url = "https://invalid-domain-that-does-not-exist-12345.com"
                success = await searcher._goto_with_retry(page, invalid_url, timeout=5000)
                assert success == False
                
                print("✅ 重试机制测试通过")
                
            finally:
                await searcher.close()
                await browser.close()

    async def test_magnet_extraction(self):
        """测试 magnet 链接提取"""
        searcher = MovieSearcher()
        
        # 测试 HTML 包含 magnet 链接
        test_html = """
        <html>
        <body>
            <a href="magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678&dn=test">Test Magnet 1</a>
            <a href="magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12&dn=test2&tr=tracker">Test Magnet 2</a>
            <p>Some text with magnet:?xt=urn:btih:fedcba0987654321fedcba0987654321fedcba09 embedded</p>
        </body>
        </html>
        """
        
        magnets = searcher.extract_magnet_links(test_html)
        
        # 验证提取到 magnet 链接
        assert len(magnets) >= 2
        assert all(m.startswith("magnet:?xt=urn:btih:") for m in magnets)
        
        # 验证去重功能
        magnets2 = searcher.extract_magnet_links(test_html)
        assert len(searcher.found_magnets) == len(magnets)  # 不应该重复添加
        
        print(f"✅ Magnet 提取测试通过 - 找到 {len(magnets)} 个链接")

    async def test_page_content_extraction(self):
        """测试页面内容提取（关键词优先）"""
        searcher = MovieSearcher()
        searcher.movie_name = "Test Movie"
        
        test_html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <script>console.log('should be removed');</script>
            <style>.test { color: red; }</style>
            <div>This is an ad, ignore this content</div>
            <p>Download Test Movie magnet torrent here with high quality</p>
            <p>Another paragraph about Test Movie 种子下载 BT资源</p>
            <div>Some irrelevant content without keywords</div>
        </body>
        </html>
        """
        
        content = searcher.extract_page_content(test_html)
        
        # 验证脚本和样式被移除
        assert "console.log" not in content
        assert "color: red" not in content
        
        # 验证关键词内容被保留
        assert "magnet" in content.lower() or "torrent" in content.lower()
        
        # 验证内容不为空
        assert len(content) > 0
        
        print(f"✅ 页面内容提取测试通过 - 提取了 {len(content)} 字符")


class TestIntegration:
    """集成测试 - 测试完整搜索流程"""

    async def test_search_engines_config(self):
        """测试搜索引擎配置正确性"""
        searcher = MovieSearcher()
        
        # 验证有3个搜索引擎
        assert len(searcher.SEARCH_ENGINES) == 3
        
        # 验证每个引擎配置完整
        for engine in searcher.SEARCH_ENGINES:
            assert "name" in engine
            assert "url" in engine
            assert "query_param" in engine
            assert engine["url"].startswith("https://")
        
        # 验证引擎名称
        engine_names = [e["name"] for e in searcher.SEARCH_ENGINES]
        assert "DuckDuckGo" in engine_names
        assert "Brave Search" in engine_names
        assert "Bing" in engine_names
        
        print(f"✅ 搜索引擎配置测试通过 - 共 {len(searcher.SEARCH_ENGINES)} 个引擎")

    async def test_parameters(self):
        """测试参数化配置"""
        # 测试默认参数
        searcher1 = MovieSearcher()
        assert searcher1.max_iterations == 15
        assert searcher1.min_magnets == 5
        assert searcher1.max_retries == 3
        
        # 测试自定义参数
        searcher2 = MovieSearcher(max_iterations=10, min_magnets=3, max_retries=5)
        assert searcher2.max_iterations == 10
        assert searcher2.min_magnets == 3
        assert searcher2.max_retries == 5
        
        print("✅ 参数化配置测试通过")


# 运行测试的辅助函数
async def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("🧪 开始运行单元测试")
    print("="*70 + "\n")
    
    test_search = TestSearchEngines()
    test_integration = TestIntegration()
    
    try:
        # 基础配置测试
        print("\n📋 测试 1: 搜索引擎配置")
        await test_integration.test_search_engines_config()
        
        print("\n📋 测试 2: 参数化配置")
        await test_integration.test_parameters()
        
        print("\n📋 测试 3: 搜索引擎切换")
        await test_search.test_search_engine_switching()
        
        print("\n📋 测试 4: Magnet 链接提取")
        await test_search.test_magnet_extraction()
        
        print("\n📋 测试 5: 页面内容提取")
        await test_search.test_page_content_extraction()
        
        print("\n📋 测试 6: 重试机制")
        await test_search.test_retry_mechanism()
        
        # 搜索引擎实际调用测试（需要网络）
        print("\n📋 测试 7: DuckDuckGo 搜索引擎调用")
        await test_search.test_duckduckgo_search()
        
        print("\n📋 测试 8: Brave Search 搜索引擎调用")
        await test_search.test_brave_search()
        
        print("\n📋 测试 9: Bing 搜索引擎调用")
        await test_search.test_bing_search()
        
        print("\n" + "="*70)
        print("✅ 所有测试通过!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 直接运行测试（不使用 pytest）
    asyncio.run(run_all_tests())
