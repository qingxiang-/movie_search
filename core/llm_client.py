"""
LLM Client - 封装 LLM API 调用
"""

import os
import asyncio
import httpx
from typing import List, Dict, Any


class LLMClient:
    """LLM API 客户端（支持 Qwen 和 Azure OpenAI）"""

    def __init__(self,
                 base_url: str = None,
                 api_key: str = None,
                 model: str = None,
                 timeout: float = 60.0):
        """
        初始化 LLM 客户端

        Args:
            base_url: API 基础 URL
            api_key: API Key
            model: 模型名称
            timeout: 超时时间（秒）
        """
        # 获取 LLM 提供商配置
        self.provider = os.getenv("LLM_PROVIDER", "qwen").lower()
        self.timeout = timeout

        # Azure OpenAI 客户端 (延迟初始化)
        self._azure_client = None

        # Qwen 配置
        self.base_url = base_url or os.getenv("DASHSCOPE_BASE_URL",
                                               "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self.model = model or os.getenv("DASHSCOPE_MODEL", "qwen-flash-2025-07-28")

        self.http_client = httpx.AsyncClient(timeout=timeout)

    def _get_azure_client(self):
        """获取 Azure OpenAI 客户端 (延迟初始化)"""
        if self._azure_client is None:
            from openai import AzureOpenAI
            azure_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

            self._azure_client = AzureOpenAI(
                api_key=azure_api_key,
                api_version=azure_api_version,
                azure_endpoint=azure_endpoint.rstrip('/') if azure_endpoint else ""
            )
        return self._azure_client

    @property
    def azure_deployment(self):
        return os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.http_client.aclose()
    
    async def call(self,
                   messages: List[Dict[str, str]],
                   temperature: float = 0.7,
                   max_tokens: int = 2000) -> Dict[str, Any]:
        """
        调用 LLM API（支持 Qwen 和 Azure OpenAI）

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            {"success": bool, "content": str} 或 {"success": bool, "error": str}
        """
        try:
            # 重新加载环境变量以确保最新配置
            from dotenv import load_dotenv
            load_dotenv('.env')

            provider = os.getenv("LLM_PROVIDER", "qwen").lower()

            if provider == "azure":
                # 使用新版 Azure OpenAI SDK
                client = self._get_azure_client()

                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.chat.completions.create(
                        model=self.azure_deployment,
                        messages=messages,
                        temperature=temperature,
                    )
                )
                content = response.choices[0].message.content
                return {"success": True, "content": content}
            else:
                # 调用 Qwen API
                base_url = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
                api_key = os.getenv("DASHSCOPE_API_KEY", "")
                model = os.getenv("DASHSCOPE_MODEL", "qwen-flash-2025-07-28")
                
                url = f"{base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                }
                
                response = await self.http_client.post(url, json=data, headers=headers)
                response.raise_for_status()
                result = response.json()
                return {
                    "success": True, 
                    "content": result["choices"][0]["message"]["content"]
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
