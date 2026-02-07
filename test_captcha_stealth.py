#!/usr/bin/env python3
"""
使用 playwright-stealth 测试滑块验证码
关键：在访问页面前应用 stealth，绕过反自动化检测
"""
import asyncio
import math
import random
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import os
from datetime import datetime

async def perfect_drag(page, start_x: int, start_y: int, distance: int):
    """
    拟人化拖拽函数：
    1. 非线性轨迹（先快后慢）
    2. Y轴随机抖动
    3. 超出后回退
    """
    print(f"\n🎯 拟人化拖拽: ({start_x}, {start_y}) → {distance}px")
    
    # 移动到起点并按下
    await page.mouse.move(start_x, start_y)
    await asyncio.sleep(random.uniform(0.2, 0.5))
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.2, 0.5))
    print(f"   🔽 按下鼠标")
    
    # 生成非线性轨迹（先快后慢）
    current_x = start_x
    steps = 30
    print(f"   🚀 开始拖拽 ({steps} 步)")
    
    for i in range(steps):
        # 使用指数衰减让每一步距离不等
        remaining = distance - (current_x - start_x)
        diff = remaining / (steps - i)
        move_x = diff + random.uniform(-2, 3)  # 加入随机微调
        current_x += move_x
        
        # Y轴必须有随机抖动，否则会被判为直线
        y_jitter = start_y + random.uniform(-2, 2)
        await page.mouse.move(current_x, y_jitter)
        await asyncio.sleep(random.uniform(0.01, 0.02))
        
        if i % 10 == 0:
            print(f"      → {int((i/steps)*100)}% (x={int(current_x)})")
    
    # 最后微调：回退动作（人类常滑过头再往回拉）
    print(f"   🎯 超出后回退")
    await page.mouse.move(start_x + distance + 3, start_y)
    await asyncio.sleep(0.1)
    await page.mouse.move(start_x + distance, start_y)
    
    # 释放
    await asyncio.sleep(0.2)
    await page.mouse.up()
    print(f"   🔼 释放鼠标")
    print(f"   ✅ 拖拽完成")


async def test_bot_detection(url: str, name: str):
    """测试机器人检测网站"""
    print(f"\n{'='*60}")
    print(f"🤖 测试: {name}")
    print(f"{'='*60}")
    
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
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # 【关键步骤】在访问 URL 之前应用 Stealth
        print("🔒 应用 Stealth 插件...")
        await stealth_async(page)
        
        try:
            print(f"📄 访问: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # 保存截图
            screenshot_path = f"debug_captcha/stealth_{name.replace(' ', '_')}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 截图保存: {screenshot_path}")
            
            print(f"\n✅ 请查看浏览器窗口和截图")
            print(f"   绿色 Pass = Stealth 生效")
            print(f"   红色 Fail = 被检测为机器人")
            print(f"\n⏸️  浏览器保持打开 30 秒...")
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"❌ 错误: {e}")
        finally:
            await browser.close()


async def test_damai_captcha_with_stealth():
    """使用 Stealth 测试大麦验证码"""
    debug_dir = "debug_captcha"
    os.makedirs(debug_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n{'='*60}")
    print(f"🎭 测试大麦网滑块验证码 (with Stealth)")
    print(f"{'='*60}")
    
    async with async_playwright() as p:
        print("\n🌐 启动浏览器...")
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # 【关键】应用 Stealth
        print("🔒 应用 Stealth 插件...")
        await stealth_async(page)
        
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
            screenshot_path = f"{debug_dir}/stealth_{timestamp}_01_typed.png"
            await page.screenshot(path=screenshot_path)
            print(f"📸 输入后: {screenshot_path}")
            
            # 提交搜索
            print("\n⏎ 提交搜索...")
            await page.keyboard.press('Enter')
            await asyncio.sleep(3)
            
            screenshot_path = f"{debug_dir}/stealth_{timestamp}_02_after_enter.png"
            await page.screenshot(path=screenshot_path)
            print(f"📸 提交后: {screenshot_path}")
            
            # 等待验证码 iframe
            print("\n⏳ 等待验证码 iframe...")
            iframe_element = None
            for i in range(20):
                iframes = page.frames
                for frame in iframes:
                    if 'captcha' in frame.url.lower() or 'nc' in frame.url.lower():
                        iframe_element = frame
                        print(f"   ✓ 找到验证码 iframe")
                        break
                if iframe_element:
                    break
                await asyncio.sleep(0.5)
            
            if not iframe_element:
                print("   ⚠️  未找到验证码 iframe")
                screenshot_path = f"{debug_dir}/stealth_{timestamp}_03_no_captcha.png"
                await page.screenshot(path=screenshot_path)
                print(f"📸 {screenshot_path}")
                print("\n可能原因:")
                print("   1. Stealth 生效，网站未触发验证码")
                print("   2. 验证码加载延迟")
                print("\n⏸️  浏览器保持打开，请手动检查...")
                await asyncio.sleep(60)
                return
            
            screenshot_path = f"{debug_dir}/stealth_{timestamp}_03_captcha.png"
            await page.screenshot(path=screenshot_path)
            print(f"📸 验证码出现: {screenshot_path}")
            
            # 在 iframe 内查找滑块
            print("\n🎯 在 iframe 内查找滑块...")
            slider_selectors = [
                '.nc_iconfont.btn_slide',
                '.btn_slide',
                'span.nc-lang-cnt',
                '#nc_1_n1z',
                'span[id*="nc_"]',
                '.nc-lang-cnt'
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
                            print(f"   坐标: {slider_box}")
                            break
                except Exception as e:
                    pass
            
            if not slider_box:
                print("   ⚠️  未找到滑块元素，尝试查找滑动条...")
                track_selectors = [
                    '#nc_1__scale_text',
                    '.nc-lang-cnt',
                    'div[id*="scale"]',
                    'span[id*="scale"]'
                ]
                for selector in track_selectors:
                    try:
                        track = await iframe_element.query_selector(selector)
                        if track:
                            track_box = await track.bounding_box()
                            if track_box:
                                print(f"   ✓ 找到滑动条: {selector}")
                                print(f"   滑动条坐标: {track_box}")
                                # 滑块在左侧
                                slider_box = {
                                    'x': track_box['x'] - 20,
                                    'y': track_box['y'],
                                    'width': 40,
                                    'height': track_box['height']
                                }
                                break
                    except Exception as e:
                        pass
            
            if slider_box:
                # 计算滑块中心点
                slider_x = int(slider_box['x'] + slider_box['width'] / 2)
                slider_y = int(slider_box['y'] + slider_box['height'] / 2)
                drag_distance = 260
                
                print(f"\n🎮 准备拖拽...")
                print(f"   起点: ({slider_x}, {slider_y})")
                print(f"   距离: {drag_distance}px")
                
                # 使用拟人化拖拽
                await perfect_drag(page, slider_x, slider_y, drag_distance)
                
                # 等待验证结果
                await asyncio.sleep(3)
                
                screenshot_path = f"{debug_dir}/stealth_{timestamp}_04_after_drag.png"
                await page.screenshot(path=screenshot_path)
                print(f"\n📸 拖拽后: {screenshot_path}")
                
                # 检查验证结果
                print("\n🔍 检查验证结果...")
                await asyncio.sleep(2)
                
                iframes_after = [f for f in page.frames if 'captcha' in f.url.lower() or 'nc' in f.url.lower()]
                if len(iframes_after) == 0:
                    print("   ✅ 验证码 iframe 已消失 - 验证成功！")
                else:
                    print("   ⚠️  验证码 iframe 仍存在")
                    try:
                        text = await iframe_element.text_content('body')
                        if '成功' in text or '通过' in text:
                            print("   ✅ 检测到成功提示")
                        else:
                            print(f"   iframe 内容: {text[:100] if text else 'empty'}")
                    except:
                        pass
                
                screenshot_path = f"{debug_dir}/stealth_{timestamp}_05_final.png"
                await page.screenshot(path=screenshot_path)
                print(f"📸 最终: {screenshot_path}")
            else:
                print("   ❌ 无法定位滑块")
                print("   可能原因:")
                print("   1. iframe 内元素选择器不正确")
                print("   2. 验证码类型不同")
                print("   3. 需要等待更长时间")
            
            print("\n✅ 测试完成！")
            print(f"📁 所有截图: {debug_dir}/")
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


async def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("🔬 Playwright Stealth 测试套件")
    print("="*60)
    
    # 1. 测试机器人检测网站
    print("\n【第一步】测试机器人检测网站")
    print("-" * 60)
    
    await test_bot_detection(
        "https://bot.sannysoft.com/",
        "Sannysoft Bot Detector"
    )
    
    await test_bot_detection(
        "https://arh.antoinevastel.com/bots/areyouheadless",
        "Are You Headless"
    )
    
    # 2. 测试大麦验证码
    print("\n【第二步】测试大麦网滑块验证码")
    print("-" * 60)
    
    await test_damai_captcha_with_stealth()


if __name__ == "__main__":
    asyncio.run(main())
