#!/usr/bin/env python3
"""
大麦网验证码测试 - 整合 ddddocr 滑块识别
使用 Playwright + ddddocr 自动识别并破解滑块验证码

使用前先安装依赖:
    pip3 install ddddocr playwright
    playwright install chromium

使用方法:
    python3 test_damai_with_ddddocr.py
"""
import asyncio
import base64
import random
import os
from datetime import datetime
from playwright.async_api import async_playwright
import ddddocr


class DamaiCaptchaSolver:
    """大麦网滑块验证码破解器"""
    
    def __init__(self, debug: bool = True):
        self.debug = debug
        self.ocr = ddddocr.DdddOcr()
        self.debug_dir = "debug_ddddocr"
        if debug:
            os.makedirs(self.debug_dir, exist_ok=True)
    
    async def solve_captcha(self, page) -> bool:
        """
        破解滑块验证码
        
        Returns:
            bool: 是否成功破解
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. 查找验证码 iframe
        print("\n🎯 查找验证码...")
        captcha_frame = await self._find_captcha_frame(page)
        
        if not captcha_frame:
            print("   ⚠️  未找到验证码")
            return False
        
        # 2. 获取验证码图片
        print("   📸 获取验证码图片...")
        slide_bytes, bg_bytes = await self._get_captcha_images(captcha_frame, timestamp)
        
        if not slide_bytes or not bg_bytes:
            print("   ❌ 获取图片失败")
            return False
        
        # 3. 用 ddddocr 识别缺口位置
        print("   🧠 正在用 ddddocr 识别缺口位置...")
        try:
            result = self.ocr.slide_match(slide_bytes, bg_bytes)
            target_x = result.get('target_x', 0)
            print(f"   ✓ 识别到缺口 X 坐标: {target_x}")
        except Exception as e:
            print(f"   ❌ ddddocr 识别失败: {e}")
            return False
        
        # 4. 计算拖拽距离
        # 注意：需要减去滑块本身的宽度
        slide_width = 40  # 滑块宽度约40px
        drag_distance = target_x - slide_width // 2
        if drag_distance < 0:
            drag_distance = 0
        
        print(f"   📏 计算拖拽距离: {drag_distance}px")
        
        # 5. 执行拖拽
        print("   🖱️  执行拖拽...")
        success = await self._human_like_drag(
            page, captcha_frame, drag_distance, timestamp
        )
        
        # 6. 验证结果
        await asyncio.sleep(2)
        iframes_after = [f for f in page.frames if 'captcha' in f.url.lower() or 'nc' in f.url.lower()]
        
        if len(iframes_after) == 0:
            print("   ✅ 验证码已通过!")
            return True
        else:
            print("   ⚠️  验证码仍在，可能未通过")
            return success
    
    async def _find_captcha_frame(self, page) -> any:
        """查找验证码 iframe"""
        for i in range(30):  # 最多等30秒
            for frame in page.frames:
                url = frame.url.lower()
                if any(keyword in url for keyword in ['captcha', 'nc', 'alicdn', 'damai']):
                    if 'ali' in url or 'damai' in url:
                        print(f"   ✓ 找到验证码 frame: {url[:80]}")
                        return frame
            await asyncio.sleep(1)
        return None
    
    async def _get_captcha_images(self, frame, timestamp: str):
        """获取滑块图和背景图"""
        try:
            # 查找滑块图片
            slide_el = await frame.query_selector('img')
            bg_el = await frame.query_selector('img:nth-child(2)')
            
            if not slide_el or not bg_el:
                # 尝试其他选择器
                all_imgs = await frame.query_selector_all('img')
                if len(all_imgs) >= 2:
                    slide_el = all_imgs[0]
                    bg_el = all_imgs[1]
            
            if not slide_el or not bg_el:
                print("   ❌ 未找到验证码图片元素")
                return None, None
            
            # 获取图片
            slide_src = await slide_el.get_attribute('src')
            bg_src = await bg_el.get_attribute('src')
            
            # 如果是 base64
            if slide_src.startswith('data:image'):
                slide_bytes = base64.b64decode(slide_src.split(',')[1])
            elif slide_src.startswith('http'):
                async with async_playwright() as p:
                    browser = await p.chromium.launch()
                    ctx = await browser.new_context()
                    page = await ctx.new_page()
                    await page.goto(slide_src)
                    await asyncio.sleep(1)
                    slide_bytes = await page.screenshot()
                    await browser.close()
            else:
                slide_bytes = base64.b64decode(slide_src)
            
            if bg_src.startswith('data:image'):
                bg_bytes = base64.b64decode(bg_src.split(',')[1])
            elif bg_src.startswith('http'):
                async with async_playwright() as p:
                    browser = await p.chromium.launch()
                    ctx = await browser.new_context()
                    page = await ctx.new_page()
                    await page.goto(bg_src)
                    await asyncio.sleep(1)
                    bg_bytes = await page.screenshot()
                    await browser.close()
            else:
                bg_bytes = base64.b64decode(bg_src)
            
            # 保存调试图片
            if self.debug:
                with open(f"{self.debug_dir}/slide_{timestamp}.png", 'wb') as f:
                    f.write(slide_bytes)
                with open(f"{self.debug_dir}/bg_{timestamp}.png", 'wb') as f:
                    f.write(bg_bytes)
                print(f"   📁 图片已保存: slide_{timestamp}.png, bg_{timestamp}.png")
            
            return slide_bytes, bg_bytes
            
        except Exception as e:
            print(f"   ❌ 获取图片失败: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    async def _human_like_drag(self, page, frame, distance: int, timestamp: str) -> bool:
        """执行人类化拖拽"""
        try:
            # 找到滑块元素
            slider = await frame.query_selector('#nc_1_n1z') or await frame.query_selector('.btn_slide')
            
            if not slider:
                print("   ❌ 未找到滑块元素")
                return False
            
            box = await slider.bounding_box()
            start_x = int(box['x'] + box['width'] / 2)
            start_y = int(box['y'] + box['height'] / 2)
            
            print(f"   🎯 滑块位置: ({start_x}, {start_y})")
            
            # 保存截图
            if self.debug:
                await page.screenshot(path=f"{self.debug_dir}/before_drag_{timestamp}.png")
            
            # 执行拖拽
            await frame.mouse.move(start_x, start_y)
            await asyncio.sleep(random.uniform(0.2, 0.5))
            await frame.mouse.down()
            await asyncio.sleep(random.uniform(0.1, 0.2))
            
            # 分步拖拽，模拟人类行为
            steps = 20
            current_x = start_x
            
            for i in range(steps):
                progress = i / steps
                # 使用缓动函数
                eased = progress * progress * (3 - 2 * progress)
                target_x = start_x + distance * eased
                
                # 添加随机抖动
                jitter_y = random.uniform(-2, 2)
                
                await frame.mouse.move(int(target_x), start_y + jitter_y)
                await asyncio.sleep(random.uniform(0.02, 0.05))
                
                if i % 5 == 0:
                    print(f"   📍 拖拽进度: {int(progress * 100)}%")
            
            # 释放
            await asyncio.sleep(random.uniform(0.1, 0.2))
            await frame.mouse.up()
            
            # 保存截图
            if self.debug:
                await page.screenshot(path=f"{self.debug_dir}/after_drag_{timestamp}.png")
            
            print(f"   ✅ 拖拽完成")
            return True
            
        except Exception as e:
            print(f"   ❌ 拖拽失败: {e}")
            return False


async def test_damai():
    """测试大麦验证码"""
    solver = DamaiCaptchaSolver(debug=True)
    
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
        """)
        
        page = await context.new_page()
        
        try:
            # 访问大麦
            print("\n📄 访问大麦网搜索页...")
            await page.goto("https://search.damai.cn/search.html?keyword=演唱会", 
                          wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # 截图
            await page.screenshot(path=f"{solver.debug_dir}/01_homepage.png")
            print("📸 首页截图已保存")
            
            # 触发验证码
            print("\n🔄 等待验证码出现...")
            await asyncio.sleep(5)
            
            # 尝试破解
            success = await solver.solve_captcha(page)
            
            print("\n" + "="*60)
            if success:
                print("✅ 验证码破解成功!")
            else:
                print("❌ 验证码破解失败")
            print("="*60)
            
            # 保持浏览器打开
            print("\n⏸️  浏览器保持打开60秒...")
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


if __name__ == "__main__":
    print("="*60)
    print("🎯 大麦网验证码破解测试 (Playwright + ddddocr)")
    print("="*60)
    
    # 检查依赖
    try:
        import ddddocr
        print("✓ ddddocr 已安装")
    except ImportError:
        print("✗ ddddocr 未安装，请先运行: pip3 install ddddocr")
        exit(1)
    
    asyncio.run(test_damai())
