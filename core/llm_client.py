"""
LLM Client - 封装 LLM API 调用
"""

import os
import asyncio
import httpx
import openai
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
        
        # Qwen 配置
        self.base_url = base_url or os.getenv("DASHSCOPE_BASE_URL", 
                                               "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self.model = model or os.getenv("DASHSCOPE_MODEL", "qwen-flash-2025-07-28")
        self.http_client = httpx.AsyncClient(timeout=timeout)
        
        # Azure OpenAI 配置
        if self.provider == "azure":
            azure_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
            self.azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
            
            if azure_api_key:
                openai.api_type = "azure"
                openai.api_key = azure_api_key
                openai.api_base = azure_endpoint
                openai.api_version = azure_api_version
    
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
            if self.provider == "azure":
                # 调用 Azure OpenAI (使用 openai v0.28.1 API)
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: openai.ChatCompletion.create(
                        engine=self.azure_deployment,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                )
                content = response.choices[0].message["content"]
                return {"success": True, "content": content}
            else:
                # 调用 Qwen API
                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                data = {
                    "model": self.model,
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
