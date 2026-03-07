"""
Stock Analysis Agent - 美股分析 + 未来收益预测
包含：历史分析 + 未来6个月收益预测
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import requests
import numpy as np
from scipy import stats
from scipy.optimize import minimize

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class StockPredictor:
    """股票收益预测器 - 预测未来6个月收益"""
    
    def __init__(self, session: requests.Session):
        self.session = session
        self.cache = {}
    
    def get_historical_data(self, symbol: str, period: str = "2y") -> Optional[List[Dict]]:
        """获取历史数据"""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {
                'range': period,  # 获取2年数据用于预测
                'interval': '1d',
            }
            
            resp = self.session.get(url, params=params, timeout=15)
            
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            result = data.get('chart', {}).get('result', [])
            
            if not result:
                return None
            
            meta = result[0].get('meta', {})
            timestamps = result[0].get('timestamp', [])
            quotes = result[0].get('indicators', {}).get('quote', [{}])[0]
            closes = quotes.get('close', [])
            volumes = quotes.get('volume', [])
            
            if not timestamps or not closes:
                return None
            
            history = []
            for i, (ts, close, vol) in enumerate(zip(timestamps, closes, volumes)):
                if close is None:
                    continue
                history.append({
                    'date': datetime.fromtimestamp(ts).strftime('%Y-%m-%d'),
                    'close': close,
                    'volume': vol if vol else 0,
                    'day': i  # 用于回归分析
                })
            
            return history
            
        except Exception as e:
            print(f"   ⚠️  获取 {symbol} 历史数据失败: {e}")
            return None
    
    def calculate_technical_indicators(self, closes: List[float]) -> Dict:
        """计算技术指标"""
        if len(closes) < 20:
            return {}
        
        closes = np.array(closes)
        
        # 移动平均线
        ma20 = np.mean(closes[-20:])
        ma50 = np.mean(closes[-50:]) if len(closes) >= 50 else ma20
        ma200 = np.mean(closes[-200:]) if len(closes) >= 200 else ma50
        
        # RSI (14日)
        delta = np.diff(closes)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = np.mean(gain[-14:]) if len(gain) >= 14 else np.mean(gain)
        avg_loss = np.mean(loss[-14:]) if len(loss) >= 14 else np.mean(loss)
        
        if avg_loss == 0:
            rsi = 70
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = np.average(closes[-12:], weights=np.linspace(0, 1, 12))
        ema26 = np.average(closes[-26:], weights=np.linspace(0, 1, 26))
        macd = ema12 - ema26
        signal = np.average([macd] + list(closes[-9:]), weights=np.linspace(0, 1, 10))
        histogram = macd - signal
        
        # 动量
        momentum_1m = (closes[-1] / closes[-20] - 1) * 100 if len(closes) >= 20 else 0
        momentum_3m = (closes[-1] / closes[-60] - 1) * 100 if len(closes) >= 60 else 0
        momentum_6m = (closes[-1] / closes[-120] - 1) * 100 if len(closes) >= 120 else 0
        
        # 波动率
        daily_returns = np.diff(closes) / closes[:-1]
        volatility = np.std(daily_returns) * np.sqrt(252) * 100
        
        return {
            'ma20': round(ma20, 2),
            'ma50': round(ma50, 2),
            'ma200': round(ma200, 2),
            'rsi': round(rsi, 1),
            'macd': round(macd, 2),
            'signal': round(signal, 2),
            'histogram': round(histogram, 2),
            'momentum_1m': round(momentum_1m, 1),
            'momentum_3m': round(momentum_3m, 1),
            'momentum_6m': round(momentum_6m, 1),
            'volatility': round(volatility, 1),
            'trend': 'up' if closes[-1] > ma50 else ('down' if closes[-1] < ma50 else 'sideways')
        }
    
    def predict_linear(self, closes: List[float], days: int = 126) -> Dict:
        """线性回归预测"""
        if len(closes) < 30:
            return {'predicted_return': 0, 'confidence': 'low'}
        
        x = np.arange(len(closes))
        y = np.array(closes)
        
        # 线性回归
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # 预测未来 days 天
        future_x = np.arange(len(closes), len(closes) + days)
        predicted_prices = intercept + slope * future_x
        
        current_price = closes[-1]
        predicted_price = predicted_prices[-1]
        predicted_return = ((predicted_price / current_price) - 1) * 100
        
        # R² 决定系数
        r_squared = r_value ** 2
        
        return {
            'method': '线性回归',
            'current_price': current_price,
            'predicted_price': round(predicted_price, 2),
            'predicted_return': round(predicted_return, 1),
            'confidence': 'high' if r_squared > 0.7 else ('medium' if r_squared > 0.4 else 'low'),
            'r_squared': round(r_squared, 3),
            'trend_slope': round(slope * 252, 4)  # 年化斜率
        }
    
    def predict_momentum(self, closes: List[float], days: int = 126) -> Dict:
        """动量外推预测 - 基于短期趋势"""
        if len(closes) < 60:
            return {'predicted_return': 0, 'confidence': 'low'}
        
        # 使用最近60天计算趋势
        recent = closes[-60:]
        x = np.arange(len(recent))
        y = np.array(recent)
        
        slope, intercept, r_value, _, _ = stats.linregress(x, y)
        
        current_price = closes[-1]
        # 假设趋势持续，但衰减
        decay_factor = 0.9  # 每月衰减
        
        # 简单动量预测
        daily_return = (recent[-1] / recent[0]) ** (1/60) - 1
        
        # 预测未来 (考虑均值回归)
        predicted_return_3m = daily_return * 63 * 0.7  # 3个月
        predicted_return_6m = daily_return * 126 * 0.5  # 6个月（衰减更多）
        
        return {
            'method': '动量外推',
            'current_price': current_price,
            'predicted_price': round(current_price * (1 + predicted_return_6m/100), 2),
            'predicted_return': round(predicted_return_6m, 1),
            'confidence': 'medium' if abs(daily_return) > 0.002 else 'low',
            'daily_return': round(daily_return * 100, 3),
            'trend': 'up' if slope > 0 else ('down' if slope < 0 else 'neutral')
        }
    
    def predict_mean_reversion(self, closes: List[float], days: int = 126) -> Dict:
        """均值回归预测"""
        if len(closes) < 120:
            return {'predicted_return': 0, 'confidence': 'low'}
        
        current_price = closes[-1]
        mean_price = np.mean(closes[-120:])
        std_price = np.std(closes[-120:])
        
        # Z-score
        z_score = (current_price - mean_price) / std_price if std_price > 0 else 0
        
        # 如果价格高于均值，预测回归；反之亦然
        if abs(z_score) < 0.5:
            # 在均值附近，预测小幅上涨
            predicted_return = 3.0
            confidence = 'medium'
        elif z_score > 1:
            # 高于均值，预测回归
            predicted_return = -z_score * 3
            confidence = 'high'
        elif z_score < -1:
            # 低于均值，预测回归
            predicted_return = abs(z_score) * 3
            confidence = 'high'
        else:
            predicted_return = z_score * 2
            confidence = 'medium'
        
        return {
            'method': '均值回归',
            'current_price': current_price,
            'mean_price': round(mean_price, 2),
            'z_score': round(z_score, 2),
            'predicted_price': round(current_price * (1 + predicted_return/100), 2),
            'predicted_return': round(predicted_return, 1),
            'confidence': confidence
        }
    
    def predict_ensemble(self, symbol: str, closes: List[float]) -> Dict:
        """集成预测 - 综合多种方法"""
        
        methods = [
            self.predict_linear(closes),
            self.predict_momentum(closes),
            self.predict_mean_reversion(closes)
        ]
        
        # 过滤有效预测
        valid_predictions = [m for m in methods if 'predicted_return' in m]
        
        if not valid_predictions:
            return {
                'symbol': symbol,
                'error': '无法生成预测'
            }
        
        # 加权平均 (根据置信度)
        weights = []
        for m in valid_predictions:
            conf = m.get('confidence', 'low')
            weight = 1.0 if conf == 'high' else (0.7 if conf == 'medium' else 0.4)
            weights.append(weight)
        
        weights = np.array(weights)
        weights = weights / weights.sum()
        
        returns = np.array([m['predicted_return'] for m in valid_predictions])
        predicted_return = float(np.average(returns, weights=weights))
        
        # 计算预测区间
        std_return = np.std(returns)
        upper_bound = predicted_return + std_return * 1.5
        lower_bound = predicted_return - std_return * 1.5
        
        # 综合置信度
        avg_confidence = np.average([1.0 if m.get('confidence') == 'high' else 
                                      (0.7 if m.get('confidence') == 'medium' else 0.4) 
                                      for m in valid_predictions])
        
        # 给出建议
        if predicted_return > 15:
            recommendation = "买入"
            reason = "多模型预测上涨超15%"
        elif predicted_return > 5:
            recommendation = "持有"
            reason = "模型倾向小幅上涨"
        elif predicted_return > -5:
            recommendation = "观望"
            reason = "模型预测区间震荡"
        elif predicted_return > -15:
            recommendation = "减仓"
            reason = "模型预测下跌5-15%"
        else:
            recommendation = "卖出"
            reason = "模型预测下跌超15%"
        
        current_price = closes[-1]
        
        return {
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'predicted_return': round(predicted_return, 1),
            'predicted_price': round(current_price * (1 + predicted_return/100), 2),
            'upper_bound': round(upper_bound, 1),
            'lower_bound': round(lower_bound, 1),
            'confidence': 'high' if avg_confidence > 0.7 else ('medium' if avg_confidence > 0.4 else 'low'),
            'method_details': {
                m['method']: {
                    'return': m.get('predicted_return', 'N/A'),
                    'confidence': m.get('confidence', 'N/A')
                } for m in valid_predictions
            },
            'recommendation': recommendation,
            'reason': reason
        }
    
    def analyze_stock(self, symbol: str) -> Dict:
        """完整分析 + 预测"""
        
        # 获取历史数据
        history = self.get_historical_data(symbol)
        
        if not history:
            return {'symbol': symbol, 'error': '无法获取数据'}
        
        closes = [h['close'] for h in history]
        volumes = [h['volume'] for h in history]
        
        current_price = closes[-1]
        start_price = closes[-126] if len(closes) >= 126 else closes[0]
        historical_return = ((current_price / start_price) - 1) * 100
        
        # 计算技术指标
        tech_indicators = self.calculate_technical_indicators(closes)
        
        # 生成预测
        prediction = self.predict_ensemble(symbol, closes)
        
        # 整合结果
        result = {
            'symbol': symbol,
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'current_price': current_price,
            'historical_6m': round(historical_return, 1),
            'prediction': prediction,
            'technical': tech_indicators,
            'trading_days': len(closes),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        
        return result


def format_prediction_result(result: Dict) -> str:
    """格式化预测结果"""
    
    if 'error' in result:
        return f"❌ {result['symbol']}: {result['error']}"
    
    pred = result['prediction']
    
    result_str = f"""
{result['symbol']} 分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 当前价格: ${result['current_price']}

📈 历史表现 (过去6个月): 
   {result['historical_6m']:+.1f}%

🔮 未来6个月预测:
   预测收益: {pred['predicted_return']:+.1f}%
   预测价格: ${pred['predicted_price']}
   置信度: {pred['confidence']}
   
   预测区间: {pred['lower_bound']:.0f}% ~ {pred['upper_bound']:.0f}%
   
   🏷️ 建议: {pred['recommendation']}
   📝 理由: {pred['reason']}

📊 各模型预测:
"""
    # 添加各模型细节
    details = pred.get('method_details', {})
    for method, info in details.items():
        emoji = "📈" if info.get('return', 0) > 0 else "📉"
        result_str += f"   {emoji} {method}: {info.get('return', 'N/A'):+.1f}% (置信: {info.get('confidence')})\n"
    
    # 添加技术指标
    tech = result.get('technical', {})
    if tech:
        result_str += f"""
📱 技术指标:
   RSI: {tech.get('rsi', 'N/A')} ({'超买' if tech.get('rsi', 0) > 70 else ('超卖' if tech.get('rsi', 0) < 30 else '正常')})
   MA20: ${tech.get('ma20', 'N/A')} | MA50: ${tech.get('ma50', 'N/A')}
   趋势: {tech.get('trend', 'N/A').upper()}
   波动率: {tech.get('volatility', 'N/A')}%
"""
    
    return result_str


# ==================== 测试 ====================

async def test_prediction():
    """测试预测功能"""
    
    print("\n" + "="*70)
    print("🔮 股票收益预测测试")
    print("="*70 + "\n")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    predictor = StockPredictor(session)
    
    test_symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META']
    
    for symbol in test_symbols:
        print(f"[{symbol}]")
        result = predictor.analyze_stock(symbol)
        
        if 'error' in result:
            print(f"   ❌ {result['error']}")
        else:
            pred = result['prediction']
            print(f"   当前: ${result['current_price']}")
            print(f"   历史6M: {result['historical_6m']:+.1f}%")
            print(f"   预测6M: {pred['predicted_return']:+.1f}% | 置信: {pred['confidence']}")
            print(f"   建议: {pred['recommendation']}")
        print()
    
    print("="*70)
    print("✅ 测试完成\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_prediction())
