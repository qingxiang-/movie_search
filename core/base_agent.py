"""
Base Browser Agent - 通用浏览器 Agent 基类
"""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from urllib.parse import quote

from playwright.async_api import Page
from .llm_client import LLMClient
from .browser_utils import BrowserUtils


class BaseBrowserAgent(ABC):
    """
    基础浏览器 Agent 类
    
    提供通用的浏览器操作和 LLM 交互能力
    子类需要实现特定领域的逻辑
    """
    
    def __init__(self, 
                 max_iterations: int = 15,
                 max_retries: int = 3):
        """
        初始化 Agent
        
        Args:
            max_iterations: 最大迭代次数
            max_retries: 最大重试次数
        """
        self.llm_client = LLMClient()
        self.browser_utils = BrowserUtils()
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.search_history = []
        self.current_engine_index = 0
    
    async def close(self):
        """关闭资源"""
        await self.llm_client.close()
    
    @property
    @abstractmethod
    def SEARCH_ENGINES(self) -> List[Dict[str, str]]:
        """搜索引擎配置（子类必须实现）"""
        pass
    
    @abstractmethod
    async def plan_next_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 LLM 规划下一步操作（子类必须实现）
        
        Args:
            context: 当前上下文信息
            
        Returns:
            {"success": bool, "decision": dict} 或 {"success": bool, "error": str}
        """
        pass
    
    @abstractmethod
    async def execute_action(self, 
                           page: Page, 
                           action: Dict[str, Any], 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 LLM 规划的操作（子类必须实现）
        
        Args:
            page: Playwright Page 对象
            action: 操作信息
            context: 上下文信息
            
        Returns:
            {"success": bool, "action_taken": str} 或 {"success": bool, "error": str}
        """
        pass
    
    async def _goto_with_retry(self, page: Page, url: str, timeout: int = 15000) -> bool:
        """带重试机制的页面导航"""
        return await self.browser_utils.goto_with_retry(
            page, url, timeout, self.max_retries
        )
    
    def extract_page_content(self, 
                           html: str, 
                           max_length: int = 8000,
                           keywords: List[str] = None) -> str:
        """提取页面核心内容"""
        return self.browser_utils.extract_page_content(html, max_length, keywords)
    
    def extract_links(self, 
                     html: str, 
                     base_url: str, 
                     max_links: int = 15) -> List[Dict[str, str]]:
        """提取页面中的关键链接"""
        return self.browser_utils.extract_links(html, base_url, max_links)
    
    async def _execute_common_action(self,
                                    page: Page,
                                    action_type: str,
                                    params: Dict[str, Any],
                                    context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        执行通用操作（所有 Agent 共享）
        
        Returns:
            如果是通用操作，返回执行结果；否则返回 None
        """
        try:
            # 点击链接
            if action_type == "click_link":
                link_index = params.get("link_index", 1) - 1
                links = context.get("links", [])
                
                if 0 <= link_index < len(links):
                    target_url = links[link_index]["url"]
                    link_text = links[link_index]['text'][:50]
                    print(f"🔗 点击链接: {link_text}")
                    print(f"   URL: {target_url}")
                    success = await self._goto_with_retry(page, target_url)
                    if success:
                        return {"success": True, "action_taken": "click_link"}
                    else:
                        return {"success": False, "error": "页面导航失败"}
                else:
                    return {"success": False, "error": f"无效的链接索引: {link_index + 1}"}
            
            # 搜索
            elif action_type == "search":
                query = params.get("query", "")
                engine_index = params.get("engine_index", 0)
                
                if 0 <= engine_index < len(self.SEARCH_ENGINES):
                    engine = self.SEARCH_ENGINES[engine_index]
                    search_url = f"{engine['url']}{quote(query)}"
                    print(f"🔍 在 {engine['name']} 搜索: {query}")
                    success = await self._goto_with_retry(page, search_url, timeout=30000)
                    if success:
                        return {"success": True, "action_taken": "search"}
                    else:
                        return {"success": False, "error": "搜索页面加载失败"}
                else:
                    return {"success": False, "error": f"无效的搜索引擎索引: {engine_index}"}
            
            # 滚动
            elif action_type == "scroll":
                print("⬇️  向下滚动页面")
                await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
                await asyncio.sleep(1)
                return {"success": True, "action_taken": "scroll"}
            
            # 返回
            elif action_type == "back":
                print("⬅️  返回上一页")
                await page.go_back()
                await asyncio.sleep(1)
                return {"success": True, "action_taken": "back"}
            
            # 翻页
            elif action_type == "next_page":
                print("➡️  尝试翻到下一页")
                next_selectors = [
                    'a:has-text("下一页")',
                    'a:has-text("Next")',
                    'a.nxt',
                    'a.next',
                    '#page a:last-child'
                ]
                for selector in next_selectors:
                    try:
                        next_btn = page.locator(selector).first
                        if await next_btn.count() > 0:
                            await next_btn.click()
                            await asyncio.sleep(2)
                            return {"success": True, "action_taken": "next_page"}
                    except:
                        continue
                return {"success": False, "error": "未找到下一页按钮"}
            
            # 切换搜索引擎
            elif action_type == "switch_engine":
                engine_index = params.get("engine_index", 0)
                if 0 <= engine_index < len(self.SEARCH_ENGINES):
                    if engine_index == self.current_engine_index:
                        return {"success": False, "error": "已经在使用该搜索引擎"}
                    
                    self.current_engine_index = engine_index
                    engine = self.SEARCH_ENGINES[engine_index]
                    print(f"🔄 切换到 {engine['name']}")
                    return {"success": True, "action_taken": "switch_engine", "switch_only": True}
                else:
                    return {"success": False, "error": f"无效的搜索引擎索引: {engine_index}"}
            
            # 停止
            elif action_type == "stop":
                print("⏹️  决定停止搜索")
                return {"success": True, "action_taken": "stop", "done": True}
            
            # 不是通用操作
            else:
                return None
                
        except Exception as e:
            return {"success": False, "error": str(e)}
