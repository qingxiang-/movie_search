#!/usr/bin/env python3
"""
测试 LLM 股票预测 - 只测试 AAPL
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.stock_agent import StockAnalysisAgent
from prompts.stock_prompts import get_prediction_prompt


async def test_aapl():
    """测试 AAPL"""
    
    print("\n" + "="*70)
    print("🔮 测试 AAPL - LLM 预测")
    print("="*70)
    
    agent = StockAnalysisAgent()
    
    # 1. 获取数据
    print("\n📊 Step 1: 获取数据...")
    stock_data = agent.get_stock_data('AAPL')
    
    if not stock_data:
        print("❌ 数据获取失败")
        return
    
    print(f"   ✅ 获取 {stock_data['data_points']} 天数据")
    print(f"   💰 当前价格: ${stock_data['current_price']}")
    print(f"   📈 历史收益: 1M={stock_data['returns']['1m']:+.1f}%, 3M={stock_data['returns']['3m']:+.1f}%, 6M={stock_data['returns']['6m'] or 'N/A'}")
    print(f"   📉 RSI: {stock_data['rsi']} | 趋势: {stock_data['trend']}")
    
    # 2. 显示 Prompt
    print("\n📝 Step 2: LLM Prompt (前500字预览)...")
    prompt = get_prediction_prompt('AAPL', stock_data)
    print(f"   {prompt[:500]}...")
    print(f"   ... (共 {len(prompt)} 字)")
    
    # 3. 调用 LLM (如果配置了)
    print("\n🔮 Step 3: 调用 LLM 预测...")
    
    try:
        # 尝试导入 LLM client
        from core.llm_client import LLMClient
        llm = LLMClient()
        
        messages = [{"role": "user", "content": prompt}]
        result = await llm.call(messages, temperature=0.3, max_tokens=2000)
        
        if result["success"]:
            print("   ✅ LLM 响应成功")
            
            # 解析 JSON
            content = result["content"]
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                prediction = json.loads(content)
                
                # 显示结果
                print(f"\n{'='*70}")
                print("📊 LLM 预测结果")
                print("="*70)
                
                if 'predicted_return' in prediction:
                    pred_return = prediction['predicted_return']
                    pred_price = stock_data['current_price'] * (1 + pred_return / 100)
                    
                    print(f"""
🔮 未来6个月预测
   预测收益: {pred_return:+.1f}%
   预测价格: ${pred_price:.2f}
   置信度: {prediction.get('confidence', 'N/A')}
   风险等级: {prediction.get('risk_level', 'N/A')}
   建议: {prediction.get('recommendation', 'N/A')}
   
📝 分析逻辑
   {prediction.get('reasoning', 'N/A')}
   
🔑 关键因素
""")
                    for factor in prediction.get('key_factors', []):
                        print(f"   • {factor}")
                    
                    if prediction.get('upside_factors'):
                        print(f"\n🟢 上涨因素")
                        for f in prediction.get('upside_factors', []):
                            print(f"   • {f}")
                    
                    if prediction.get('downside_factors'):
                        print(f"\n🔴 下跌因素")
                        for f in prediction.get('downside_factors', []):
                            print(f"   • {f}")
                    
                    print(f"\n📐 交易建议")
                    print(f"   入场价: ${prediction.get('entry_price', 'N/A')}")
                    print(f"   止损价: ${prediction.get('stop_loss', 'N/A')}")
                    print(f"   目标价: ${prediction.get('target_price_6m', 'N/A')}")
                
                else:
                    print(f"   ⚠️ {prediction.get('error', '解析失败')}")
                    print(f"\n原始响应:\n{content}")
                
                # 保存完整结果
                full_result = {
                    'stock_data': stock_data,
                    'prediction': prediction,
                    'llm_raw': result["content"]
                }
                
                json_file = f"data/llm_prediction_AAPL_{datetime.now().strftime('%Y-%m-%d')}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(full_result, f, ensure_ascii=False, indent=2, default=str)
                print(f"\n💾 结果已保存: {json_file}")
                
            except json.JSONDecodeError as e:
                print(f"   ⚠️ JSON解析失败: {e}")
                print(f"   原始响应:\n{content}")
        else:
            print(f"   ❌ LLM调用失败: {result.get('error')}")
            
    except ImportError:
        print("   ⚠️ 未配置 LLM client")
        print("   📋 数据已准备好，可以配置LLM后调用")
        print(f"\n📦 完整数据:")
        print(json.dumps(stock_data, indent=2, ensure_ascii=False))
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(test_aapl())
