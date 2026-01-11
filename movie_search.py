#!/usr/bin/env python3
"""
电影 Magnet Link 搜索工具
使用 Playwright 无头浏览器搜索电影并提取 magnet link
"""

import os
import re
import json
import asyncio
from typing import List, Optional
from urllib.parse import quote

from playwright.async_api import async_playwright, Page
import httpx
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 从环境变量加载配置
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-flash-2025-07-28")


class MovieSearcher:
    """电影 magnet link 搜索器"""

    # 常用 BT 搜索站点
    SEARCH_SITES = [
        "https://www.btdigs.com/",
        "https://btso.xyz/",
        "https://www.magnetdl.com/",
    ]

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.http_client.aclose()

    async def call_qwen_api(self, messages: list) -> dict:
        """调用 Qwen API"""
        url = f"{DASHSCOPE_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "model": DASHSCOPE_MODEL,
            "messages": messages,
            "temperature": 0.3,
        }

        try:
            response = await self.http_client.post(url, json=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            return {"success": True, "content": result["choices"][0]["message"]["content"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def search_with_llm(self, movie_name: str, magnet_links: List[str]) -> dict:
        """使用 LLM 分析搜索结果并选择最佳 magnet link"""
        magnets_str = "\n".join([f"{i+1}. {m}" for i, m in enumerate(magnet_links[:10])])

        prompt = f"""你是一个电影资源搜索助手。用户正在搜索电影: {movie_name}

请分析以下搜索到的 magnet links，返回最佳选择：
{magnets_str}

选择标准：
1. 种子健康度（Seeder 数量多）
2. 文件大小合理
3. 包含中英文名称匹配
4. 视频质量高（如 1080p, 4K, BluRay 等）

请以 JSON 格式返回：
{{
    "best_match": "最匹配的 magnet link（完整链接）",
    "reason": "选择理由",
    "quality": "视频质量",
    "size": "文件大小"
}}

如果没有找到合适的，返回：
{{
    "best_match": null,
    "reason": "未找到合适资源"
}}
"""

        messages = [{"role": "user", "content": prompt}]
        result = await self.call_qwen_api(messages)

        if result["success"]:
            content = result["content"]
            # 尝试解析 JSON
            try:
                # 提取 JSON 部分（可能被 ```json 包围）
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                analysis = json.loads(content)
                return {"llm_analysis": analysis}
            except json.JSONDecodeError:
                return {"llm_analysis": {"best_match": None, "reason": "JSON 解析失败", "raw_response": content}}
        else:
            return {"error": f"LLM 分析失败: {result['error']}"}

    def extract_magnet_links(self, page_text: str) -> List[str]:
        """从页面文本中提取所有 magnet links"""
        magnet_pattern = r'magnet:\?xt=urn:btih:[a-zA-Z0-9]{32,40}[^<>\s]*'
        return list(set(re.findall(magnet_pattern, page_text)))

    async def search_site(self, page: Page, site: str, movie_name: str) -> List[str]:
        """在单个站点搜索"""
        magnets = []

        try:
            # 构造搜索 URL（根据不同站点调整）
            if "btdigs" in site:
                search_url = f"{site}search?q={quote(movie_name)}"
            elif "btso" in site:
                search_url = f"{site}search/{quote(movie_name)}"
            elif "magnetdl" in site:
                search_url = f"{site}{movie_name[0].lower()}/{quote(movie_name)}/"
            else:
                search_url = f"{site}search?q={quote(movie_name)}"

            print(f"正在访问: {search_url}")
            await page.goto(search_url, timeout=15000, wait_until="domcontentloaded")

            # 等待页面加载
            await asyncio.sleep(2)

            # 提取 magnet links
            page_text = await page.content()
            magnets = self.extract_magnet_links(page_text)

            if magnets:
                print(f"✓ 在 {site} 找到 {len(magnets)} 个 magnet links")
            else:
                # 尝试点击第一个结果链接
                try:
                    links = await page.locator('a[href*="/detail/"], a[href*="/torrent/"], a.torrent-link').all()
                    if links:
                        await links[0].click()
                        await asyncio.sleep(2)
                        page_text = await page.content()
                        magnets = self.extract_magnet_links(page_text)
                        if magnets:
                            print(f"✓ 在 {site} 的详情页找到 {len(magnets)} 个 magnet links")
                except:
                    pass

        except Exception as e:
            print(f"✗ 搜索 {site} 失败: {str(e)}")

        return magnets

    async def search_movie(self, movie_name: str) -> dict:
        """搜索电影 magnet links"""
        all_magnets = []
        visited_sites = []

        print(f"\n{'='*60}")
        print(f"开始搜索电影: {movie_name}")
        print(f"{'='*60}\n")

        async with async_playwright() as p:
            # 使用 Chromium 无头模式
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            # 在多个站点搜索
            for site in self.SEARCH_SITES:
                magnets = await self.search_site(page, site, movie_name)
                if magnets:
                    all_magnets.extend(magnets)
                    visited_sites.append(site)

            await browser.close()

        # 去重
        all_magnets = list(set(all_magnets))

        result = {
            "movie_name": movie_name,
            "total_found": len(all_magnets),
            "magnet_links": all_magnets,
            "searched_sites": visited_sites,
        }

        # 如果找到 magnet links，使用 LLM 分析
        if all_magnets and DASHSCOPE_API_KEY:
            print(f"\n使用 LLM 分析 {len(all_magnets)} 个 magnet links...")
            llm_result = await self.search_with_llm(movie_name, all_magnets)
            result["analysis"] = llm_result

        return result

    def format_result(self, result: dict) -> str:
        """格式化搜索结果"""
        output = [
            f"\n{'='*60}",
            f"搜索结果: {result['movie_name']}",
            f"{'='*60}",
            f"搜索站点: {', '.join(result['searched_sites'])}",
            f"找到数量: {result['total_found']}",
            f"",
        ]

        if result['magnet_links']:
            output.append("Magnet Links:")
            for i, magnet in enumerate(result['magnet_links'], 1):
                output.append(f"  {i}. {magnet}")
        else:
            output.append("未找到任何 magnet links")

        if 'analysis' in result:
            analysis = result['analysis']
            if 'llm_analysis' in analysis:
                llm_result = analysis['llm_analysis']
                output.append(f"\nLLM 分析结果:")
                if 'best_match' in llm_result:
                    if llm_result['best_match']:
                        output.append(f"  最佳匹配: {llm_result['best_match']}")
                    if 'reason' in llm_result:
                        output.append(f"  理由: {llm_result['reason']}")
                    if 'quality' in llm_result:
                        output.append(f"  质量: {llm_result['quality']}")
                    if 'size' in llm_result:
                        output.append(f"  大小: {llm_result['size']}")
                elif 'raw_response' in llm_result:
                    output.append(f"  原始响应: {llm_result['raw_response']}")
            elif 'error' in analysis:
                output.append(f"\nLLM 分析失败: {analysis['error']}")

        output.append(f"{'='*60}\n")
        return "\n".join(output)


async def main():
    """主函数"""
    # 检查环境变量（可选，不设置也能进行基础搜索）
    if not DASHSCOPE_API_KEY or DASHSCOPE_API_KEY == "your_api_key_here":
        print("警告: 未设置 DASHSCOPE_API_KEY 环境变量")
        print("LLM 分析功能将被禁用，仅进行基础搜索")
        print("提示: 复制 .env.example 为 .env 并填入真实的 API Key 以启用 LLM 分析\n")

    # 获取用户输入
    movie_name = input("请输入要搜索的电影名称: ").strip()
    if not movie_name:
        print("错误: 电影名称不能为空")
        return

    # 执行搜索
    searcher = MovieSearcher()
    try:
        result = await searcher.search_movie(movie_name)
        # 输出结果
        print(searcher.format_result(result))
    finally:
        await searcher.close()


if __name__ == "__main__":
    asyncio.run(main())
