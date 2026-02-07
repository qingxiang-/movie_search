"""
Stock Analysis - 未来6个月收益预测 (简化版，无需scipy)
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, List
import requests
import numpy as np
import sys
import os


class StockPredictor:
    """股票收益预测器 - 预测未来6个月"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_data(self, symbol: str, period: str = "2y") -> Optional[list]:
        """获取历史数据"""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {'range': period, 'interval': '1d'}
            
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            result = data.get('chart', {}).get('result', [])
            if not result:
                return None
            
            closes = result[0].get('indicators', {}).get('quote', [{}])[0].get('close', [])
            timestamps = result[0].get('timestamp', [])
            
            if not closes or not timestamps:
                return None
            
            return [
                {'date': datetime.fromtimestamp(ts).strftime('%Y-%m-%d'), 'close': c}
                for ts, c in zip(timestamps, closes) if c is not None
            ]
        except Exception as e:
            print(f"   ⚠️  获取 {symbol} 数据失败: {e}")
            return None
    
    def linear_regression(self, y: list) -> Dict:
        """线性回归"""
        x = np.arange(len(y))
        y = np.array(y)
        
        n = len(x)
        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_xx = np.sum(x * x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x) if (n * sum_xx - sum_x * sum_x) != 0 else 0
        intercept = (sum_y - slope * sum_x) / n
        
        # R²
        y_pred = intercept + slope * x
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        return {'slope': slope, 'intercept': intercept, 'r2': r_squared}
    
    def predict(self, symbol: str) -> Dict:
        """预测未来6个月收益"""
        
        history = self.get_data(symbol)
        if not history or len(history) < 60:
            return {'symbol': symbol, 'error': '数据不足'}
        
        closes = [h['close'] for h in history]
        current_price = closes[-1]
        
        # 历史6个月收益
        if len(closes) >= 126:
            start_price = closes[-126]
        else:
            start_price = closes[0]
        hist_return = ((current_price / start_price) - 1) * 100
        
        # 方法1: 线性回归
        lr = self.linear_regression(closes[-180:])  # 最近180天
        lr_return = (lr['slope'] * 126 / current_price) * 100
        
        # 方法2: 动量
        if len(closes) >= 60:
            mom_return = (closes[-1] / closes[-60] - 1) * 210 / 60  # 外推6个月
        else:
            mom_return = 0
        
        # 方法3: 均值回归
        mean_price = np.mean(closes[-120:])
        z_score = (current_price - mean_price) / np.std(closes[-120:]) if np.std(closes[-120:]) > 0 else 0
        mr_return = -z_score * 5  # Z-score 回归
        
        # 集成预测
        lr_w, mom_w, mr_w = 0.4, 0.35, 0.25
        predicted_return = lr_w * lr_return + mom_w * mom_return + mr_w * mr_return
        
        # 置信度
        confidence = 'high' if lr['r2'] > 0.6 else ('medium' if lr['r2'] > 0.3 else 'low')
        
        # 建议
        if predicted_return > 15:
            recommendation, reason = '买入', '多模型预测上涨超15%'
        elif predicted_return > 5:
            recommendation, reason = '持有', '模型倾向小幅上涨'
        elif predicted_return > -5:
            recommendation, reason = '观望', '模型预测区间震荡'
        elif predicted_return > -15:
            recommendation, reason = '减仓', '模型预测下跌5-15%'
        else:
            recommendation, reason = '卖出', '模型预测下跌超15%'
        
        return {
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'historical_6m': round(hist_return, 1),
            'predicted_6m': round(predicted_return, 1),
            'predicted_price': round(current_price * (1 + predicted_return/100), 2),
            'confidence': confidence,
            'methods': {
                '线性回归': round(lr_return, 1),
                '动量外推': round(mom_return, 1),
                '均值回归': round(mr_return, 1)
            },
            'recommendation': recommendation,
            'reason': reason
        }


async def main():
    """测试"""
    print("\n" + "="*70)
    print("🔮 股票未来6个月收益预测")
    print("="*70 + "\n")
    
    predictor = StockPredictor()
    symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META']
    
    results = []
    for symbol in symbols:
        print(f"[{symbol}] ", end="", flush=True)
        result = predictor.predict(symbol)
        
        if 'error' in result:
            print(f"❌ {result['error']}")
        else:
            print(f"当前:${result['current_price']} | 历史:{result['historical_6m']:+.1f}% → 预测:{result['predicted_6m']:+.1f}% | 🏷️{result['recommendation']}")
            results.append(result)
    
    print(f"\n{'='*70}")
    print("📊 汇总")
    print("="*70)
    
    # 买入推荐
    buy = [r for r in results if r.get('recommendation') == '买入']
    if buy:
        print(f"\n🟢 买入 ({len(buy)}): {', '.join([r['symbol'] for r in buy])}")
        for r in buy:
            print(f"   {r['symbol']}: ${r['current_price']} → ${r['predicted_price']} ({r['predicted_6m']:+.1f}%)")
    
    # 持有
    hold = [r for r in results if r.get('recommendation') == '持有']
    if hold:
        print(f"\n🟡 持有 ({len(hold)}): {', '.join([r['symbol'] for r in hold])}")
    
    # 卖出
    sell = [r for r in results if r.get('recommendation') in ['卖出', '减仓']]
    if sell:
        print(f"\n🔴 卖出/减仓 ({len(sell)}): {', '.join([r['symbol'] for r in sell])}")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
