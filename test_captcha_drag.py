#!/usr/bin/env python3
"""
测试滑块验证码拖拽 - 独立测试脚本
直接打开大麦搜索页面，测试各种拖拽方法
"""

import asyncio
import base64
import os
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import openai

load_dotenv()

# Azure OpenAI 配置
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")

# 配置 Azure OpenAI
if AZURE_OPENAI_API_KEY:
    openai.api_type = "azure"
    openai.api_key = AZURE_OPENAI_API_KEY
    openai.api_base = AZURE_OPENAI_ENDPOINT
    openai.api_version = AZURE_OPENAI_API_VERSION


async def call_gpt_vision(screenshot_base64: str, question: str):
    """调用 GPT Vision 分析截图"""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"}}
            ]
        }
    ]
    
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: openai.ChatCompletion.create(
                engine=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                temperature=0.3,
                max_completion_tokens=500
            )
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"Error: {e}"


async def save_screenshot(page, filename):
    """保存截图"""
    screenshot_bytes = await page.screenshot(full_page=False)
    with open(filename, "wb") as f:
        f.write(screenshot_bytes)
    print(f"📸 保存截图: {filename}")
    return base64.b64encode(screenshot_bytes).decode('utf-8')


async def method1_playwright_drag_to(page):
    """方法1: 使用 Playwright 的 drag_to"""
    print("\n" + "="*60)
    print("方法1: Playwright drag_to")
    print("="*60)
    
    # 查找滑块元素
    selectors = [
        ".nc_iconfont.btn_slide",
        ".btn_slide",
        "span.btn_slide",
        "[class*='slide']"
    ]
    
    slider = None
    for sel in selectors:
        try:
            element = page.locator(sel).first
            if await element.count() > 0:
                slider = element
                print(f"✓ 找到滑块: {sel}")
                break
        except:
            continue
    
    if not slider:
        print("❌ 未找到滑块元素")
        return False
    
    try:
        # 获取滑块位置
        box = await slider.bounding_box()
        if box:
            print(f"滑块位置: x={box['x']}, y={box['y']}, width={box['width']}, height={box['height']}")
            
            # 拖拽到右侧
            target_x = box['x'] + 300
            target_y = box['y'] + box['height'] / 2
            
            print(f"拖拽到: x={target_x}, y={target_y}")
            await slider.drag_to(
                page.locator("body"),
                target_position={"x": int(target_x), "y": int(target_y)},
                force=True
            )
            
            await asyncio.sleep(2)
            await save_screenshot(page, "test_method1_result.png")
            return True
    except Exception as e:
        print(f"❌ 方法1失败: {e}")
        return False


async def method2_mouse_drag(page):
    """方法2: 使用 Playwright mouse API - 增强版"""
    print("\n" + "="*60)
    print("方法2: Playwright Mouse API (增强版)")
    print("="*60)
    
    # 先检查所有 frame
    all_frames = page.frames
    print(f"检查 {len(all_frames)} 个 frame...")
    
    box = None
    target_frame = page
    
    # 扩展的选择器列表
    selectors = [
        ".nc_iconfont.btn_slide",
        ".btn_slide", 
        "span.btn_slide",
        "[class*='slide']",
        "[class*='btn_slide']",
        ".nc-lang-cnt span",
        "#nc_1_n1z",
    ]
    
    # 在所有 frame 中查找
    for frame in all_frames:
        for sel in selectors:
            try:
                element = frame.locator(sel).first
                if await element.count() > 0:
                    box = await element.bounding_box()
                    if box and box['width'] > 0:
                        target_frame = frame
                        print(f"✓ 在 frame 中找到滑块: {sel}")
                        print(f"  位置: ({box['x']}, {box['y']}), 大小: {box['width']}x{box['height']}")
                        break
            except:
                continue
        if box:
            break
    
    if not box:
        print("❌ 未找到滑块，尝试使用固定坐标")
        # 根据截图，滑块大约在左下角
        box = {'x': 130, 'y': 525, 'width': 50, 'height': 40}
        print(f"使用估计坐标: ({box['x']}, {box['y']})")
    
    try:
        # 使用滑块中心点作为起点
        start_x = box['x'] + box['width'] / 2
        start_y = box['y'] + box['height'] / 2
        distance = 500  # 增加拖拽距离
        
        print(f"起点: ({start_x}, {start_y})")
        print(f"拖拽距离: {distance}px")
        
        # 移动到滑块
        await page.mouse.move(start_x, start_y)
        await asyncio.sleep(0.3)
        
        # 按下鼠标
        await page.mouse.down()
        await asyncio.sleep(0.2)
        print("✓ 鼠标按下")
        
        # 拖拽
        for i in range(0, distance, 10):
            await page.mouse.move(start_x + i, start_y)
            await asyncio.sleep(0.02)
        
        print(f"✓ 拖拽到 x={start_x + distance}")
        
        # 释放鼠标
        await page.mouse.up()
        print("✓ 鼠标释放")
        
        await asyncio.sleep(2)
        await save_screenshot(page, "test_method2_result.png")
        return True
        
    except Exception as e:
        print(f"❌ 方法2失败: {e}")
        return False


async def method3_javascript_events(page):
    """方法3: 使用 JavaScript 触发事件"""
    print("\n" + "="*60)
    print("方法3: JavaScript Events")
    print("="*60)
    
    script = """
    (async () => {
        // 查找滑块
        const slider = document.querySelector('.nc_iconfont.btn_slide') || 
                      document.querySelector('.btn_slide') ||
                      document.querySelector('[class*="slide"]');
        
        if (!slider) {
            return {success: false, error: 'Slider not found'};
        }
        
        const rect = slider.getBoundingClientRect();
        const startX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height / 2;
        const distance = 300;
        
        // mousedown
        const mousedown = new MouseEvent('mousedown', {
            bubbles: true,
            cancelable: true,
            view: window,
            clientX: startX,
            clientY: startY,
            button: 0
        });
        slider.dispatchEvent(mousedown);
        
        // 逐步移动
        for (let i = 0; i <= distance; i += 10) {
            const mousemove = new MouseEvent('mousemove', {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: startX + i,
                clientY: startY,
                button: 0
            });
            document.dispatchEvent(mousemove);
            await new Promise(r => setTimeout(r, 20));
        }
        
        // mouseup
        const mouseup = new MouseEvent('mouseup', {
            bubbles: true,
            cancelable: true,
            view: window,
            clientX: startX + distance,
            clientY: startY,
            button: 0
        });
        document.dispatchEvent(mouseup);
        
        return {success: true, startX, startY, distance};
    })()
    """
    
    try:
        result = await page.evaluate(script)
        print(f"JavaScript 执行结果: {result}")
        
        await asyncio.sleep(2)
        await save_screenshot(page, "test_method3_result.png")
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ 方法3失败: {e}")
        return False


async def method4_hover_and_drag(page):
    """方法4: 先 hover 再拖拽"""
    print("\n" + "="*60)
    print("方法4: Hover + Drag")
    print("="*60)
    
    selectors = [".nc_iconfont.btn_slide", ".btn_slide", "[class*='slide']"]
    
    slider = None
    for sel in selectors:
        try:
            element = page.locator(sel).first
            if await element.count() > 0:
                slider = element
                print(f"✓ 找到滑块: {sel}")
                break
        except:
            continue
    
    if not slider:
        print("❌ 未找到滑块")
        return False
    
    try:
        # 先 hover
        await slider.hover()
        await asyncio.sleep(0.5)
        print("✓ Hover 滑块")
        
        # 获取位置
        box = await slider.bounding_box()
        if not box:
            return False
        
        start_x = box['x'] + box['width'] / 2
        start_y = box['y'] + box['height'] / 2
        
        # 按下并拖拽
        await page.mouse.move(start_x, start_y)
        await page.mouse.down()
        await asyncio.sleep(0.2)
        
        # 慢速拖拽
        for i in range(0, 300, 5):
            await page.mouse.move(start_x + i, start_y)
            await asyncio.sleep(0.01)
        
        await page.mouse.up()
        print("✓ 拖拽完成")
        
        await asyncio.sleep(2)
        await save_screenshot(page, "test_method4_result.png")
        return True
        
    except Exception as e:
        print(f"❌ 方法4失败: {e}")
        return False


async def inspect_page_structure(page):
    """检查页面结构，查找滑块元素"""
    print("\n🔍 检查页面结构...")
    
    # 检查是否有 iframe
    iframes = page.frames
    print(f"页面中有 {len(iframes)} 个 frame")
    for i, frame in enumerate(iframes):
        print(f"  Frame {i}: {frame.url[:100] if frame.url else 'about:blank'}")
    
    # 尝试多种选择器查找滑块
    selectors_to_try = [
        # 常见的滑块选择器
        ".nc_iconfont.btn_slide",
        ".btn_slide",
        "span.btn_slide",
        "#nc_1_n1z",
        ".nc-lang-cnt",
        # 通配符选择器
        "[class*='slide']",
        "[class*='slider']",
        "[class*='btn']",
        "[id*='nc']",
        # 可能的滑块容器
        ".nc_wrapper",
        "#nc_1__scale_text",
        ".nc_scale",
    ]
    
    print("\n尝试查找滑块元素:")
    found_elements = []
    
    # 在主页面查找
    for selector in selectors_to_try:
        try:
            elements = await page.locator(selector).all()
            if elements:
                for elem in elements:
                    box = await elem.bounding_box()
                    if box:
                        found_elements.append({
                            'selector': selector,
                            'box': box,
                            'frame': 'main'
                        })
                        print(f"  ✓ 主页面找到: {selector} at ({box['x']}, {box['y']})")
        except:
            pass
    
    # 在每个 iframe 中查找
    for i, frame in enumerate(iframes):
        if i == 0:  # 跳过主 frame
            continue
        for selector in selectors_to_try:
            try:
                elements = await frame.locator(selector).all()
                if elements:
                    for elem in elements:
                        box = await elem.bounding_box()
                        if box:
                            found_elements.append({
                                'selector': selector,
                                'box': box,
                                'frame': f'iframe_{i}',
                                'frame_obj': frame
                            })
                            print(f"  ✓ Frame {i} 找到: {selector} at ({box['x']}, {box['y']})")
            except:
                pass
    
    return found_elements


async def main():
    """主测试函数"""
    print("🧪 滑块验证码拖拽测试")
    print("="*60)
    
    url = "https://search.damai.cn/search.html?keyword=%E6%BC%94%E5%94%B1%E4%BC%9A&spm=a2oeg.home.searchtxt.dsearchbtn"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        
        print(f"\n📡 访问: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        
        # 保存初始截图
        screenshot_b64 = await save_screenshot(page, "test_initial.png")
        
        # 检查页面结构
        found_elements = await inspect_page_structure(page)
        
        if not found_elements:
            print("\n❌ 未找到任何滑块元素！")
            print("尝试使用 JavaScript 查找所有可能的元素...")
            
            # 使用 JavaScript 查找所有可能的滑块元素
            js_result = await page.evaluate("""
                () => {
                    const results = [];
                    
                    // 查找所有可能的滑块元素
                    const candidates = [
                        ...document.querySelectorAll('[class*="slide"]'),
                        ...document.querySelectorAll('[class*="btn"]'),
                        ...document.querySelectorAll('[id*="nc"]'),
                    ];
                    
                    candidates.forEach((el, i) => {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            results.push({
                                index: i,
                                tag: el.tagName,
                                class: el.className,
                                id: el.id,
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height
                            });
                        }
                    });
                    
                    return results;
                }
            """)
            
            print(f"\nJavaScript 找到 {len(js_result)} 个候选元素:")
            for elem in js_result[:10]:  # 只显示前10个
                print(f"  - {elem['tag']}.{elem['class']} #{elem['id']} at ({elem['x']}, {elem['y']})")
        
        # 询问 GPT 是否有验证码
        if AZURE_OPENAI_API_KEY:
            print("\n🤖 询问 GPT 是否有验证码...")
            gpt_response = await call_gpt_vision(
                screenshot_b64,
                "页面上是否有滑块验证码？如果有，请描述滑块的位置和特征，以及滑块按钮的颜色。"
            )
            print(f"GPT 回答: {gpt_response}\n")
        
        # 测试各种方法
        methods = [
            ("方法1: drag_to", method1_playwright_drag_to),
            ("方法2: Mouse API", method2_mouse_drag),
            ("方法3: JavaScript", method3_javascript_events),
            ("方法4: Hover+Drag", method4_hover_and_drag),
        ]
        
        for name, method in methods:
            try:
                success = await method(page)
                
                # 等待用户观察结果
                print(f"\n{'✅' if success else '❌'} {name} {'成功' if success else '失败'}")
                print("等待5秒观察结果...")
                await asyncio.sleep(5)
                
                # 询问 GPT 验证是否成功
                if AZURE_OPENAI_API_KEY:
                    screenshot_b64 = await save_screenshot(page, f"test_{name}_gpt_check.png")
                    gpt_check = await call_gpt_vision(
                        screenshot_b64,
                        "验证码是否已经验证成功？滑块是否移动到了正确位置？"
                    )
                    print(f"🤖 GPT 验证结果: {gpt_check}")
                
                # 刷新页面准备下一个测试
                if name != methods[-1][0]:
                    print("\n🔄 刷新页面准备下一个测试...")
                    await page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(3)
                    
            except Exception as e:
                print(f"❌ {name} 异常: {e}")
        
        print("\n" + "="*60)
        print("测试完成！请查看截图文件：")
        print("  - test_initial.png")
        print("  - test_method1_result.png")
        print("  - test_method2_result.png")
        print("  - test_method3_result.png")
        print("  - test_method4_result.png")
        print("="*60)
        
        # 保持浏览器打开
        print("\n浏览器将保持打开状态，按 Ctrl+C 退出...")
        try:
            await asyncio.sleep(300)  # 保持5分钟
        except KeyboardInterrupt:
            print("\n退出测试")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
