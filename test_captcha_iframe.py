#!/usr/bin/env python3
"""
测试 iframe 内的滑块拖拽 - 关键是要在 iframe 内操作
"""
import asyncio
import math
import random
from playwright.async_api import async_playwright
import os
from datetime import datetime

async def human_like_drag_in_frame(frame, start_x: int, start_y: int, distance: int):
    """在 iframe 内执行人类化拖拽"""
    print(f"\n🎯 iframe 内拖拽: ({start_x}, {start_y}) → {distance}px")
    
    # 注意：这里使用 frame 而不是 page
    await frame.mouse.move(start_x, start_y)
    await asyncio.sleep(random.uniform(0.1, 0.2))
    await frame.mouse.down()
    await asyncio.sleep(random.uniform(0.1, 0.15))
    
    # 初始快速拖动
    initial_distance = random.randint(8, 15)
    print(f"   📍 初始拖动 {initial_distance}px")
    for pixel in range(initial_distance):
        y_offset = math.log(1 + pixel) * 0.5
        await frame.mouse.move(start_x + pixel, start_y + y_offset)
        await asyncio.sleep(0.03)
    
    # 主要拖拽
    print(f"   🚀 主要拖拽")
    remaining_distance = distance - initial_distance
    steps = 50
    for i in range(steps):
        progress = i / steps
        eased_progress = progress * progress * (3 - 2 * progress)
        current_pixel = initial_distance + int(remaining_distance * eased_progress)
        y_offset = math.log(1 + current_pixel) * 0.5 + random.uniform(-1, 1)
        await frame.mouse.move(start_x + current_pixel, start_y + y_offset)
        
        if progress < 0.3 or progress > 0.7:
            await asyncio.sleep(random.uniform(0.015, 0.025))
        else:
            await asyncio.sleep(random.uniform(0.008, 0.012))
        
        if i % (steps // 4) == 0 and i > 0:
            print(f"      → {int(progress * 100)}%")
    
    # Overshoot 和回退
    print(f"   🎯 Overshoot")
    overshoot = random.randint(3, 8)
    final_x = start_x + distance
    await frame.mouse.move(final_x + overshoot, start_y + random.uniform(-1, 1), steps=15)
    await asyncio.sleep(0.05)
    await frame.mouse.move(final_x, start_y, steps=10)
    await asyncio.sleep(random.uniform(0.15, 0.25))
    
    await frame.mouse.up()
    print(f"   ✅ 拖拽完成")


async def test_iframe_captcha():
    """测试 iframe 内的验证码拖拽"""
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
            # 访问首页
            print("\n📄 访问大麦网首页...")
            await page.goto("https://www.damai.cn/", wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # 找到搜索框
            print("\n🔍 查找搜索框...")
            search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=10000)
            
            # 输入搜索关键词
            print("\n⌨️  输入: 演唱会")
            await search_input.click()
            await asyncio.sleep(0.5)
            for char in "演唱会":
                await search_input.type(char, delay=random.randint(100, 300))
            
            await asyncio.sleep(1)
            
            # 提交搜索
            print("\n⏎ 提交搜索...")
            await page.keyboard.press('Enter')
            await asyncio.sleep(3)
            
            # 等待验证码 iframe 出现
            print("\n⏳ 等待验证码 iframe...")
            iframe_element = None
            for i in range(20):
                iframes = page.frames
                for frame in iframes:
                    if 'captcha' in frame.url.lower() or 'nc' in frame.url.lower():
                        iframe_element = frame
                        print(f"   ✓ 找到验证码 iframe: {frame.url[:80]}...")
                        break
                if iframe_element:
                    break
                await asyncio.sleep(0.5)
            
            if not iframe_element:
                print("   ❌ 未找到验证码 iframe")
                print(f"   当前所有 frames: {[f.url[:50] for f in page.frames]}")
                
                screenshot_path = f"{debug_dir}/iframe_{timestamp}_no_captcha.png"
                await page.screenshot(path=screenshot_path)
                print(f"📸 截图: {screenshot_path}")
                
                print("\n⏸️  浏览器保持打开，请手动检查...")
                await asyncio.sleep(300)
                return
            
            # 保存验证码出现时的截图
            screenshot_path = f"{debug_dir}/iframe_{timestamp}_01_captcha.png"
            await page.screenshot(path=screenshot_path)
            print(f"📸 验证码截图: {screenshot_path}")
            
            # 在 iframe 内查找滑块
            print("\n🎯 在 iframe 内查找滑块...")
            slider_selectors = [
                '.nc_iconfont.btn_slide',
                '.btn_slide',
                'span.nc-lang-cnt',
                '#nc_1_n1z',
                'span[id*="nc_"]'
            ]
            
            slider = None
            slider_box = None
            for selector in slider_selectors:
                try:
                    slider = await iframe_element.query_selector(selector)
                    if slider:
                        slider_box = await slider.bounding_box()
                        if slider_box:
                            print(f"   ✓ 找到滑块: {selector}")
                            print(f"   iframe 内坐标: {slider_box}")
                            break
                except Exception as e:
                    print(f"   尝试 {selector}: {e}")
            
            if not slider_box:
                print("   ⚠️  未找到滑块，尝试获取整个滑动条...")
                # 尝试找滑动条
                track_selectors = [
                    '#nc_1__scale_text',
                    '.nc-lang-cnt',
                    'div[id*="scale"]'
                ]
                for selector in track_selectors:
                    try:
                        track = await iframe_element.query_selector(selector)
                        if track:
                            track_box = await track.bounding_box()
                            if track_box:
                                print(f"   ✓ 找到滑动条: {selector}")
                                print(f"   滑动条坐标: {track_box}")
                                # 滑块在滑动条左侧
                                slider_box = {
                                    'x': track_box['x'],
                                    'y': track_box['y'] + track_box['height'] / 2,
                                    'width': 40,
                                    'height': track_box['height']
                                }
                                break
                    except Exception as e:
                        print(f"   尝试 {selector}: {e}")
            
            if slider_box:
                # 计算滑块中心点（iframe 内的坐标）
                slider_x = int(slider_box['x'] + slider_box['width'] / 2)
                slider_y = int(slider_box['y'] + slider_box['height'] / 2)
                drag_distance = 260
                
                print(f"\n🎮 准备拖拽...")
                print(f"   iframe 内起点: ({slider_x}, {slider_y})")
                print(f"   拖拽距离: {drag_distance}px")
                
                # 在 iframe 内执行拖拽
                await human_like_drag_in_frame(iframe_element, slider_x, slider_y, drag_distance)
                
                # 等待验证结果
                await asyncio.sleep(3)
                
                screenshot_path = f"{debug_dir}/iframe_{timestamp}_02_after_drag.png"
                await page.screenshot(path=screenshot_path)
                print(f"📸 拖拽后截图: {screenshot_path}")
                
                # 检查是否成功
                print("\n🔍 检查验证结果...")
                await asyncio.sleep(2)
                
                # 检查 iframe 是否还存在
                iframes_after = [f for f in page.frames if 'captcha' in f.url.lower() or 'nc' in f.url.lower()]
                if len(iframes_after) == 0:
                    print("   ✅ 验证码 iframe 已消失 - 可能验证成功！")
                else:
                    print("   ⚠️  验证码 iframe 仍存在")
                    # 检查 iframe 内的文本
                    try:
                        text = await iframe_element.text_content('body')
                        if '成功' in text or '通过' in text:
                            print("   ✅ 检测到成功提示")
                        elif '失败' in text or '错误' in text:
                            print("   ❌ 检测到失败提示")
                        else:
                            print(f"   iframe 内容: {text[:100]}")
                    except:
                        pass
                
                screenshot_path = f"{debug_dir}/iframe_{timestamp}_03_final.png"
                await page.screenshot(path=screenshot_path)
                print(f"📸 最终截图: {screenshot_path}")
            else:
                print("   ❌ 无法定位滑块")
            
            print("\n✅ 测试完成！")
            print(f"📁 截图保存在: {debug_dir}/")
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
    asyncio.run(test_iframe_captcha())
