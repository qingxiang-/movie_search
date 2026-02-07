#!/usr/bin/env python3
"""
简化的滑块验证码测试 - 直接使用坐标拖拽
"""

import asyncio
from playwright.async_api import async_playwright


async def main():
    print("🧪 简化滑块验证码测试")
    print("="*60)
    
    url = "https://search.damai.cn/search.html?keyword=%E6%BC%94%E5%94%B1%E4%BC%9A"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print(f"\n📡 访问: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        print("\n⏳ 等待验证码出现...")
        await asyncio.sleep(5)
        
        # 保存初始截图
        await page.screenshot(path="captcha_before.png")
        print("📸 保存初始截图: captcha_before.png")
        
        # 检查所有 iframe
        print(f"\n🔍 检查 iframe...")
        all_frames = page.frames
        print(f"共有 {len(all_frames)} 个 frame")
        
        for i, frame in enumerate(all_frames):
            print(f"\nFrame {i}:")
            print(f"  URL: {frame.url[:100] if frame.url else 'about:blank'}")
            
            # 在每个 frame 中查找滑块
            try:
                # 尝试多种选择器
                selectors = [
                    ".nc_iconfont",
                    ".btn_slide",
                    "span.btn_slide",
                    "[class*='nc_']",
                    "[class*='slide']"
                ]
                
                for sel in selectors:
                    try:
                        elements = await frame.locator(sel).all()
                        if elements:
                            print(f"  找到 {len(elements)} 个元素匹配 '{sel}'")
                            for idx, elem in enumerate(elements[:3]):  # 只检查前3个
                                box = await elem.bounding_box()
                                if box:
                                    print(f"    元素 {idx}: 位置({box['x']}, {box['y']}), 大小({box['width']}x{box['height']})")
                    except Exception as e:
                        pass
            except Exception as e:
                print(f"  检查失败: {e}")
        
        print("\n" + "="*60)
        print("方法1: 使用固定坐标拖拽 (基于你的截图)")
        print("="*60)
        
        # 根据你的截图，滑块大约在左下角
        # 验证码弹窗通常在屏幕中央，滑块在弹窗底部左侧
        start_x = 155  # 滑块中心 x 坐标
        start_y = 525  # 滑块中心 y 坐标
        distance = 500  # 拖拽距离
        
        print(f"起点: ({start_x}, {start_y})")
        print(f"拖拽距离: {distance}px")
        
        try:
            # 移动到滑块位置
            await page.mouse.move(start_x, start_y)
            await asyncio.sleep(0.5)
            print("✓ 移动到滑块")
            
            # 按下鼠标
            await page.mouse.down()
            await asyncio.sleep(0.3)
            print("✓ 按下鼠标")
            
            # 慢速拖拽
            steps = 50
            for i in range(steps + 1):
                progress = i / steps
                current_x = start_x + (distance * progress)
                await page.mouse.move(current_x, start_y)
                await asyncio.sleep(0.01)
            
            print(f"✓ 拖拽到 x={start_x + distance}")
            
            # 释放鼠标
            await page.mouse.up()
            print("✓ 释放鼠标")
            
            # 等待验证结果
            await asyncio.sleep(3)
            
            # 保存结果截图
            await page.screenshot(path="captcha_after_method1.png")
            print("📸 保存结果截图: captcha_after_method1.png")
            
        except Exception as e:
            print(f"❌ 方法1失败: {e}")
        
        print("\n" + "="*60)
        print("方法2: 使用 JavaScript 直接操作滑块")
        print("="*60)
        
        # 刷新页面
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(5)
        
        # 使用 JavaScript 查找并拖拽滑块
        js_drag = """
        async () => {
            // 查找所有可能的滑块元素
            const findSlider = () => {
                // 在主文档中查找
                let slider = document.querySelector('.nc_iconfont.btn_slide') ||
                            document.querySelector('.btn_slide') ||
                            document.querySelector('span.btn_slide');
                
                if (slider) return {slider, frame: 'main'};
                
                // 在 iframe 中查找
                const iframes = document.querySelectorAll('iframe');
                for (let iframe of iframes) {
                    try {
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        slider = iframeDoc.querySelector('.nc_iconfont.btn_slide') ||
                                iframeDoc.querySelector('.btn_slide') ||
                                iframeDoc.querySelector('span.btn_slide');
                        if (slider) return {slider, frame: 'iframe'};
                    } catch (e) {
                        // 跨域 iframe，跳过
                    }
                }
                
                return null;
            };
            
            const result = findSlider();
            if (!result) {
                return {success: false, error: 'Slider not found'};
            }
            
            const {slider, frame} = result;
            const rect = slider.getBoundingClientRect();
            
            // 创建并触发拖拽事件
            const startX = rect.left + rect.width / 2;
            const startY = rect.top + rect.height / 2;
            const distance = 500;
            
            // mousedown
            slider.dispatchEvent(new MouseEvent('mousedown', {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: startX,
                clientY: startY,
                button: 0
            }));
            
            // 逐步移动
            for (let i = 0; i <= distance; i += 10) {
                await new Promise(r => setTimeout(r, 20));
                const event = new MouseEvent('mousemove', {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    clientX: startX + i,
                    clientY: startY,
                    button: 0
                });
                document.dispatchEvent(event);
            }
            
            // mouseup
            document.dispatchEvent(new MouseEvent('mouseup', {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: startX + distance,
                clientY: startY,
                button: 0
            }));
            
            return {
                success: true,
                frame,
                startX,
                startY,
                distance
            };
        }
        """
        
        try:
            result = await page.evaluate(js_drag)
            print(f"JavaScript 执行结果: {result}")
            
            await asyncio.sleep(3)
            await page.screenshot(path="captcha_after_method2.png")
            print("📸 保存结果截图: captcha_after_method2.png")
            
        except Exception as e:
            print(f"❌ 方法2失败: {e}")
        
        print("\n" + "="*60)
        print("测试完成！")
        print("请查看截图:")
        print("  - captcha_before.png (初始状态)")
        print("  - captcha_after_method1.png (方法1结果)")
        print("  - captcha_after_method2.png (方法2结果)")
        print("="*60)
        
        # 保持浏览器打开
        print("\n浏览器将保持打开，按 Ctrl+C 退出...")
        try:
            await asyncio.sleep(300)
        except KeyboardInterrupt:
            print("\n退出")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
