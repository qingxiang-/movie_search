#!/usr/bin/env python3
"""
测试 AAPL - 使用 Azure OpenAI LLM 预测
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List
import numpy as np
import sys
import os

# 关键：加载 .env
from dotenv import load_dotenv
load_dotenv('.env')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.stock_agent import StockAnalysisAgent
from core.llm_client import LLMClient


def simple_prediction(stock_data):
    """简单规则预测 (备用方案)"""
    
    current = stock_data['current_price']
    returns = stock_data['returns']
    rsi = stock_data['rsi']
    trend = stock_data['trend']
    position = stock_data['position']
    volatility = stock_data['volatility']
    
    score = 0
    factors = []
    
    # 趋势
    if trend == "上升":
        score += 7
        factors.append("✓ 处于上升趋势")
    elif trend == "下降":
        score -= 7
        factors.append("✗ 处于下降趋势")
    else:
        factors.append("○ 处于震荡整理")
    
    # RSI
    if rsi > 70:
        score -= 3
        factors.append("⚠ RSI超买(>70)，有回调压力")
    elif rsi < 30:
        score += 3
        factors.append("✓ RSI超卖(<30)，有反弹机会")
    elif 50 <= rsi <= 70:
        score += 2
    elif 30 <= rsi < 50:
        score -= 2
    
    # 均线
    ma20_pos = position['vs_ma20']
    ma50_pos = position['vs_ma50']
    if ma20_pos > 5 and ma50_pos > 3:
        score += 4
        factors.append("✓ 价格在MA20/MA50上方，多头排列")
    elif ma20_pos < -5 or ma50_pos < -3:
        score -= 4
        factors.append("✗ 价格在均线下方，空头排列")
    else:
        factors.append("○ 价格围绕均线震荡")
    
    # 动量
    r1m = returns['1m']
    if r1m > 10:
        score += 5
    elif r1m > 5:
        score += 3
    elif r1m < -10:
        score -= 5
    elif r1m < -5:
        score -= 3
    
    # 波动率
    if volatility > 40:
        score -= 1
    elif volatility < 20:
        score += 1
    
    base_return = (score / 20) * 20
    
    # 趋势外推
    if trend == "上升":
        base_return += 5
    elif trend == "下降":
        base_return -= 5
    
    # RSI回归
    if rsi > 70:
        base_return -= 5
    elif rsi < 30:
        base_return += 5
    
    # 置信度
    if abs(base_return) > 15:
        confidence = "high"
    elif abs(base_return) > 8:
        confidence = "medium"
    else:
        confidence = "low"
    
    # 风险
    if volatility > 40 or abs(base_return) > 20:
        risk = "high"
    elif volatility > 25 or abs(base_return) > 10:
        risk = "medium"
    else:
        risk = "low"
    
    # 建议
    if base_return > 10:
        recommendation = "买入"
    elif base_return > 3:
        recommendation = "持有"
    elif base_return > -3:
        recommendation = "观望"
    elif base_return > -10:
        recommendation = "减仓"
    else:
        recommendation = "卖出"
    
    predicted_price = current * (1 + base_return / 100)
    
    return {
        "predicted_return": round(base_return, 1),
        "predicted_price": round(predicted_price, 2),
        "confidence": confidence,
        "risk_level": risk,
        "recommendation": recommendation,
        "current_phase": f"{trend}趋势",
        "momentum": "强势" if score > 10 else ("中性" if score > -10 else "弱势"),
        "reasoning": f"综合评分{score}分，基于{'看涨' if base_return > 0 else '看跌'}趋势",
        "key_factors": factors,
    }


async def call_llm_prediction(symbol: str, stock_data: Dict) -> Dict:
    """调用 Azure OpenAI 进行预测"""
    
    from prompts.stock_prompts import get_prediction_prompt
    
    prompt = get_prediction_prompt(symbol, stock_data)
    
    print("\n" + "="*70)
    print("🔮 调用 Azure OpenAI...")
    print("="*70)
    
    llm = LLMClient()
    messages = [{"role": "user", "content": prompt}]
    
    print(f"📤 发送 Prompt ({len(prompt)} 字)...")
    
    result = await llm.call(messages, temperature=0.3, max_tokens=2000)
    
    if result["success"]:
        print("✅ LLM 响应成功")
        
        content = result["content"]
        print(f"📥 收到响应 ({len(content)} 字)")
        
        # 解析 JSON
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            prediction = json.loads(content)
            return prediction
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败: {e}")
            return {"error": "解析失败", "raw": content}
    else:
        print(f"❌ LLM 调用失败: {result.get('error')}")
        return {"error": result.get('error')}


async def main():
    """测试 AAPL"""
    
    print("\n" + "="*70)
    print("🔮 AAPL 预测测试 - Azure OpenAI")
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
    print(f"   📈 历史: 1M={stock_data['returns']['1m']:+.1f}%, 3M={stock_data['returns']['3m']:+.1f}%")
    print(f"   📉 RSI: {stock_data['rsi']} | 趋势: {stock_data['trend']}")
    print(f"   📐 MA20: ${stock_data['ma']['ma20']} ({stock_data['position']['vs_ma20']:+.1f}%)")
    
    # 2. 调用 Azure OpenAI
    print("\n🚀 Step 2: 调用 Azure OpenAI...")
    
    provider = os.getenv('LLM_PROVIDER', 'qwen')
    print(f"   LLM Provider: {provider}")
    
    if provider == 'azure':
        prediction = await call_llm_prediction('AAPL', stock_data)
    else:
        print("   ⚠️ 使用备用规则预测")
        prediction = simple_prediction(stock_data)
    
    # 3. 显示结果
    print("\n" + "="*70)
    print("📊 预测结果")
    print("="*70)
    
    if 'error' in prediction:
        print(f"\n   ⚠️ {prediction['error']}")
        print("\n   使用备用规则预测...\n")
        prediction = simple_prediction(stock_data)
    
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
""")
        
        if 'reasoning' in prediction:
            print(f"📝 分析逻辑:")
            print(f"   {prediction['reasoning']}")
        
        if 'key_factors' in prediction:
            print(f"\n🔑 关键因素:")
            for f in prediction.get('key_factors', []):
                print(f"   • {f}")
        
        if 'upside_factors' in prediction:
            print(f"\n🟢 上涨因素:")
            for f in prediction.get('upside_factors', []):
                print(f"   • {f}")
        
        if 'downside_factors' in prediction:
            print(f"\n🔴 下跌因素:")
            for f in prediction.get('downside_factors', []):
                print(f"   • {f}")
        
        if 'target_price_6m' in prediction:
            print(f"\n📐 目标价: ${prediction['target_price_6m']}")
    else:
        print(f"\n   ⚠️ 预测失败: {prediction}")
    
    print(f"\n{'='*70}")
    
    # 保存结果
    result = {
        'symbol': 'AAPL',
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'stock_data': stock_data,
        'prediction': prediction,
    }
    
    json_file = f"data/llm_prediction_AAPL_{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"💾 结果已保存: {json_file}\n")


if __name__ == "__main__":
    # 安装依赖
    try:
        import dotenv
    except:
        os.system('pip install python-dotenv -q')
        import dotenv
    
    asyncio.run(main())
