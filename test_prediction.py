#!/usr/bin/env python3
"""
测试 AAPL - 数据获取 + 简单规则预测
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.stock_agent import StockAnalysisAgent


def simple_prediction(stock_data):
    """简单规则预测 (LLM不可用时备用)"""
    
    current = stock_data['current_price']
    returns = stock_data['returns']
    rsi = stock_data['rsi']
    trend = stock_data['trend']
    position = stock_data['position']
    volatility = stock_data['volatility']
    
    # 因素评分
    factors = []
    score = 0
    
    # 趋势 (权重 30%)
    if trend == "上升":
        score += 7
        factors.append("✓ 处于上升趋势")
    elif trend == "下降":
        score -= 7
        factors.append("✗ 处于下降趋势")
    else:
        factors.append("○ 处于震荡整理")
    
    # RSI (权重 20%)
    if rsi > 70:
        score -= 3
        factors.append("⚠ RSI超买(>70)，有回调压力")
    elif rsi < 30:
        score += 3
        factors.append("✓ RSI超卖(<30)，有反弹机会")
    elif 50 <= rsi <= 70:
        score += 2
        factors.append("○ RSI偏强(50-70)")
    elif 30 <= rsi < 50:
        score -= 2
        factors.append("○ RSI偏弱(30-50)")
    
    # 均线位置 (权重 25%)
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
    
    # 历史动量 (权重 25%)
    r1m = returns['1m']
    r3m = returns['3m']
    if r1m > 10:
        score += 5
        factors.append("✓ 短期动能强劲(+10%以上)")
    elif r1m > 5:
        score += 3
        factors.append("○ 短期偏强")
    elif r1m < -10:
        score -= 5
        factors.append("✗ 短期动能疲弱(-10%以下)")
    elif r1m < -5:
        score -= 3
        factors.append("○ 短期偏弱")
    
    # 波动率调整
    if volatility > 40:
        score -= 1
        factors.append("⚠ 高波动(>40%)，风险较大")
    elif volatility < 20:
        score += 1
        factors.append("✓ 低波动(<20%)，风险可控")
    
    # 归一化到 -20% ~ +20% 区间
    base_return = (score / 20) * 20
    
    # 趋势外推
    if trend == "上升":
        base_return += 5
    elif trend == "下降":
        base_return -= 5
    
    # RSI 回归
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
    
    # 风险等级
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
    
    # 预测价格
    predicted_price = current * (1 + base_return / 100)
    
    return {
        "predicted_return": round(base_return, 1),
        "predicted_price": round(predicted_price, 2),
        "confidence": confidence,
        "risk_level": risk,
        "recommendation": recommendation,
        "current_phase": f"{trend}趋势" + ("整理期" if trend == "震荡" else ""),
        "momentum": "强势" if score > 10 else ("中性" if score > -10 else "弱势"),
        "reasoning": f"综合评分{score}分，基于{'看涨' if base_return > 0 else '看跌'}趋势",
        "key_factors": factors,
        "upside_factors": [
            "RSI从超买区域回落，可能获得支撑" if rsi > 60 else "短期技术指标偏弱，但中长期趋势未破",
            "历史收益显示增长惯性" if returns['1m'] > 0 else "短期回调后估值吸引力增加"
        ],
        "downside_factors": [
            "RSI超买区域" if rsi > 70 else "市场整体波动可能影响",
            "高估值板块可能有调整压力" if volatility > 30 else "宏观不确定性"
        ],
        "entry_price": round(current * 0.95, 2),
        "stop_loss": round(current * 0.85, 2),
        "target_price_6m": round(predicted_price, 2)
    }


async def main():
    """测试 AAPL"""
    
    print("\n" + "="*70)
    print("🔮 测试 AAPL - 数据 + 规则预测")
    print("="*70)
    
    agent = StockAnalysisAgent()
    
    # 获取数据
    print("\n📊 Step 1: 获取数据...")
    stock_data = agent.get_stock_data('AAPL')
    
    if not stock_data:
        print("❌ 数据获取失败")
        return
    
    print(f"   ✅ 获取 {stock_data['data_points']} 天数据")
    print(f"   💰 当前价格: ${stock_data['current_price']}")
    print(f"   📈 历史收益: 1M={stock_data['returns']['1m']:+.1f}%, 3M={stock_data['returns']['3m']:+.1f}%")
    print(f"   📉 RSI: {stock_data['rsi']} | 趋势: {stock_data['trend']}")
    print(f"   📐 MA20: ${stock_data['ma']['ma20']} (vs_ma20: {stock_data['position']['vs_ma20']:+.1f}%)")
    print(f"   📐 MA50: ${stock_data['ma']['ma50']} (vs_ma50: {stock_data['position']['vs_ma50']:+.1f}%)")
    
    # 简单规则预测
    print("\n🔮 Step 2: 规则预测...")
    prediction = simple_prediction(stock_data)
    
    # 显示结果
    print(f"\n{'='*70}")
    print("📊 预测结果")
    print("="*70)
    
    pred_return = prediction['predicted_return']
    pred_price = stock_data['current_price'] * (1 + pred_return / 100)
    
    print(f"""
🔮 未来6个月预测
   预测收益: {pred_return:+.1f}%
   预测价格: ${pred_price:.2f}
   置信度: {prediction['confidence']}
   风险等级: {prediction['risk_level']}
   建议: {prediction['recommendation']}
   
📝 分析逻辑
   {prediction['reasoning']}
   当前: {prediction['current_phase']} | 动能: {prediction['momentum']}
   
🔑 关键因素
""")
    for f in prediction['key_factors']:
        print(f"   {f}")
    
    print(f"\n🟢 上涨因素")
    for f in prediction['upside_factors']:
        print(f"   • {f}")
    
    print(f"\n🔴 下跌因素")
    for f in prediction['downside_factors']:
        print(f"   • {f}")
    
    print(f"\n📐 交易建议")
    print(f"   入场价: ${prediction['entry_price']}")
    print(f"   止损价: ${prediction['stop_loss']}")
    print(f"   目标价: ${prediction['target_price_6m']}")
    
    print(f"\n{'='*70}")
    
    # 保存结果
    result = {
        'symbol': 'AAPL',
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'stock_data': stock_data,
        'prediction': prediction,
    }
    
    json_file = f"data/prediction_AAPL_{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"💾 结果已保存: {json_file}\n")


if __name__ == "__main__":
    asyncio.run(main())
