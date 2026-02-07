#!/usr/bin/env python3
"""
大麦网验证码调试 - 2026-02-05 最新版
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
            print("\n📄 访问大麦网...")
            await page.goto("https://www.damai.cn/", wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # 截图
            await page.screenshot(path=f"{debug_dir}/damai_{timestamp}_01_home.png")
            print("📸 首页截图已保存")
            
            # 找搜索框
            print("\n🔍 查找搜索框...")
            search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=10000)
            await search_input.click()
            
            # 输入
            print("⌨️  输入: 演唱会")
            for char in "演唱会":
                await search_input.type(char, delay=random.randint(100, 200))
            
            await asyncio.sleep(0.5)
            await page.screenshot(path=f"{debug_dir}/damai_{timestamp}_02_typed.png")
            
            # 回车提交
            print("⏎ 提交搜索...")
            await page.keyboard.press('Enter')
            await asyncio.sleep(5)  # 等待更长时间让验证码出现
            
            await page.screenshot(path=f"{debug_dir}/damai_{timestamp}_03_after_enter.png")
            print("📸 提交后截图")
            
            # 检查frames
            print("\n🔍 检查所有 frames...")
            all_frames = page.frames
            print(f"   总共 {len(all_frames)} 个 frames:")
            for i, frame in enumerate(all_frames):
                url = frame.url[:80] if frame.url else "(no url)"
                print(f"   [{i}] {url}")
            
            # 找验证码iframe
            print("\n🎯 查找验证码...")
            captcha_frame = None
            for i in range(30):  # 等待30秒
                for frame in all_frames:
                    url = frame.url.lower()
                    if 'captcha' in url or 'damai' in url or 'nc' in url or 'alicdn' in url:
                        if 'ali' in url or 'damai' in url:
                            captcha_frame = frame
                            print(f"   ✓ 找到候选 iframe [{i}]: {frame.url[:100]}")
                            break
                if captcha_frame:
                    break
                await asyncio.sleep(1)
            
            if not captcha_frame:
                print("   ❌ 未找到验证码 iframe")
                # 检查是否有任何弹窗或遮罩
                popup = await page.query_selector('.baxia-dialog, .bx-content, [class*="captcha"]')
                if popup:
                    print(f"   ⚠️  发现弹窗元素")
                    await popup.screenshot()
                await asyncio.sleep(300)
                return
            
            # 在iframe内查找元素
            print("\n📋 分析 iframe 内容...")
            
            # 获取iframe位置
            frame_bounds = await captcha_frame.bounding_box()
            print(f"   iframe 位置: {frame_bounds}")
            
            # 获取iframe内HTML
            html = await captcha_frame.content()
            print(f"   iframe HTML 长度: {len(html)} chars")
            
            # 查找滑块
            print("\n🎯 查找滑块元素...")
            slider_selectors = [
                '.nc_iconfont.btn_slide',
                '.btn_slide',
                '#nc_1_n1z',
                '[class*="slide"]',
                '[class*="slider"]',
                '[id*="nc_"]'
            ]
            
            for selector in slider_selectors:
                el = await captcha_frame.query_selector(selector)
                if el:
                    box = await el.bounding_box()
                    print(f"   ✓ {selector}: {box}")
                else:
                    print(f"   ✗ {selector}: 未找到")
            
            # 查找滑轨
            print("\n📏 查找滑轨...")
            track_selectors = [
                '#nc_1__scale_text',
                '.nc-lang-cnt',
                '[class*="track"]',
                '[class*="bar"]'
            ]
            
            for selector in track_selectors:
                el = await captcha_frame.query_selector(selector)
                if el:
                    box = await el.bounding_box()
                    print(f"   ✓ {selector}: {box}")
                else:
                    print(f"   ✗ {selector}: 未找到")
            
            # 获取iframe内的body text
            try:
                text = await captcha_frame.text_content('body')
                print(f"\n📝 iframe 文本内容 (前200字):\n   {text[:200].replace(chr(10), chr(10) + '   ')}")
            except Exception as e:
                print(f"   获取文本失败: {e}")
            
            # 保存完整HTML
            with open(f"{debug_dir}/damai_{timestamp}_iframe.html", 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"\n📄 iframe HTML 已保存: damai_{timestamp}_iframe.html")
            
            await page.screenshot(path=f"{debug_dir}/damai_{timestamp}_04_captcha.png", full_page=True)
            
            print("\n⏸️  浏览器保持打开60秒，请观察...")
            print("   观察点:")
            print("   1. 是否有验证码出现")
            print("   2. 滑块是否可以拖动")
            print("   3. 拖动后是否验证成功")
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_captcha())
