#!/usr/bin/env python3
"""
测试人类化的滑块拖拽 - 借鉴 Shopee CAPTCHA Solver 的技术
"""
import asyncio
import math
import random
from playwright.async_api import async_playwright
import os
from datetime import datetime

async def human_like_drag(page, start_x: int, start_y: int, distance: int):
    """
    使用人类化的拖拽方式，借鉴 Shopee solver:
    1. 使用对数曲线产生 Y 轴微小变化
    2. 小步移动，每步有延迟
    3. 最后有 overshoot（超出）然后回退
    """
    print(f"\n🎯 人类化拖拽开始")
    print(f"   起点: ({start_x}, {start_y})")
    print(f"   距离: {distance}px")
    
    # 移动到起点
    await page.mouse.move(start_x, start_y)
    await asyncio.sleep(random.uniform(0.1, 0.2))
    
    # 按下鼠标
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.1, 0.15))
    
    # 第一阶段：快速移动一小段距离（模拟人类按下后的初始拖动）
    initial_distance = random.randint(8, 15)
    print(f"   📍 初始快速拖动 {initial_distance}px")
    for pixel in range(initial_distance):
        # 使用对数曲线产生 Y 轴微小变化
        y_offset = math.log(1 + pixel) * 0.5
        await page.mouse.move(start_x + pixel, start_y + y_offset)
        await asyncio.sleep(0.03)
    
    # 第二阶段：主要拖拽（使用变速和曲线）
    print(f"   🚀 主要拖拽阶段")
    remaining_distance = distance - initial_distance
    steps = 50
    
    for i in range(steps):
        progress = i / steps
        # 使用 ease-in-out 曲线
        eased_progress = progress * progress * (3 - 2 * progress)
        current_pixel = initial_distance + int(remaining_distance * eased_progress)
        
        # Y 轴使用对数曲线 + 随机抖动
        y_offset = math.log(1 + current_pixel) * 0.5 + random.uniform(-1, 1)
        
        await page.mouse.move(start_x + current_pixel, start_y + y_offset)
        
        # 变速：开始慢，中间快，结束慢
        if progress < 0.3 or progress > 0.7:
            await asyncio.sleep(random.uniform(0.015, 0.025))
        else:
            await asyncio.sleep(random.uniform(0.008, 0.012))
        
        if i % (steps // 4) == 0 and i > 0:
            print(f"      → {int(progress * 100)}% (x={start_x + current_pixel})")
    
    # 第三阶段：overshoot（超出目标）然后回退
    print(f"   🎯 Overshoot 和回退")
    overshoot = random.randint(3, 8)
    final_x = start_x + distance
    
    # 超出
    await page.mouse.move(final_x + overshoot, start_y + random.uniform(-1, 1), steps=15)
    await asyncio.sleep(0.05)
    
    # 回退到准确位置
    await page.mouse.move(final_x, start_y, steps=10)
    await asyncio.sleep(random.uniform(0.15, 0.25))
    
    # 释放鼠标
    print(f"   ✅ 释放鼠标")
    await page.mouse.up()
    
    print(f"   🏁 拖拽完成: 总距离 {distance}px")


async def test_captcha_drag():
    """测试人类化的滑块拖拽"""
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
        
        # 设置反检测
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # 注入反检测脚本
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = await context.new_page()
        
        try:
            # 访问搜索页面
            url = "https://search.damai.cn/search.html?keyword=演唱会&spm=a2oeg.home.searchtxt.dsearchbtn"
            print(f"📄 访问: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 等待页面加载
            await asyncio.sleep(3)
            
            # 保存初始截图
            screenshot_path = f"{debug_dir}/humanlike_{timestamp}_00_initial.png"
            await page.screenshot(path=screenshot_path, full_page=False)
            print(f"📸 初始截图: {screenshot_path}")
            
            # 等待验证码出现
            print("\n⏳ 等待验证码出现...")
            await asyncio.sleep(5)
            
            # 检查是否有验证码
            captcha_visible = False
            try:
                # 尝试多个可能的验证码选择器
                selectors = [
                    '.nc_wrapper',
                    '#nc_1_wrapper',
                    'div[id*="nc_"]',
                    'div[class*="nc_"]'
                ]
                
                for selector in selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"✓ 找到验证码元素: {selector}")
                        captcha_visible = True
                        break
            except:
                pass
            
            if not captcha_visible:
                print("⚠️  验证码可能未出现，尝试继续...")
            
            # 保存验证码截图
            screenshot_path = f"{debug_dir}/humanlike_{timestamp}_01_captcha.png"
            await page.screenshot(path=screenshot_path, full_page=False)
            print(f"📸 验证码截图: {screenshot_path}")
            
            # 使用固定坐标拖拽（基于之前的截图分析）
            # 滑块大约在 x=610, y=563 位置
            slider_x = 610
            slider_y = 563
            drag_distance = 260
            
            print(f"\n🎮 准备拖拽滑块...")
            print(f"   坐标: ({slider_x}, {slider_y})")
            print(f"   距离: {drag_distance}px")
            
            # 执行人类化拖拽
            await human_like_drag(page, slider_x, slider_y, drag_distance)
            
            # 等待验证结果
            await asyncio.sleep(2)
            
            # 保存拖拽后截图
            screenshot_path = f"{debug_dir}/humanlike_{timestamp}_02_after_drag.png"
            await page.screenshot(path=screenshot_path, full_page=False)
            print(f"📸 拖拽后截图: {screenshot_path}")
            
            # 检查验证码是否消失
            await asyncio.sleep(2)
            screenshot_path = f"{debug_dir}/humanlike_{timestamp}_03_final.png"
            await page.screenshot(path=screenshot_path, full_page=False)
            print(f"📸 最终截图: {screenshot_path}")
            
            print("\n✅ 测试完成！")
            print(f"📁 截图保存在: {debug_dir}/")
            print("\n⏸️  浏览器保持打开，请手动检查结果...")
            print("   按 Ctrl+C 关闭浏览器")
            
            # 保持浏览器打开
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
    asyncio.run(test_captcha_drag())
