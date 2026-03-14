#!/usr/bin/env python3
"""
大麦网演出搜索工具 - Azure GPT Vision Agent 智能导航版
使用 Playwright (headed 模式) + GPT Vision 智能识别页面元素和处理验证码
"""

import os
import re
import json
import base64
import asyncio
import random
from datetime import datetime
from typing import List, Optional, Dict, Any
from io import BytesIO

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI 配置
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")

# 搜索类别配置
SEARCH_CATEGORIES = {
    "演唱会": {
        "keywords": ["演唱会", "音乐会", "concert"],
        "search_term": "演唱会"
    },
    "话剧": {
        "keywords": ["话剧", "戏剧", "drama"],
        "search_term": "话剧"
    },
    "歌剧": {
        "keywords": ["歌剧", "opera"],
        "search_term": "歌剧"
    },
    "livehouse": {
        "keywords": ["livehouse", "live", "现场"],
        "search_term": "livehouse"
    }
}


class DamaiSearcher:
    """大麦网智能搜索器 - 基于 GPT Vision Agent"""

    def __init__(self, headless: bool = False, max_retries: int = 3):
        self.headless = headless
        self.max_retries = max_retries
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.results = {}

        # Azure OpenAI 客户端 (延迟初始化)
        self._azure_client = None

        if not AZURE_OPENAI_API_KEY:
            raise ValueError("Azure OpenAI API Key 未配置，请在 .env 文件中设置 AZURE_OPENAI_API_KEY")

    def _get_azure_client(self):
        """获取 Azure OpenAI 客户端 (延迟初始化)"""
        if self._azure_client is None:
            from openai import AzureOpenAI
            self._azure_client = AzureOpenAI(
                api_key=AZURE_OPENAI_API_KEY,
                api_version=AZURE_OPENAI_API_VERSION,
                azure_endpoint=AZURE_OPENAI_ENDPOINT.rstrip('/') if AZURE_OPENAI_ENDPOINT else ""
            )
        return self._azure_client

    async def call_gpt_vision(
        self, 
        screenshot_base64: str, 
        task_description: str,
        page_elements: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        调用 Azure GPT Vision API 分析页面并做出决策
        
        Args:
            screenshot_base64: Base64 编码的截图
            task_description: 当前任务描述
            page_elements: 页面元素信息（可选）
        
        Returns:
            GPT 的决策结果
        """
        system_prompt = """你是一个网页自动化专家，擅长分析网页截图并给出精确的操作指令。

你的任务是：
1. 分析页面截图，识别关键元素（按钮、输入框、链接等）
2. 根据当前任务，决定下一步操作
3. 返回 JSON 格式的操作指令

操作类型包括：
- click: 点击元素（包括"查看全部"、"更多"等按钮）
- input: 输入文字
- drag: 拖拽（用于滑块验证码，系统会自动增量拖拽并验证）
- wait: 等待页面加载（单位：秒，通常1-3秒即可）
- scroll: 滚动页面
- captcha_click: 点选验证码
- captcha_verified: 验证码已验证成功
- captcha_continue: 验证码需要继续拖拽
- extract: 提取信息

返回格式：
{
  "action": "操作类型",
  "target": {
    "selector": "标准CSS选择器（如 .class-name, #id, button, a 等，不要使用 :contains 或 :has-text）",
    "text": "元素的精确文本内容（优先使用此方式定位）",
    "description": "元素描述",
    "coordinates": {"x": 100, "y": 200}
  },
  "value": "输入值、拖拽距离(px)、或等待时长(秒)",
  "reasoning": "决策理由",
  "confidence": 0.9
}

特别注意：
1. 如果遇到验证码，action 应为 captcha_click 或 drag
2. 对于滑块验证码，返回拖拽起点和距离(像素)
3. 对于点选验证码，返回所有需要点击的坐标
4. 如果页面还在加载，返回 wait 操作，value 为等待秒数(1-3秒)
5. 如果看到"查看全部"、"更多"等按钮，优先点击以获取完整列表
6. wait 操作的 value 必须是秒数，例如 2 表示等待2秒，不要使用毫秒
7. 对于点击操作，优先填写 text 字段（元素的精确文本），这是最可靠的定位方式
8. selector 字段只能使用标准CSS选择器，不要使用 :contains() 或 :has-text() 等伪选择器
"""

        user_content = [
            {
                "type": "text",
                "text": f"当前任务: {task_description}\n\n"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{screenshot_base64}"
                }
            }
        ]

        if page_elements:
            elements_text = "\n可交互元素列表：\n"
            for i, elem in enumerate(page_elements[:20]):  # 限制元素数量
                elements_text += f"{i+1}. {elem.get('tag', 'unknown')} - '{elem.get('text', '')}' at ({elem.get('position', {}).get('x', 0)}, {elem.get('position', {}).get('y', 0)})\n"
            user_content[0]["text"] += elements_text

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            # 使用新版 Azure OpenAI SDK
            client = self._get_azure_client()
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=AZURE_OPENAI_DEPLOYMENT,
                    messages=messages,
                    temperature=0.3,
                    max_completion_tokens=1000
                )
            )

            content = response.choices[0].message.content
            
            # 打印完整的 GPT 响应用于调试
            print(f"\n{'='*60}")
            print(f"🤖 GPT 完整响应:")
            print(f"{'-'*60}")
            print(content)
            print(f"{'='*60}\n")
            
            # 尝试解析 JSON
            try:
                # 提取 JSON 代码块
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                else:
                    json_content = content
                
                decision = json.loads(json_content)
                print(f"✅ JSON 解析成功")
                print(f"   Action: {decision.get('action')}")
                print(f"   Target: {decision.get('target', {})}")
                print(f"   Value: {decision.get('value')}")
                print(f"   Confidence: {decision.get('confidence')}\n")
                
                return {"success": True, "decision": decision, "raw_content": content}
            except json.JSONDecodeError as e:
                print(f"❌ JSON 解析失败: {e}")
                print(f"   尝试解析的内容: {json_content[:200]}...\n")
                return {
                    "success": False,
                    "error": f"Failed to parse GPT response as JSON: {e}",
                    "raw_content": content
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_page_elements(self, page: Page) -> List[Dict]:
        """提取页面关键元素信息"""
        try:
            elements = await page.evaluate("""
                () => {
                    const elements = [];
                    const selectors = 'button, input, a, [role="button"], [role="link"], .search-box, .item, .event';
                    
                    document.querySelectorAll(selectors).forEach((el, index) => {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            elements.push({
                                index: index,
                                tag: el.tagName.toLowerCase(),
                                text: (el.innerText || el.value || el.placeholder || '').trim().substring(0, 50),
                                className: el.className,
                                id: el.id,
                                position: {
                                    x: Math.round(rect.x + rect.width / 2),
                                    y: Math.round(rect.y + rect.height / 2),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height)
                                },
                                visible: rect.width > 0 && rect.height > 0
                            });
                        }
                    });
                    
                    return elements.slice(0, 50);
                }
            """)
            return elements
        except Exception as e:
            print(f"⚠️  提取页面元素失败: {e}")
            return []

    async def take_screenshot(self, page: Page) -> str:
        """截图并转换为 Base64"""
        screenshot_bytes = await page.screenshot(full_page=False)
        return base64.b64encode(screenshot_bytes).decode('utf-8')

    async def incremental_drag_with_verification(
        self,
        page: Page,
        start_x: int,
        start_y: int,
        max_distance: int = 300,
        increment: int = 50
    ) -> bool:
        """使用人类化拖拽方式（借鉴 Shopee CAPTCHA Solver）"""
        print(f"\n🔐 开始拖拽验证码滑块 (人类化方式)")
        print(f"   起点: ({start_x}, {start_y})")
        print(f"   拖拽距离: {max_distance}px")
        
        # 创建 debug 目录
        import os
        from datetime import datetime
        debug_dir = "debug_captcha"
        os.makedirs(debug_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存初始截图
        screenshot_bytes = await page.screenshot(full_page=False)
        with open(f"{debug_dir}/drag_{timestamp}_00_initial.png", "wb") as f:
            f.write(screenshot_bytes)
        print(f"   📸 保存初始截图: {debug_dir}/drag_{timestamp}_00_initial.png")
        
        try:
            import random
            import math
            
            # 移动到起点
            print(f"   👆 移动到起点")
            await page.mouse.move(start_x, start_y)
            await asyncio.sleep(random.uniform(0.1, 0.2))
            
            # 按下鼠标
            print(f"   🔽 按下鼠标")
            await page.mouse.down()
            await asyncio.sleep(random.uniform(0.1, 0.15))
            
            # 第一阶段：初始快速拖动（模拟人类按下后的反应）
            initial_distance = random.randint(8, 15)
            print(f"   📍 初始拖动 {initial_distance}px")
            for pixel in range(initial_distance):
                # 使用对数曲线产生 Y 轴微小变化
                y_offset = math.log(1 + pixel) * 0.5
                await page.mouse.move(start_x + pixel, start_y + y_offset)
                await asyncio.sleep(0.03)
            
            # 第二阶段：主要拖拽（使用变速和曲线）
            print(f"   🚀 主要拖拽阶段")
            remaining_distance = max_distance - initial_distance
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
            
            # 第三阶段：overshoot（超出）然后回退
            print(f"   🎯 Overshoot 和回退")
            overshoot = random.randint(3, 8)
            final_x = start_x + max_distance
            
            # 超出目标
            await page.mouse.move(final_x + overshoot, start_y + random.uniform(-1, 1), steps=15)
            await asyncio.sleep(0.05)
            
            # 回退到准确位置
            await page.mouse.move(final_x, start_y, steps=10)
            await asyncio.sleep(random.uniform(0.15, 0.25))
            
            print(f"   ✓ 拖拽完成 (x={final_x})")
            
            # 保存拖拽后截图
            screenshot_bytes = await page.screenshot(full_page=False)
            with open(f"{debug_dir}/drag_{timestamp}_dragged.png", "wb") as f:
                f.write(screenshot_bytes)
            print(f"   📸 保存拖拽后截图")
            
            # 释放鼠标
            print(f"   🔼 释放鼠标")
            await page.mouse.up()
            await asyncio.sleep(2)
            
            # 保存释放后截图
            screenshot_bytes = await page.screenshot(full_page=False)
            with open(f"{debug_dir}/drag_{timestamp}_released.png", "wb") as f:
                f.write(screenshot_bytes)
            print(f"   📸 保存释放后截图")
            
            # 验证结果
            screenshot = await self.take_screenshot(page)
            task = "检查验证码是否验证成功。如果看到验证成功的提示或验证码弹窗消失，返回 action='captcha_verified'。如果还在显示验证码，返回 action='captcha_continue'。"
            result = await self.call_gpt_vision(screenshot, task, [])
            
            if result.get("success"):
                decision = result.get("decision", {})
                if decision.get("action") == "captcha_verified":
                    print(f"   ✅ 验证码验证成功")
                    return True
                else:
                    print(f"   ⚠️  验证码未通过，可能需要重试")
            
            return False
            
        except Exception as e:
            print(f"   ❌ 人类化拖拽失败: {e}")
            print(f"   ⚠️  这个验证码可能需要人工干预")
            print(f"   📝 建议: 1) 登录后再搜索  2) 使用验证码解决服务  3) 手动完成验证")
            return False

    async def _old_coordinate_based_drag(
        self,
        page: Page,
        start_x: int,
        start_y: int,
        max_distance: int,
        debug_dir: str,
        timestamp: str
    ) -> bool:
        """坐标拖拽回退方案 - 使用JavaScript直接操作"""
        print(f"   🔧 使用JavaScript坐标拖拽")
        
        # 使用JavaScript模拟拖拽事件
        drag_script = f"""
        (async () => {{
            const startX = {start_x};
            const startY = {start_y};
            const distance = {max_distance};
            
            // 找到滑块元素
            const slider = document.querySelector('.nc_iconfont.btn_slide') || 
                          document.querySelector('.btn_slide') ||
                          document.querySelector('[class*="slide"]');
            
            if (!slider) {{
                return {{success: false, error: 'Slider not found'}};
            }}
            
            // 触发拖拽事件
            const mousedown = new MouseEvent('mousedown', {{
                bubbles: true,
                cancelable: true,
                clientX: startX,
                clientY: startY
            }});
            slider.dispatchEvent(mousedown);
            
            // 逐步移动
            for (let i = 0; i <= distance; i += 10) {{
                const mousemove = new MouseEvent('mousemove', {{
                    bubbles: true,
                    cancelable: true,
                    clientX: startX + i,
                    clientY: startY
                }});
                document.dispatchEvent(mousemove);
                await new Promise(r => setTimeout(r, 20));
            }}
            
            // 释放
            const mouseup = new MouseEvent('mouseup', {{
                bubbles: true,
                cancelable: true,
                clientX: startX + distance,
                clientY: startY
            }});
            document.dispatchEvent(mouseup);
            
            return {{success: true}};
        }})()
        """
        
        try:
            result = await page.evaluate(drag_script)
            print(f"   JavaScript拖拽结果: {result}")
            
            # 保存截图
            screenshot_bytes = await page.screenshot(full_page=False)
            with open(f"{debug_dir}/drag_{timestamp}_js_result.png", "wb") as f:
                f.write(screenshot_bytes)
            
            await asyncio.sleep(2)
            
            # 验证结果
            screenshot = await self.take_screenshot(page)
            task = "检查验证码是否验证成功。如果看到验证成功的提示或验证码消失，返回 action='captcha_verified'。"
            result = await self.call_gpt_vision(screenshot, task, [])
            
            if result.get("success"):
                decision = result.get("decision", {})
                if decision.get("action") == "captcha_verified":
                    return True
                    
        except Exception as e:
            print(f"   ❌ JavaScript拖拽失败: {e}")
        
        return False

    async def handle_captcha(self, page: Page, decision: Dict) -> bool:
        """处理验证码"""
        action = decision.get("action", "")
        target = decision.get("target", {})
        
        print(f"🔐 处理验证码: {action}")
        print(f"   决策理由: {decision.get('reasoning', 'N/A')}")
        
        try:
            if action == "drag":
                # 滑块验证码 - 使用增量拖拽
                coords = target.get("coordinates", {})
                start_x = coords.get("x", 0)
                start_y = coords.get("y", 0)
                max_distance = int(decision.get("value", 300))
                
                print(f"   拖拽滑块: 起点({start_x}, {start_y}), 最大距离={max_distance}px")
                success = await self.incremental_drag_with_verification(
                    page, start_x, start_y, max_distance, increment=50
                )
                return success
                
            elif action == "captcha_click":
                # 点选验证码
                click_points = decision.get("value", [])
                if isinstance(click_points, list):
                    for point in click_points:
                        x, y = point.get("x", 0), point.get("y", 0)
                        print(f"   点击验证码位置: ({x}, {y})")
                        await page.mouse.click(x, y)
                        await asyncio.sleep(random.uniform(0.3, 0.6))
                    return True
                    
            elif action == "input":
                # 文字验证码
                selector = target.get("selector", "")
                value = decision.get("value", "")
                if selector and value:
                    print(f"   输入验证码: {value}")
                    await page.fill(selector, value)
                    await asyncio.sleep(1)
                    return True
                    
        except Exception as e:
            print(f"❌ 验证码处理失败: {e}")
            return False
        
        return False

    async def execute_action(self, page: Page, decision: Dict) -> bool:
        """执行 GPT 决策的操作"""
        action = decision.get("action", "")
        target = decision.get("target", {})
        
        try:
            if action == "click":
                # 尝试多种定位方式
                selector = target.get("selector", "")
                text = target.get("text", "")
                coords = target.get("coordinates", {})
                
                clicked = False
                
                # 优先尝试文本定位（最可靠）
                if text and not clicked:
                    try:
                        print(f"   点击文本: {text}")
                        await page.click(f"text={text}", timeout=5000)
                        clicked = True
                    except Exception as e:
                        print(f"   ⚠️  文本定位失败: {str(e)[:100]}")
                
                # 尝试 CSS 选择器（如果有效）
                if selector and not clicked:
                    try:
                        # 检查是否是无效的选择器（如 :contains）
                        if ":contains" in selector or ":has-text" in selector:
                            print(f"   ⚠️  跳过无效选择器: {selector}")
                        else:
                            print(f"   点击元素: {selector}")
                            await page.click(selector, timeout=5000)
                            clicked = True
                    except Exception as e:
                        print(f"   ⚠️  选择器定位失败: {str(e)[:100]}")
                
                # 最后尝试坐标点击
                if coords.get("x") and coords.get("y") and not clicked:
                    try:
                        x, y = coords["x"], coords["y"]
                        print(f"   点击坐标: ({x}, {y})")
                        await page.mouse.click(x, y)
                        clicked = True
                    except Exception as e:
                        print(f"   ⚠️  坐标点击失败: {str(e)[:100]}")
                
                if not clicked:
                    print("   ❌ 所有定位方式都失败")
                    return False
                    
                await asyncio.sleep(random.uniform(1, 2))
                return True
                
            elif action == "input":
                selector = target.get("selector", "")
                value = decision.get("value", "")
                
                if selector and value:
                    print(f"   输入文字: {value} -> {selector}")
                    await page.fill(selector, value)
                    await asyncio.sleep(random.uniform(0.3, 0.5))
                    
                    # 如果是搜索框，按 Enter 提交搜索
                    if "搜索" in str(target.get("text", "")) or "search" in selector.lower():
                        print(f"   按 Enter 提交搜索")
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(2)  # 等待页面跳转
                    
                    return True
                    
            elif action == "scroll":
                distance = int(decision.get("value", 500))
                print(f"   滚动页面: {distance}px")
                await page.evaluate(f"window.scrollBy(0, {distance})")
                await asyncio.sleep(1)
                return True
                
            elif action == "wait":
                duration = float(decision.get("value", 2))
                # 确保等待时间合理（1-10秒之间）
                if duration > 10:
                    print(f"   ⚠️  等待时间过长({duration}秒)，调整为3秒")
                    duration = 3
                elif duration < 0.5:
                    duration = 1
                print(f"   等待: {duration}秒")
                await asyncio.sleep(duration)
                return True
                
            elif action in ["drag", "captcha_click"]:
                return await self.handle_captcha(page, decision)
                
        except Exception as e:
            print(f"❌ 执行操作失败: {e}")
            return False
        
        return False

    async def search_category(self, category: str) -> List[Dict]:
        """搜索特定类别的演出"""
        print(f"\n🔍 搜索类别: {category}")
        
        if not self.page:
            print("❌ 页面未初始化")
            return []
        
        page = self.page
        config = SEARCH_CATEGORIES.get(category, {})
        search_term = config.get("search_term", category)
        
        events = []
        max_iterations = 10
        last_url = ""
        same_url_count = 0
        
        for iteration in range(max_iterations):
            print(f"\n--- 迭代 {iteration + 1}/{max_iterations} ---")
            
            # 检测页面 URL 是否变化，避免无限循环
            current_url = page.url
            if current_url == last_url:
                same_url_count += 1
                if same_url_count >= 3:
                    print(f"\n⚠️  页面 URL 未变化已达 {same_url_count} 次，可能陷入循环")
                    print(f"   当前 URL: {current_url}")
                    print(f"   当前页面可能没有正确跳转到搜索结果页")
                    print(f"   尝试提取当前页面的演出信息...")
                    extracted_events = await self.extract_events_from_page(page)
                    events.extend(extracted_events)
                    if len(events) > 0:
                        print(f"   ✓ 成功提取 {len(extracted_events)} 条信息，退出循环")
                        break
                    else:
                        print(f"   ⚠️  未能提取到信息，可能需要重新搜索")
                        # 尝试重新导航到首页
                        await page.goto("https://www.damai.cn", wait_until="domcontentloaded", timeout=10000)
                        await asyncio.sleep(2)
                        same_url_count = 0
                        last_url = page.url
            else:
                same_url_count = 0
            last_url = current_url
            
            # 截图并获取页面元素
            screenshot = await self.take_screenshot(page)
            elements = await self.get_page_elements(page)
            
            # 根据当前状态构建任务描述
            if iteration == 0:
                task = f"在大麦网首页搜索 '{search_term}'。请找到搜索框并输入关键词（系统会自动按Enter提交）。"
            elif iteration == 1:
                task = f"检查是否有验证码需要处理。如果有滑块验证码，返回 action='drag'。如果有点选验证码，返回 action='captcha_click'。如果没有验证码，等待2秒让页面加载完成。"
            elif iteration < 4:
                task = f"检查当前页面状态。如果已经在搜索结果页面（URL包含search或有大量演出列表），返回 action='extract' 开始提取信息。如果还在首页，等待1-2秒。"
            else:
                task = f"提取页面上的演出信息，包括标题、日期、地点、价格等。如果需要滚动查看更多内容，返回 action='scroll'。如果已提取足够信息，返回 action='extract'。"
            
            # 调用 GPT Vision 分析
            print(f"🤖 GPT 分析中...")
            result = await self.call_gpt_vision(screenshot, task, elements)
            
            if not result.get("success"):
                print(f"❌ GPT 分析失败: {result.get('error')}")
                await asyncio.sleep(2)
                continue
            
            decision = result.get("decision", {})
            action = decision.get("action", "")
            confidence = decision.get("confidence", 0)
            reasoning = decision.get("reasoning", "")
            
            print(f"📋 决策: {action} (置信度: {confidence})")
            print(f"💭 理由: {reasoning}")
            
            # 执行操作
            if action == "extract":
                # 提取信息
                print("📊 提取演出信息...")
                extracted_events = await self.extract_events_from_page(page)
                events.extend(extracted_events)
                print(f"   已提取 {len(extracted_events)} 条信息")
                
                if len(events) >= 20:  # 提取足够信息后停止
                    break
                    
                # 继续滚动查看更多
                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(2)
                
            else:
                # 执行其他操作
                success = await self.execute_action(page, decision)
                if not success:
                    print("⚠️  操作执行失败，重试...")
                    await asyncio.sleep(2)
        
        print(f"\n✅ {category} 搜索完成，共提取 {len(events)} 条信息")
        return events

    async def extract_events_from_page(self, page: Page) -> List[Dict]:
        """从当前页面提取演出信息"""
        try:
            events = await page.evaluate("""
                () => {
                    const events = [];
                    const items = document.querySelectorAll('.item, .event-item, [class*="item"]');
                    
                    items.forEach(item => {
                        try {
                            const title = item.querySelector('[class*="title"], h3, h4, .name')?.innerText?.trim() || '';
                            const date = item.querySelector('[class*="date"], [class*="time"]')?.innerText?.trim() || '';
                            const venue = item.querySelector('[class*="venue"], [class*="place"], [class*="location"]')?.innerText?.trim() || '';
                            const price = item.querySelector('[class*="price"], [class*="money"]')?.innerText?.trim() || '';
                            const link = item.querySelector('a')?.href || '';
                            const image = item.querySelector('img')?.src || '';
                            
                            if (title) {
                                events.push({
                                    title: title,
                                    date: date,
                                    venue: venue,
                                    price_range: price,
                                    url: link,
                                    image: image,
                                    status: '在售'
                                });
                            }
                        } catch (e) {
                            console.error('提取单个演出信息失败:', e);
                        }
                    });
                    
                    return events;
                }
            """)
            
            return events
            
        except Exception as e:
            print(f"❌ 提取演出信息失败: {e}")
            return []

    async def run(self, categories: Optional[List[str]] = None):
        """主执行流程"""
        print("🎭 大麦网演出搜索工具启动")
        print("=" * 60)
        
        if categories is None:
            categories = list(SEARCH_CATEGORIES.keys())
        
        async with async_playwright() as playwright:
            # 启动浏览器 (headed 模式)
            print(f"🌐 启动浏览器 (headless={self.headless})...")
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            # 创建上下文
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
                timezone_id='Asia/Shanghai'
            )
            
            self.page = await self.context.new_page()
            
            # 访问大麦网
            print("📡 访问 https://www.damai.cn ...")
            await self.page.goto("https://www.damai.cn", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            # 搜索各个类别
            for category in categories:
                try:
                    events = await self.search_category(category)
                    self.results[category] = {
                        "events": events,
                        "total_count": len(events),
                        "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                except Exception as e:
                    print(f"❌ 搜索 {category} 失败: {e}")
                    self.results[category] = {
                        "events": [],
                        "total_count": 0,
                        "error": str(e)
                    }
                
                await asyncio.sleep(random.uniform(2, 4))
            
            # 输出结果
            self.print_results()
            self.save_results()
            
            # 关闭浏览器
            await self.browser.close()
            print("\n✅ 搜索完成！")

    def print_results(self):
        """打印搜索结果"""
        print("\n" + "=" * 60)
        print("🎭 大麦网演出搜索结果")
        print("=" * 60)
        
        for category, data in self.results.items():
            events = data.get("events", [])
            print(f"\n📍 {category} (共 {len(events)} 场)")
            print("-" * 60)
            
            for i, event in enumerate(events[:10], 1):  # 只显示前10条
                print(f"{i}. {event.get('title', 'N/A')}")
                print(f"   📅 {event.get('date', 'N/A')} | 📍 {event.get('venue', 'N/A')}")
                print(f"   💰 {event.get('price_range', 'N/A')}")
                if event.get('url'):
                    print(f"   🔗 {event['url']}")
                print()

    def save_results(self):
        """保存结果到 JSON 文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"damai_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 结果已保存到: {filename}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='大麦网演出搜索工具')
    parser.add_argument('--categories', type=str, help='搜索类别，逗号分隔，如: 演唱会,话剧')
    parser.add_argument('--headless', action='store_true', help='使用 headless 模式')
    
    args = parser.parse_args()
    
    categories = None
    if args.categories:
        categories = [c.strip() for c in args.categories.split(',')]
    
    searcher = DamaiSearcher(headless=args.headless)
    await searcher.run(categories=categories)


if __name__ == "__main__":
    asyncio.run(main())
