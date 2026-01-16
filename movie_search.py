#!/usr/bin/env python3
"""
电影 Magnet Link 搜索工具 - LLM 智能导航版
使用 LLM 指导浏览器操作，智能搜索并提取 magnet link
"""

import os
import re
import json
import asyncio
from typing import List, Optional, Dict, Any
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup

from playwright.async_api import async_playwright, Page
import httpx
from dotenv import load_dotenv
import openai

from prompts import get_planning_prompt, get_analysis_prompt

# 加载 .env 文件
load_dotenv()

# 从环境变量加载配置
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "qwen").lower()

# Qwen API 配置
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-flash-2025-07-28")

# Azure OpenAI 配置
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")


class MovieSearcher:
    """LLM 智能导航的电影 magnet link 搜索器"""

    # 通用搜索引擎（优化用于 magnet/torrent 搜索）
    SEARCH_ENGINES = [
        {"name": "DuckDuckGo", "url": "https://duckduckgo.com/?q=", "query_param": "q"},
        {"name": "Brave Search", "url": "https://search.brave.com/search?q=", "query_param": "q"},
        {"name": "Bing", "url": "https://www.bing.com/search?q=", "query_param": "q"},
    ]

    def __init__(self, max_iterations: int = 15, min_magnets: int = 5, max_retries: int = 3):
        self.http_client = httpx.AsyncClient(timeout=60.0)
        self.max_iterations = max_iterations
        self.min_magnets = min_magnets  # 参数化停止条件
        self.max_retries = max_retries  # 重试次数
        self.search_history = []
        self.found_magnets = []
        self.movie_name = ""  # 作为类变量，支持动态更新
        self.current_engine_index = 0  # 当前使用的搜索引擎索引
        self.llm_provider = LLM_PROVIDER
        
        # 配置 Azure OpenAI
        if self.llm_provider == "azure" and AZURE_OPENAI_API_KEY:
            openai.api_type = "azure"
            openai.api_key = AZURE_OPENAI_API_KEY
            openai.api_base = AZURE_OPENAI_ENDPOINT
            openai.api_version = AZURE_OPENAI_API_VERSION

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.http_client.aclose()

    async def call_llm_api(self, messages: list, temperature: float = 0.7, max_tokens: int = 2000) -> dict:
        """调用 LLM API (支持 Qwen 和 Azure OpenAI)"""
        try:
            if self.llm_provider == "azure":
                # 调用 Azure OpenAI (使用 openai v0.28.1 API)
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: openai.ChatCompletion.create(
                        engine=AZURE_OPENAI_DEPLOYMENT,
                        messages=messages,
                        temperature=temperature,
                        max_completion_tokens=max_tokens
                    )
                )
                content = response.choices[0].message["content"]
                return {"success": True, "content": content}
            else:
                # 调用 Qwen API
                url = f"{DASHSCOPE_BASE_URL}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json",
                }
                data = {
                    "model": DASHSCOPE_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                }

                response = await self.http_client.post(url, json=data, headers=headers)
                response.raise_for_status()
                result = response.json()
                return {"success": True, "content": result["choices"][0]["message"]["content"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_page_content(self, html: str, max_length: int = 8000) -> str:
        """提取页面核心内容，优先保留包含关键词的段落"""
        soup = BeautifulSoup(html, 'html.parser')

        # 移除脚本和样式
        for script in soup(["script", "style", "noscript"]):
            script.decompose()

        # 关键词列表
        keywords = ['magnet', '磁力', '下载', '种子', 'torrent', 'bt', '电影', self.movie_name.lower()]
        
        # 提取所有段落
        paragraphs = []
        for tag in soup.find_all(['p', 'div', 'article', 'section']):
            text = tag.get_text(strip=True)
            if text and len(text) > 20:  # 过滤太短的段落
                # 计算关键词权重
                weight = sum(1 for kw in keywords if kw and kw in text.lower())
                paragraphs.append((weight, text))
        
        # 按权重排序，优先保留相关内容
        paragraphs.sort(key=lambda x: x[0], reverse=True)
        
        # 组合文本
        combined_text = ' '.join(p[1] for p in paragraphs)
        
        # 如果没有段落，回退到全文本
        if not combined_text:
            combined_text = soup.get_text()
            lines = (line.strip() for line in combined_text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            combined_text = ' '.join(chunk for chunk in chunks if chunk)

        # 限制长度，但尽量不截断关键信息
        if len(combined_text) > max_length:
            combined_text = combined_text[:max_length] + "..."

        return combined_text

    def extract_magnet_links(self, page_text: str) -> List[str]:
        """从页面文本中提取所有 magnet links"""
        # 改进的正则：支持40位SHA-1和64位SHA-256，更精确匹配参数
        magnet_pattern = r'magnet:\?xt=urn:btih:[a-fA-F0-9]{40}(?:&[^\s<>"\'\']+)*'
        found = list(set(re.findall(magnet_pattern, page_text, re.IGNORECASE)))

        # 记录新发现的 magnet links
        new_magnets = [m for m in found if m not in self.found_magnets]
        if new_magnets:
            self.found_magnets.extend(new_magnets)

        return found

    def extract_links(self, html: str, base_url: str, max_links: int = 15) -> List[Dict[str, str]]:
        """提取页面中的关键链接"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []

        for a in soup.find_all('a', href=True):
            if len(links) >= max_links:
                break

            href = a['href']
            text = a.get_text(strip=True)

            # 过滤掉无用链接
            if not text or len(text) < 2:
                continue
            if href.startswith('javascript:') or href.startswith('#'):
                continue
            if href.startswith('//'):
                href = 'https:' + href
            elif not href.startswith('http'):
                href = urljoin(base_url, href)

            links.append({
                "text": text[:100],  # 限制文本长度
                "url": href
            })

        return links

    async def plan_next_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """使用 LLM 规划下一步操作"""

        # 添加累计发现的 magnet 数量和当前搜索引擎索引到上下文
        context["found_magnets_count"] = len(self.found_magnets)
        context["current_engine_index"] = self.current_engine_index

        # 从配置文件获取系统提示
        system_prompt = get_planning_prompt(context, self.SEARCH_ENGINES, self.max_iterations)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请规划下一步操作"}
        ]

        result = await self.call_llm_api(messages, temperature=0.7)

        if result["success"]:
            content = result["content"]
            try:
                # 提取 JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                decision = json.loads(content)
                return {"success": True, "decision": decision}
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"JSON 解析失败: {e}",
                    "raw_response": content
                }
        else:
            return {"success": False, "error": result["error"]}

    async def _goto_with_retry(self, page: Page, url: str, timeout: int = 15000) -> bool:
        """带重试机制的页面导航"""
        for attempt in range(self.max_retries):
            try:
                await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                return True
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"⚠️  导航失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)[:50]}")
                    await asyncio.sleep(1)
                else:
                    print(f"❌ 导航失败，已重试 {self.max_retries} 次: {str(e)[:50]}")
                    return False
        return False

    async def execute_action(self, page: Page, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 LLM 规划的操作"""

        action_type = action.get("action")
        params = action.get("params", {})

        print(f"\n📋 LLM 决策: {action.get('reason', action_type)}")

        try:
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

            elif action_type == "search":
                query = params.get("query", context.get("movie_name", ""))
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

            elif action_type == "scroll":
                print("⬇️  向下滚动页面")
                await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
                await asyncio.sleep(1)
                return {"success": True, "action_taken": "scroll"}

            elif action_type == "back":
                print("⬅️  返回上一页")
                await page.go_back()
                await asyncio.sleep(1)
                return {"success": True, "action_taken": "back"}

            elif action_type == "next_page":
                print("➡️  尝试翻到下一页")
                # 尝试常见的下一页链接
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

            elif action_type == "extract_magnets":
                print("✅ 提取 magnet links 并完成搜索")
                return {"success": True, "action_taken": "extract_magnets", "done": True}

            elif action_type == "switch_engine":
                engine_index = params.get("engine_index", 0)
                if 0 <= engine_index < len(self.SEARCH_ENGINES):
                    if engine_index == self.current_engine_index:
                        return {"success": False, "error": "已经在使用该搜索引擎"}
                    
                    self.current_engine_index = engine_index
                    engine = self.SEARCH_ENGINES[engine_index]
                    # 使用当前搜索词在新引擎搜索
                    search_query = f"{self.movie_name} magnet 下载"
                    search_url = f"{engine['url']}{quote(search_query)}"
                    print(f"🔄 切换到 {engine['name']} 搜索: {search_query}")
                    success = await self._goto_with_retry(page, search_url, timeout=30000)
                    if success:
                        return {"success": True, "action_taken": "switch_engine"}
                    else:
                        return {"success": False, "error": "切换搜索引擎后页面加载失败"}
                else:
                    return {"success": False, "error": f"无效的搜索引擎索引: {engine_index}"}

            elif action_type == "change_query":
                new_query = params.get("query", "")
                if new_query:
                    print(f"🔄 更改搜索词: {new_query}")
                    self.movie_name = new_query  # 更新类变量，确保后续迭代使用新搜索词
                    # 在当前搜索引擎搜索
                    engine = self.SEARCH_ENGINES[self.current_engine_index]
                    search_url = f"{engine['url']}{quote(new_query)}"
                    success = await self._goto_with_retry(page, search_url, timeout=30000)
                    if success:
                        return {"success": True, "action_taken": "change_query"}
                    else:
                        return {"success": False, "error": "更改搜索词后页面加载失败"}
                else:
                    return {"success": False, "error": "未提供新搜索词"}

            elif action_type == "stop":
                print("⏹️  LLM 决定停止搜索")
                return {"success": True, "action_taken": "stop", "done": True}

            else:
                return {"success": False, "error": f"未知操作类型: {action_type}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def search_movie(self, movie_name: str) -> dict:
        """使用 LLM 智能导航搜索电影 magnet links"""
        
        # 初始化类变量
        self.movie_name = movie_name

        print(f"\n{'='*70}")
        print(f"🎬 开始智能搜索电影: {movie_name}")
        print(f"🤖 使用 LLM 提供商: {self.llm_provider.upper()}")
        print(f"{'='*70}\n")

        # 检查 API Key
        if self.llm_provider == "azure":
            if not AZURE_OPENAI_API_KEY:
                print("❌ 错误: 未设置 AZURE_OPENAI_API_KEY 环境变量")
                print("Azure OpenAI 功能需要 API Key 才能运行")
                print("提示: 复制 .env.example 为 .env 并填入真实的 API Key\n")
                return {
                    "movie_name": movie_name,
                    "total_found": 0,
                    "magnet_links": [],
                    "error": "未设置 AZURE_OPENAI_API_KEY"
                }
        else:
            if not DASHSCOPE_API_KEY:
                print("❌ 错误: 未设置 DASHSCOPE_API_KEY 环境变量")
                print("LLM 智能导航功能需要 API Key 才能运行")
                print("提示: 复制 .env.example 为 .env 并填入真实的 API Key\n")
                return {
                    "movie_name": movie_name,
                    "total_found": 0,
                    "magnet_links": [],
                    "error": "未设置 DASHSCOPE_API_KEY"
                }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            browser_context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await browser_context.new_page()
            
            iteration = 0  # 在 try 外部定义，确保 finally 中可访问
            
            try:
                # 初始搜索
                initial_query = f"{self.movie_name} magnet 下载"
                engine = self.SEARCH_ENGINES[0]
                search_url = f"{engine['url']}{quote(initial_query)}"

                print(f"🔍 初始搜索: {initial_query}")
                success = await self._goto_with_retry(page, search_url, timeout=30000)
                if not success:
                    print("❌ 初始搜索页面加载失败")
                    return {
                        "movie_name": self.movie_name,
                        "total_found": 0,
                        "magnet_links": [],
                        "error": "初始搜索失败"
                    }

                # 智能导航循环
                for iteration in range(1, self.max_iterations + 1):
                    print(f"\n{'─'*70}")
                    print(f"📍 迭代 {iteration}/{self.max_iterations}")
                    print(f"{'─'*70}")

                    # 获取当前页面信息
                    current_url = page.url
                    html = await page.content()

                    # 提取 magnet links
                    magnets = self.extract_magnet_links(html)
                    print(f"🧲 当前页面 magnet links: {len(magnets)} (累计: {len(self.found_magnets)})")

                    # 如果已找到足够的 magnet links，可以提前结束
                    if len(self.found_magnets) >= self.min_magnets:
                        print(f"\n✅ 已找到 {len(self.found_magnets)} 个 magnet links，完成搜索")
                        break

                    # 提取页面内容
                    page_content = self.extract_page_content(html)

                    # 提取链接
                    links = self.extract_links(html, current_url)

                    # 构建 LLM 决策上下文（使用类变量 self.movie_name）
                    llm_context = {
                        "current_url": current_url,
                        "page_content": page_content,
                        "links": links,
                        "magnet_count": len(magnets),
                        "iteration": iteration,
                        "movie_name": self.movie_name  # 使用类变量，支持动态更新
                    }

                    # 调用 LLM 规划下一步
                    print("\n🤖 正在咨询 LLM 规划下一步操作...")
                    plan_result = await self.plan_next_action(llm_context)

                    if not plan_result["success"]:
                        print(f"❌ LLM 规划失败: {plan_result.get('error')}")
                        print("尝试默认策略：点击第一个链接")
                        if links:
                            # 尝试点击第一个相关链接
                            action = {"action": "click_link", "params": {"link_index": 1}}
                            await self.execute_action(page, action, llm_context)
                        continue

                    # 执行 LLM 规划的操作
                    decision = plan_result["decision"]
                    exec_result = await self.execute_action(page, decision, llm_context)

                    if not exec_result["success"]:
                        print(f"❌ 操作执行失败: {exec_result.get('error')}")
                        # 尝试恢复：返回上一页或重新搜索
                        if iteration < self.max_iterations:
                            print("尝试继续...")
                            continue

                    # 检查是否应该停止
                    if exec_result.get("done"):
                        break

                    # 避免过快操作
                    await asyncio.sleep(1)
                    
            finally:
                # 确保浏览器资源被正确释放
                await browser.close()

        print(f"\n{'='*70}")
        print(f"🎉 搜索完成! 共找到 {len(self.found_magnets)} 个 magnet links")
        print(f"{'='*70}\n")

        return {
            "movie_name": self.movie_name,  # 返回可能更新后的电影名
            "total_found": len(self.found_magnets),
            "magnet_links": self.found_magnets,
            "iterations": iteration,
            "search_history": self.search_history[-10:]  # 保留最近10条历史
        }

    async def analyze_with_llm(self, movie_name: str, magnet_links: List[str]) -> dict:
        """使用 LLM 分析并选择最佳 magnet link"""
        if not magnet_links:
            return {"best_match": None, "reason": "未找到任何 magnet links"}

        # 从配置文件获取分析提示
        prompt = get_analysis_prompt(movie_name, magnet_links)

        messages = [{"role": "user", "content": prompt}]
        result = await self.call_qwen_api(messages, temperature=0.3)

        if result["success"]:
            content = result["content"]
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                return json.loads(content)
            except json.JSONDecodeError:
                return {"best_match": magnet_links[0], "reason": "JSON 解析失败，返回第一个", "raw": content}
        else:
            return {"best_match": magnet_links[0], "reason": "API 调用失败，返回第一个"}

    def format_result(self, result: dict) -> str:
        """格式化搜索结果"""
        output = [
            f"\n{'='*70}",
            f"🎬 搜索结果: {result['movie_name']}",
            f"{'='*70}",
            f"📊 找到数量: {result['total_found']}",
            f"🔄 迭代次数: {result.get('iterations', 'N/A')}",
            f"",
        ]

        if result['magnet_links']:
            output.append("🧲 Magnet Links:")
            for i, magnet in enumerate(result['magnet_links'], 1):
                output.append(f"  {i}. {magnet}")
        else:
            output.append("❌ 未找到任何 magnet links")

        output.append(f"{'='*70}\n")
        return "\n".join(output)


async def main():
    """主函数"""
    # 检查环境变量
    if LLM_PROVIDER == "azure":
        if not AZURE_OPENAI_API_KEY or AZURE_OPENAI_API_KEY == "your_azure_api_key_here":
            print("⚠️  警告: 未设置 AZURE_OPENAI_API_KEY 环境变量")
            print("Azure OpenAI 功能需要 API Key 才能运行")
            print("提示: 复制 .env.example 为 .env 并填入真实的 API Key\n")
            return
    else:
        if not DASHSCOPE_API_KEY or DASHSCOPE_API_KEY == "your_api_key_here":
            print("⚠️  警告: 未设置 DASHSCOPE_API_KEY 环境变量")
            print("LLM 智能导航功能需要 API Key 才能运行")
            print("提示: 复制 .env.example 为 .env 并填入真实的 API Key\n")
            return

    # 获取用户输入
    movie_name = input("请输入要搜索的电影名称: ").strip()
    if not movie_name:
        print("❌ 错误: 电影名称不能为空")
        return

    # 执行搜索
    searcher = MovieSearcher(max_iterations=15, min_magnets=5, max_retries=3)
    try:
        result = await searcher.search_movie(movie_name)
        # 输出结果
        print(searcher.format_result(result))

        # 如果找到结果，自动使用 LLM 推荐最佳下载源
        if result['magnet_links']:
            print("\n🤖 正在分析并推荐最佳 magnet link...")
            analysis = await searcher.analyze_with_llm(movie_name, result['magnet_links'])
            print(f"\n💡 LLM 推荐:")
            print(f"  最佳匹配: {analysis.get('best_match', 'N/A')}")
            print(f"  理由: {analysis.get('reason', 'N/A')}")
            print(f"  质量: {analysis.get('quality', 'N/A')}")
            print(f"  置信度: {analysis.get('confidence', 'N/A')}")

    finally:
        await searcher.close()


if __name__ == "__main__":
    asyncio.run(main())
