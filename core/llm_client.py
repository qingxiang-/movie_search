"""
LLM Client - 封装 LLM API 调用
"""

import os
import httpx
from typing import List, Dict, Any


class LLMClient:
    """LLM API 客户端"""
    
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
        self.base_url = base_url or os.getenv("DASHSCOPE_BASE_URL", 
                                               "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self.model = model or os.getenv("DASHSCOPE_MODEL", "qwen-flash-2025-07-28")
        self.http_client = httpx.AsyncClient(timeout=timeout)
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.http_client.aclose()
    
    async def call(self, 
                   messages: List[Dict[str, str]], 
                   temperature: float = 0.7) -> Dict[str, Any]:
        """
        调用 LLM API
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            
        Returns:
            {"success": bool, "content": str} 或 {"success": bool, "error": str}
        """
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
        
        try:
            response = await self.http_client.post(url, json=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            return {
                "success": True, 
                "content": result["choices"][0]["message"]["content"]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
