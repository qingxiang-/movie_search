#!/usr/bin/env python3
"""
大麦网验证码测试 - 简化版
"""
import asyncio
import base64
import os
from datetime import datetime
from playwright.async_api import async_playwright
import ddddocr


async def test_damai_simple():
    """简化版测试"""
    print("🌐 启动浏览器...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        try:
            print("📄 访问大麦网...")
            await page.goto("https://search.damai.cn/search.html?keyword=演唱会", 
                          wait_until='networkidle', timeout=30000)
            
            print("📸 截图...")
            os.makedirs("debug_simple", exist_ok=True)
            await page.screenshot(path="debug_simple/01_page.png", full_page=True)
            
            # 列出所有 frames
            print(f"\n📦 发现 {len(page.frames)} 个 frames:")
            for i, frame in enumerate(page.frames):
                print(f"   [{i}] {frame.url[:100]}")
            
            # 查找验证码
            print("\n🔍 查找验证码元素...")
            
            # 检查页面是否有验证码相关元素
            selectors = [
                '.nc_wrapper', '.baxia-dialog', '.bx-content',
                '[class*="captcha"]', '[class*="nc_"]', '[id*="nc_"]',
                '.slider-captcha', '.tcaptcha'
            ]
            
            for sel in selectors:
                els = await page.query_selector_all(sel)
                if els:
                    visible = []
                    for el in els:
                        if await el.is_visible():
                            box = await el.bounding_box()
                            visible.append(f"{sel}: visible, box={box}")
                    if visible:
                        print(f"   ✓ {', '.join(visible)}")
            
            # 等待看是否有验证码出现
            print("\n⏳ 等待 10 秒看是否有验证码...")
            await asyncio.sleep(10)
            
            await page.screenshot(path="debug_simple/02_after_wait.png", full_page=True)
            
            # 再检查一次
            print("\n🔍 再次检查验证码...")
            for sel in selectors:
                els = await page.query_selector_all(sel)
                for el in els:
                    if await el.is_visible():
                        box = await el.bounding_box()
                        print(f"   ✓ {sel}: visible, box={box}")
                        
                        # 如果找到验证码，尝试获取图片
                        if 'nc' in sel.lower() or 'slider' in sel.lower():
                            print(f"\n🎯 找到滑块，尝试获取图片...")
                            imgs = await el.query_selector_all('img')
                            if imgs:
                                print(f"   ✓ 找到 {len(imgs)} 张图片")
                                for j, img in enumerate(imgs[:2]):
                                    src = await img.get_attribute('src')
                                    print(f"   [{j}] src: {src[:100] if src else 'None'}")
            
            print("\n✅ 测试完成! 查看 debug_simple/ 目录下的截图")
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


if __name__ == "__main__":
    print("="*60)
    print("🎯 大麦验证码测试 - 简化版")
    print("="*60)
    asyncio.run(test_damai_simple())
