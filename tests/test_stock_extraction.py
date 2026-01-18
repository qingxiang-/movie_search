
import asyncio
import pytest
import os
import sys
import json
from datetime import datetime

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.stock_agent import StockAnalysisAgent
from playwright.async_api import async_playwright

async def verify_extraction(symbol):
    print(f"\n🧪 测试提取: {symbol}")
    agent = StockAnalysisAgent(proxy=os.getenv("HTTP_PROXY", "http://127.0.0.1:7890"))
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # 执行调研 (代码提取)
            details = await agent.research_stock_details(page, {"symbol": symbol})
            code_price = details.get('current_price', 'N/A')
            stats = details.get('key_statistics', {})
            
            # LLM 提取 (作为 Ground Truth)
            page_text = details.get('page_content', '')[:4000] # 提供足够的上下文
            prompt = f"""
            你是一个精准的数据提取助手。请从下面的 Yahoo Finance 页面文本中提取 {symbol} 的关键市场数据。
            如果找不到某个字段，请返回 "N/A"。
            
            页面文本:
            {page_text}
            
            请提取以下字段并以 JSON 格式返回:
            - current_price: 当前股价
            - previous_close: 前收盘价
            - open: 开盘价
            - day_range: 日内范围
            - year_range: 52周范围
            - volume: 成交量
            - market_cap: 市值
            - target_est: 1年目标价
            
            只返回 JSON，不要包含 Markdown 格式。
            """
            
            print("   🤖 正在请求 LLM 生成 Ground Truth...")
            messages = [{"role": "user", "content": prompt}]
            result = await agent.llm_client.call(messages, temperature=0.1)
            
            llm_data = {}
            if result["success"]:
                try:
                    content = result["content"].strip()
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    llm_data = json.loads(content)
                except Exception as e:
                    print(f"   ⚠️ LLM 解析失败: {e}")

            # 对比验证
            print(f"\n   📊 数据对比 ({symbol}):")
            print(f"   {'字段':<15} | {'代码提取':<15} | {'LLM提取 (GT)':<15} | {'状态':<10}")
            print(f"   {'-'*65}")
            
            fields_map = {
                'current_price': code_price,
                'previous_close': stats.get('previous_close', 'N/A'),
                'open': stats.get('open', 'N/A'),
                'day_range': stats.get('day_range', 'N/A'),
                'year_range': stats.get('year_range', 'N/A'),
                'volume': stats.get('volume', 'N/A'),
                'market_cap': stats.get('market_cap', 'N/A'),
                'target_est': stats.get('target_est', 'N/A')
            }
            
            match_count = 0
            for field, code_val in fields_map.items():
                llm_val = llm_data.get(field, 'N/A')
                # 简单清洗数据进行对比 (移除逗号等)
                c_val_clean = str(code_val).replace(',', '').strip()
                l_val_clean = str(llm_val).replace(',', '').strip()
                
                # 模糊匹配 (允许 N/A 或轻微格式差异)
                is_match = (c_val_clean == l_val_clean) or \
                           (code_val != 'N/A' and l_val_clean == 'N/A') or \
                           (code_val in str(llm_val)) # 代码提取的是 LLM 的一部分
                           
                status = "✅ 匹配" if is_match else "❌ 差异"
                if is_match: match_count += 1
                
                print(f"   {field:<15} | {str(code_val)[:15]:<15} | {str(llm_val)[:15]:<15} | {status}")

            return match_count >= 5 # 至少匹配 5 个核心字段算通过
            
        except Exception as e:
            print(f"   ❌ 测试失败: {str(e)}")
            return False
        finally:
            await browser.close()
            await agent.close()

async def test_main():
    test_symbols = ["AAPL", "GOOGL", "TSLA"]
    results = []
    for symbol in test_symbols:
        success = await verify_extraction(symbol)
        results.append(success)
        await asyncio.sleep(2) # 避免请求过快
    
    if all(results):
        print("\n✨ 所有基础数据提取测试通过！")
    else:
        print("\n❌ 部分测试未通过，请检查提取逻辑。")

if __name__ == "__main__":
    asyncio.run(test_main())
