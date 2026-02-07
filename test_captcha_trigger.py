#!/usr/bin/env python3
"""
测试触发验证码的正确流程 - 从首页开始搜索
"""
import asyncio
import math
import random
from playwright.async_api import async_playwright
import os
from datetime import datetime

async def human_like_drag(page, start_x: int, start_y: int, distance: int):
    """人类化拖拽"""
    print(f"\n🎯 人类化拖拽: ({start_x}, {start_y}) → {distance}px")
    
    await page.mouse.move(start_x, start_y)
    await asyncio.sleep(random.uniform(0.1, 0.2))
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.1, 0.15))
    
    # 初始快速拖动
    initial_distance = random.randint(8, 15)
    for pixel in range(initial_distance):
        y_offset = math.log(1 + pixel) * 0.5
        await page.mouse.move(start_x + pixel, start_y + y_offset)
        await asyncio.sleep(0.03)
    
    # 主要拖拽
    remaining_distance = distance - initial_distance
    steps = 50
    for i in range(steps):
        progress = i / steps
        eased_progress = progress * progress * (3 - 2 * progress)
        current_pixel = initial_distance + int(remaining_distance * eased_progress)
        y_offset = math.log(1 + current_pixel) * 0.5 + random.uniform(-1, 1)
        await page.mouse.move(start_x + current_pixel, start_y + y_offset)
        
        if progress < 0.3 or progress > 0.7:
            await asyncio.sleep(random.uniform(0.015, 0.025))
        else:
            await asyncio.sleep(random.uniform(0.008, 0.012))
    
    # Overshoot 和回退
    overshoot = random.randint(3, 8)
    final_x = start_x + distance
    await page.mouse.move(final_x + overshoot, start_y + random.uniform(-1, 1), steps=15)
    await asyncio.sleep(0.05)
    await page.mouse.move(final_x, start_y, steps=10)
    await asyncio.sleep(random.uniform(0.15, 0.25))
    
    await page.mouse.up()
    print(f"   ✅ 拖拽完成")


async def wait_for_captcha(page, timeout=10):
    """等待验证码出现"""
    print(f"\n⏳ 等待验证码出现 (最多 {timeout}秒)...")
    
    selectors = [
        '.nc_wrapper',
        '#nc_1_wrapper', 
        'div[id*="nc_"]',
        'iframe[src*="captcha"]',
        'div[class*="captcha"]'
    ]
    
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < timeout:
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                for elem in elements:
                    if await elem.is_visible():
                        print(f"   ✓ 找到验证码: {selector}")
                        return True
            except:
                pass
        await asyncio.sleep(0.5)
    
    print(f"   ⚠️  {timeout}秒内未检测到验证码")
    return False


async def test_captcha_from_homepage():
    """从首页开始，触发验证码"""
    debug_dir = "debug_captcha"
    os.makedirs(debug_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async with async_playwright() as p:
        print("🌐 启动浏览器...")
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        
        page = await context.new_page()
        
        try:
            # 1. 访问首页
            print("\n📄 访问大麦网首页...")
            await page.goto("https://www.damai.cn/", wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            screenshot_path = f"{debug_dir}/trigger_{timestamp}_01_homepage.png"
            await page.screenshot(path=screenshot_path)
            print(f"📸 首页截图: {screenshot_path}")
            
            # 2. 找到搜索框并输入
            print("\n🔍 查找搜索框...")
            search_selectors = [
                'input[placeholder*="搜索"]',
                'input[placeholder*="演出"]',
                'input.search-input',
                'input[type="text"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=5000)
                    if search_input and await search_input.is_visible():
                        print(f"   ✓ 找到搜索框: {selector}")
                        break
                except:
                    continue
            
            if not search_input:
                print("   ❌ 未找到搜索框，尝试点击搜索图标...")
                await page.click('text=搜索')
                await asyncio.sleep(1)
                search_input = await page.wait_for_selector('input[type="text"]', timeout=5000)
            
            # 3. 输入搜索关键词
            print("\n⌨️  输入搜索关键词: 演唱会")
            await search_input.click()
            await asyncio.sleep(0.5)
            
            # 逐字输入，模拟人类
            keyword = "演唱会"
            for char in keyword:
                await search_input.type(char, delay=random.randint(100, 300))
            
            await asyncio.sleep(1)
            screenshot_path = f"{debug_dir}/trigger_{timestamp}_02_typed.png"
            await page.screenshot(path=screenshot_path)
            print(f"📸 输入后截图: {screenshot_path}")
            
            # 4. 按 Enter 提交搜索
            print("\n⏎ 按 Enter 提交搜索...")
            await page.keyboard.press('Enter')
            await asyncio.sleep(2)
            
            screenshot_path = f"{debug_dir}/trigger_{timestamp}_03_after_enter.png"
            await page.screenshot(path=screenshot_path)
            print(f"📸 提交后截图: {screenshot_path}")
            
            # 5. 等待验证码出现
            captcha_appeared = await wait_for_captcha(page, timeout=10)
            
            if captcha_appeared:
                print("\n✅ 验证码已出现！")
                screenshot_path = f"{debug_dir}/trigger_{timestamp}_04_captcha_visible.png"
                await page.screenshot(path=screenshot_path)
                print(f"📸 验证码截图: {screenshot_path}")
                
                # 6. 尝试定位滑块
                print("\n🎯 定位滑块位置...")
                slider_selectors = [
                    '.nc_iconfont.btn_slide',
                    '.btn_slide',
                    'span.nc-lang-cnt',
                    'div[id*="nc_"][id*="scale"]'
                ]
                
                slider_found = False
                for selector in slider_selectors:
                    try:
                        slider = await page.query_selector(selector)
                        if slider and await slider.is_visible():
                            box = await slider.bounding_box()
                            if box:
                                slider_x = int(box['x'] + box['width'] / 2)
                                slider_y = int(box['y'] + box['height'] / 2)
                                print(f"   ✓ 找到滑块: {selector}")
                                print(f"   位置: ({slider_x}, {slider_y})")
                                slider_found = True
                                
                                # 7. 执行拖拽
                                await human_like_drag(page, slider_x, slider_y, 260)
                                
                                await asyncio.sleep(3)
                                screenshot_path = f"{debug_dir}/trigger_{timestamp}_05_after_drag.png"
                                await page.screenshot(path=screenshot_path)
                                print(f"📸 拖拽后截图: {screenshot_path}")
                                break
                    except Exception as e:
                        print(f"   尝试 {selector} 失败: {e}")
                
                if not slider_found:
                    print("   ⚠️  未找到滑块元素，使用固定坐标...")
                    # 使用页面中心附近的坐标
                    await human_like_drag(page, 640, 400, 260)
                    await asyncio.sleep(3)
                    screenshot_path = f"{debug_dir}/trigger_{timestamp}_05_after_drag.png"
                    await page.screenshot(path=screenshot_path)
                    print(f"📸 拖拽后截图: {screenshot_path}")
            else:
                print("\n⚠️  验证码未出现，可能:")
                print("   1. 网站未检测到自动化")
                print("   2. 当前IP/账号不需要验证")
                print("   3. 验证码加载延迟")
            
            # 最终截图
            await asyncio.sleep(2)
            screenshot_path = f"{debug_dir}/trigger_{timestamp}_06_final.png"
            await page.screenshot(path=screenshot_path)
            print(f"📸 最终截图: {screenshot_path}")
            
            print("\n✅ 测试完成！")
            print(f"📁 所有截图保存在: {debug_dir}/")
            print("\n⏸️  浏览器保持打开，请手动检查...")
            print("   按 Ctrl+C 关闭")
            
            await asyncio.sleep(300)
            
        except KeyboardInterrupt:
            print("\n👋 用户中断")
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_captcha_from_homepage())
