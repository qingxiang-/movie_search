#!/usr/bin/env python3
"""
大麦网验证码调试 - 改进版
检测真正的验证码形式（iframe/弹窗/覆盖层）
"""
import asyncio
import random
from playwright.async_api import async_playwright
import os
from datetime import datetime

async def test_captcha():
    debug_dir = "debug_captcha"
    os.makedirs(debug_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async with async_playwright() as p:
        print("🌐 启动浏览器...")
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # 注入反检测脚本
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        """)
        
        page = await context.new_page()
        
        try:
            # 访问大麦
            print("\n📄 访问大麦网搜索页...")
            await page.goto("https://search.damai.cn/search.html?keyword=演唱会", wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # 截图
            await page.screenshot(path=f"{debug_dir}/damai_search_{timestamp}_01_init.png")
            print("📸 初始截图已保存")
            
            # 检查页面中所有可能的验证码元素
            print("\n🔍 全面检查验证码元素...")
            
            # 1. 检查所有 iframes
            all_iframes = page.frames
            print(f"\n📦 发现 {len(all_iframes)} 个 frames/iframes:")
            for i, frame in enumerate(all_iframes):
                url = frame.url[:100] if frame.url else "(no url)"
                print(f"   [{i}] {url}")
            
            # 2. 检查页面中的弹窗/遮罩
            popup_selectors = [
                '.baxia-dialog',           # 阿里系滑块验证码
                '.bx-content',             # 阿里系内容区
                '[class*="captcha"]',      # 含 captcha 的元素
                '[id*="captcha"]',
                '[class*="nc_"]',          # 阿里云滑块
                '[id*="nc_"]',
                '.nc_wrapper',             # 滑块包装器
                '.tcaptcha',               # 腾讯验证码
                '.geetest_',               # 极验验证码
                '.captcha-panel',          # 验证码面板
                '.slider-captcha',         # 滑块验证码
                '[class*="damai-captcha"]',
                '[class*="security"]',
            ]
            
            print("\n🎯 检查验证码相关元素...")
            found_elements = {}
            for selector in popup_selectors:
                try:
                    els = await page.query_selector_all(selector)
                    if els:
                        count = len(els)
                        visible_count = 0
                        for el in els:
                            is_visible = await el.is_visible()
                            if is_visible:
                                visible_count += 1
                                box = await el.bounding_box()
                                found_elements[selector] = {
                                    'total': count,
                                    'visible': visible_count,
                                    'box': box
                                }
                                print(f"   ✓ {selector}: {count}个, 可见{visible_count}个, 位置{box}")
                except Exception as e:
                    print(f"   ✗ {selector}: {e}")
            
            # 3. 检查特定类名的 div（可能包含验证码）
            print("\n🔍 检查可能的验证码容器...")
            suspect_selectors = [
                'div[class*="slide"]',
                'div[class*="slider"]', 
                'div[class*="verify"]',
                'div[class*="check"]',
                'div[class*="captcha"]',
                'div[id*="slide"]',
                'div[id*="slider"]',
                'div[id*="verify"]',
                'div[id*="captcha"]',
            ]
            
            for selector in suspect_selectors:
                try:
                    els = await page.query_selector_all(selector)
                    for el in els:
                        is_visible = await el.is_visible()
                        if is_visible:
                            box = await el.bounding_box()
                            text = await el.text_content()
                            print(f"   ✓ {selector[:50]}: visible, box={box}")
                            if text and len(text.strip()) > 0:
                                print(f"      文本: {text[:100]}")
                except:
                    pass
            
            # 4. 检查是否有任何遮罩层
            print("\n🛡️ 检查遮罩层...")
            overlay_selectors = [
                '.overlay',
                '.mask',
                '.popup-mask',
                '.dialog-mask',
                '[class*="overlay"]',
                '[class*="mask"]',
                '[class*="popup"]',
            ]
            
            for selector in overlay_selectors:
                try:
                    els = await page.query_selector_all(selector)
                    for el in els:
                        is_visible = await el.is_visible()
                        if is_visible:
                            box = await el.bounding_box()
                            opacity = await el.evaluate('el => window.getComputedStyle(el).opacity')
                            print(f"   ✓ {selector[:40]}: visible, opacity={opacity}, box={box}")
                except:
                    pass
            
            # 保存完整页面HTML
            with open(f"{debug_dir}/damai_search_{timestamp}_page.html", 'w', encoding='utf-8') as f:
                html = await page.content()
                f.write(html)
            print(f"\n📄 页面HTML已保存: damai_search_{timestamp}_page.html")
            
            # 最终截图
            await page.screenshot(path=f"{debug_dir}/damai_search_{timestamp}_02_full.png", full_page=True)
            print("📸 最终截图已保存")
            
            print("\n" + "="*60)
            print("📊 检测结果总结:")
            print("="*60)
            
            if found_elements:
                print(f"\n发现 {len(found_elements)} 个可能的验证码元素:")
                for selector, info in found_elements.items():
                    print(f"  - {selector}: {info}")
            else:
                print("\n⚠️  未发现明显的验证码元素")
                print("可能原因:")
                print("  1. 验证码已通过或不存在")
                print("  2. 验证码是动态加载的，需要更多等待")
                print("  3. 验证码使用其他技术（如纯JS检测）")
            
            print("\n⏸️  浏览器保持打开120秒，请手动检查...")
            print("   观察点:")
            print("   1. 是否有验证码弹窗出现")
            print("   2. 页面是否正常显示了搜索结果")
            print("   3. 是否有任何滑块或验证提示")
            await asyncio.sleep(120)
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_captcha())
