#!/usr/bin/env python3
"""
网络连通性测试程序
测试通过本地代理访问 Google Scholar 和 arXiv
"""

import asyncio
from playwright.async_api import async_playwright


async def test_connectivity():
    """测试网络连通性"""
    
    # 代理配置
    proxy_config = {
        "server": "http://127.0.0.1:7890"
    }
    
    print("="*70)
    print("网络连通性测试")
    print("="*70)
    print(f"代理设置: {proxy_config['server']}")
    print()
    
    async with async_playwright() as p:
        # 启动浏览器（使用代理）
        print("🚀 启动浏览器（使用代理）...")
        browser = await p.chromium.launch(
            headless=True,
            proxy=proxy_config
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        # 测试列表
        test_sites = [
            {
                "name": "Google Scholar",
                "url": "https://scholar.google.com/scholar?q=machine+learning&as_ylo=2026&as_yhi=2026",
                "success_indicator": ".gs_ri"  # 论文结果的 CSS 选择器
            },
            {
                "name": "arXiv",
                "url": "https://arxiv.org/search/?query=machine+learning&searchtype=all&order=-announced_date_first",
                "success_indicator": ".arxiv-result"  # 论文结果的 CSS 选择器
            },
            {
                "name": "Google (测试基本连通性)",
                "url": "https://www.google.com",
                "success_indicator": "input[name='q']"  # 搜索框
            }
        ]
        
        results = []
        
        for site in test_sites:
            print(f"\n{'─'*70}")
            print(f"测试: {site['name']}")
            print(f"URL: {site['url']}")
            print("─"*70)
            
            try:
                # 尝试访问
                print("⏳ 正在访问...")
                response = await page.goto(site['url'], timeout=30000, wait_until="domcontentloaded")
                
                if response:
                    status = response.status
                    print(f"✅ HTTP 状态码: {status}")
                    
                    if status == 200:
                        # 等待页面加载
                        await asyncio.sleep(2)
                        
                        # 检查是否有预期的元素
                        try:
                            elements = await page.query_selector_all(site['success_indicator'])
                            element_count = len(elements)
                            
                            if element_count > 0:
                                print(f"✅ 找到 {element_count} 个结果元素")
                                print(f"✅ {site['name']} 连通正常")
                                results.append({
                                    "name": site['name'],
                                    "status": "成功",
                                    "details": f"HTTP {status}, 找到 {element_count} 个元素"
                                })
                            else:
                                print(f"⚠️  页面加载成功，但未找到预期元素: {site['success_indicator']}")
                                
                                # 获取页面标题和部分内容用于调试
                                title = await page.title()
                                print(f"   页面标题: {title}")
                                
                                # 保存页面截图
                                screenshot_path = f"debug_{site['name'].replace(' ', '_')}.png"
                                await page.screenshot(path=screenshot_path)
                                print(f"   已保存截图: {screenshot_path}")
                                
                                results.append({
                                    "name": site['name'],
                                    "status": "警告",
                                    "details": f"HTTP {status}, 但未找到预期元素"
                                })
                        except Exception as e:
                            print(f"⚠️  检查元素时出错: {e}")
                            results.append({
                                "name": site['name'],
                                "status": "警告",
                                "details": f"HTTP {status}, 元素检查失败"
                            })
                    else:
                        print(f"❌ HTTP 状态码异常: {status}")
                        results.append({
                            "name": site['name'],
                            "status": "失败",
                            "details": f"HTTP {status}"
                        })
                else:
                    print("❌ 无响应")
                    results.append({
                        "name": site['name'],
                        "status": "失败",
                        "details": "无响应"
                    })
                    
            except asyncio.TimeoutError:
                print("❌ 访问超时（30秒）")
                results.append({
                    "name": site['name'],
                    "status": "失败",
                    "details": "超时"
                })
            except Exception as e:
                print(f"❌ 访问失败: {e}")
                results.append({
                    "name": site['name'],
                    "status": "失败",
                    "details": str(e)
                })
        
        await browser.close()
        
        # 打印总结
        print(f"\n{'='*70}")
        print("测试总结")
        print("="*70)
        
        for result in results:
            status_icon = "✅" if result['status'] == "成功" else "⚠️" if result['status'] == "警告" else "❌"
            print(f"{status_icon} {result['name']}: {result['status']} - {result['details']}")
        
        print()
        
        # 给出建议
        success_count = sum(1 for r in results if r['status'] == "成功")
        
        if success_count == len(results):
            print("🎉 所有测试通过！网络连接正常。")
        elif success_count > 0:
            print("⚠️  部分测试通过，请检查失败的站点。")
        else:
            print("❌ 所有测试失败，请检查：")
            print("   1. 代理是否正在运行（127.0.0.1:7890）")
            print("   2. 代理配置是否正确")
            print("   3. 网络连接是否正常")
        
        print("\n" + "="*70)


async def test_without_proxy():
    """测试不使用代理的连通性"""
    
    print("\n" + "="*70)
    print("测试：不使用代理")
    print("="*70)
    
    async with async_playwright() as p:
        print("🚀 启动浏览器（不使用代理）...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("⏳ 访问 Google...")
            response = await page.goto("https://www.google.com", timeout=10000)
            if response and response.status == 200:
                print("✅ 不使用代理可以访问 Google")
                print("   建议：代理可能不是必需的，或者代理配置有问题")
            else:
                print(f"⚠️  访问 Google 状态码: {response.status if response else 'None'}")
        except Exception as e:
            print(f"❌ 不使用代理无法访问 Google: {e}")
            print("   建议：可能需要使用代理")
        
        await browser.close()


async def main():
    """主函数"""
    # 测试使用代理
    await test_connectivity()
    
    # 测试不使用代理
    await test_without_proxy()


if __name__ == "__main__":
    asyncio.run(main())
