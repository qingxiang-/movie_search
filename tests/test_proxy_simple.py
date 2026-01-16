#!/usr/bin/env python3
"""
简单的代理连通性测试
使用 httpx 测试通过代理访问 Google Scholar 和 arXiv
"""

import httpx
import asyncio


async def test_with_proxy():
    """使用代理测试"""
    
    proxy_url = "http://127.0.0.1:7890"
    
    print("="*70)
    print("网络连通性测试（使用代理）")
    print("="*70)
    print(f"代理: {proxy_url}")
    print()
    
    # 配置代理
    proxies = {
        "http://": proxy_url,
        "https://": proxy_url
    }
    
    test_urls = [
        ("Google", "https://www.google.com"),
        ("Google Scholar", "https://scholar.google.com/scholar?q=machine+learning"),
        ("arXiv", "https://arxiv.org/search/?query=machine+learning"),
    ]
    
    async with httpx.AsyncClient(proxies=proxies, timeout=30.0, follow_redirects=True) as client:
        for name, url in test_urls:
            print(f"\n{'─'*70}")
            print(f"测试: {name}")
            print(f"URL: {url}")
            print("─"*70)
            
            try:
                print("⏳ 正在访问...")
                response = await client.get(url)
                
                print(f"✅ HTTP 状态码: {response.status_code}")
                print(f"✅ 响应大小: {len(response.content)} 字节")
                
                # 检查内容
                content = response.text
                if name == "Google Scholar" and "gs_ri" in content:
                    print("✅ 找到论文结果元素（gs_ri）")
                elif name == "arXiv" and "arxiv-result" in content:
                    print("✅ 找到论文结果元素（arxiv-result）")
                elif name == "Google" and "<title>Google</title>" in content:
                    print("✅ 成功访问 Google")
                else:
                    print(f"⚠️  页面内容可能不完整")
                    # 显示前200个字符
                    print(f"   内容预览: {content[:200]}...")
                
            except httpx.ProxyError as e:
                print(f"❌ 代理错误: {e}")
                print("   请检查代理是否正在运行（127.0.0.1:7890）")
            except httpx.TimeoutException:
                print("❌ 访问超时（30秒）")
            except Exception as e:
                print(f"❌ 访问失败: {e}")


async def test_without_proxy():
    """不使用代理测试"""
    
    print("\n" + "="*70)
    print("网络连通性测试（不使用代理）")
    print("="*70)
    print()
    
    test_urls = [
        ("Google", "https://www.google.com"),
        ("百度", "https://www.baidu.com"),
    ]
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for name, url in test_urls:
            print(f"\n测试: {name}")
            try:
                print("⏳ 正在访问...")
                response = await client.get(url)
                print(f"✅ HTTP 状态码: {response.status_code}")
            except Exception as e:
                print(f"❌ 访问失败: {e}")


async def main():
    """主函数"""
    # 测试使用代理
    await test_with_proxy()
    
    # 测试不使用代理
    await test_without_proxy()
    
    print("\n" + "="*70)
    print("测试完成")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
