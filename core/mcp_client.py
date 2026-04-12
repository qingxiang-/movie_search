"""
MCP (Model Context Protocol) Client - 模型上下文协议客户端
实现与MCP服务器的通信，提供搜索、数据获取和分析功能
"""

import os
import httpx
import asyncio
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class MCPClient:
    """MCP (Model Context Protocol) 客户端"""

    def __init__(self, base_url: str = None, timeout: float = 60.0):
        """
        初始化 MCP 客户端

        Args:
            base_url: MCP 服务器基础 URL
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url or os.getenv("MCP_BASE_URL", "http://localhost:3000")
        self.timeout = timeout

        # 支持的服务类型
        self.services = {
            "search": "search",
            "retrieve": "retrieve",
            "analyze": "analyze",
            "generate": "generate"
        }

        self.http_client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """关闭HTTP客户端"""
        await self.http_client.aclose()

    async def call_service(self, service_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用MCP服务

        Args:
            service_type: 服务类型
            params: 请求参数

        Returns:
            服务响应
        """
        try:
            endpoint = f"{self.base_url}/api/{self.services.get(service_type, service_type)}"

            response = await self.http_client.post(
                endpoint,
                json=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def search(self, query: str, sources: List[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        执行搜索操作

        Args:
            query: 搜索查询
            sources: 数据源列表
            limit: 结果数量限制

        Returns:
            搜索结果
        """
        params = {
            "query": query,
            "sources": sources or ["web", "news", "finance"],
            "limit": limit
        }

        return await self.call_service("search", params)

    async def retrieve(self, url: str, format: str = "text") -> Dict[str, Any]:
        """
        检索指定URL的内容

        Args:
            url: 目标URL
            format: 返回格式 (text, json, html)

        Returns:
            内容响应
        """
        params = {
            "url": url,
            "format": format
        }

        return await self.call_service("retrieve", params)

    async def analyze(self, content: str, task: str = "summarize") -> Dict[str, Any]:
        """
        分析内容

        Args:
            content: 要分析的内容
            task: 分析任务类型 (summarize, sentiment, keywords)

        Returns:
            分析结果
        """
        params = {
            "content": content,
            "task": task
        }

        return await self.call_service("analyze", params)

    async def generate(self, prompt: str, model: str = "qwen-flash") -> Dict[str, Any]:
        """
        生成内容

        Args:
            prompt: 生成提示
            model: 使用的模型

        Returns:
            生成结果
        """
        params = {
            "prompt": prompt,
            "model": model
        }

        return await self.call_service("generate", params)

    async def financial_analysis(self, ticker: str, metrics: List[str] = None) -> Dict[str, Any]:
        """
        财务分析

        Args:
            ticker: 股票代码
            metrics: 要分析的指标

        Returns:
            财务分析结果
        """
        params = {
            "ticker": ticker,
            "metrics": metrics or ["valuation", "growth", "profitability", "risk"]
        }

        return await self.call_service("analyze", params)


# 全局 MCP 客户端实例（单例模式）
_mcp_client_instance = None


def get_mcp_client() -> MCPClient:
    """获取全局 MCP 客户端实例（单例模式）"""
    global _mcp_client_instance

    if _mcp_client_instance is None:
        _mcp_client_instance = MCPClient()

    return _mcp_client_instance


# 上下文管理器
class MCPContext:
    """MCP 上下文管理器"""

    def __init__(self, base_url: str = None, timeout: float = 60.0):
        self.client = MCPClient(base_url, timeout)

    async def __aenter__(self):
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()


# 使用示例
if __name__ == "__main__":
    async def test_mcp_client():
        """测试 MCP 客户端"""
        print("测试 MCP 客户端...")

        async with MCPContext() as client:
            # 测试搜索
            print("\n1. 测试搜索功能:")
            search_result = await client.search("Apple stock price", limit=5)
            print(f"搜索成功: {search_result.get('success', False)}")
            if search_result.get('success'):
                print(f"结果数量: {len(search_result.get('data', []))}")

            # 测试财务分析
            print("\n2. 测试财务分析功能:")
            finance_result = await client.financial_analysis("AAPL")
            print(f"分析成功: {finance_result.get('success', False)}")
            if finance_result.get('success'):
                print("分析指标:", list(finance_result.get('data', {}).keys()))

        print("\n测试完成!")

    asyncio.run(test_mcp_client())
