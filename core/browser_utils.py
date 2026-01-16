"""
Browser Utils - 浏览器相关工具函数
"""

import asyncio
from typing import List, Dict
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.async_api import Page


class BrowserUtils:
    """浏览器工具类"""
    
    @staticmethod
    def extract_page_content(html: str, 
                            max_length: int = 8000,
                            keywords: List[str] = None) -> str:
        """
        提取页面核心内容，优先保留包含关键词的段落
        
        Args:
            html: HTML 内容
            max_length: 最大长度
            keywords: 关键词列表（用于优先排序）
            
        Returns:
            提取的文本内容
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除脚本和样式
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        if keywords:
            # 提取所有段落并按关键词权重排序
            paragraphs = []
            for tag in soup.find_all(['p', 'div', 'article', 'section']):
                text = tag.get_text(strip=True)
                if text and len(text) > 20:
                    weight = sum(1 for kw in keywords if kw and kw.lower() in text.lower())
                    paragraphs.append((weight, text))
            
            # 按权重排序
            paragraphs.sort(key=lambda x: x[0], reverse=True)
            combined_text = ' '.join(p[1] for p in paragraphs)
        else:
            # 简单提取全文本
            combined_text = soup.get_text()
            lines = (line.strip() for line in combined_text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            combined_text = ' '.join(chunk for chunk in chunks if chunk)
        
        # 限制长度
        if len(combined_text) > max_length:
            combined_text = combined_text[:max_length] + "..."
        
        return combined_text
    
    @staticmethod
    def extract_links(html: str, 
                     base_url: str, 
                     max_links: int = 15) -> List[Dict[str, str]]:
        """
        提取页面中的关键链接
        
        Args:
            html: HTML 内容
            base_url: 基础 URL
            max_links: 最大链接数
            
        Returns:
            链接列表 [{"text": "链接文本", "url": "链接地址"}]
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for a in soup.find_all('a', href=True):
            if len(links) >= max_links:
                break
            
            href = a['href']
            text = a.get_text(strip=True)
            
            # 过滤无用链接
            if not text or len(text) < 2:
                continue
            if href.startswith('javascript:') or href.startswith('#'):
                continue
            if href.startswith('//'):
                href = 'https:' + href
            elif not href.startswith('http'):
                href = urljoin(base_url, href)
            
            links.append({
                "text": text[:100],
                "url": href
            })
        
        return links
    
    @staticmethod
    async def goto_with_retry(page: Page, 
                             url: str, 
                             timeout: int = 15000,
                             max_retries: int = 3) -> bool:
        """
        带重试机制的页面导航
        
        Args:
            page: Playwright Page 对象
            url: 目标 URL
            timeout: 超时时间（毫秒）
            max_retries: 最大重试次数
            
        Returns:
            是否成功
        """
        for attempt in range(max_retries):
            try:
                await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  导航失败 (尝试 {attempt + 1}/{max_retries}): {str(e)[:50]}")
                    await asyncio.sleep(1)
                else:
                    print(f"❌ 导航失败，已重试 {max_retries} 次: {str(e)[:50]}")
                    return False
        return False
