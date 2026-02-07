"""
Stock Analysis Agent - 增强版
包含：多因子分析 + WorldQuant Alpha101因子 + 基本面数据 + LLM深度预测
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import requests
import numpy as np
import hmac
import hashlib
import base64
import urllib.parse
from scipy import stats

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompts.stock_prompts import get_prediction_prompt
from core.llm_client import LLMClient


def percent_encode(s):
    """URL编码"""
    return urllib.parse.quote(s, safe='-_.~').replace('%7E', '~')


def signature(method, path, params, access_secret):
    """计算签名"""
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    canonicalized_query_string = '&'.join([
        f'{percent_encode(k)}={percent_encode(v)}'
        for k, v in sorted_params
    ])
    string_to_sign = f'{method}&%2F&{percent_encode(canonicalized_query_string)}'
    sig = hmac.new(
        (access_secret + '&').encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha1
    ).digest()
    return base64.b64encode(sig).decode('utf-8')


# 股票行业分类
# 候选股票列表
CANDIDATE_STOCKS = [
    "GOOGL", "TSLA", "MSFT", "AAPL", "NVDA", "NFLX", "BABA",
    "TCEHY", "LKNCY", "ASML", "PLTR", "XPEV", "LI", "NIO", "BYDDY",
    "CVNA", "HTHT", "JD", "BILI", "PDD"
]

# 股票基本面数据
SECTOR_MAP = {
    # 科技巨头
    'AAPL': {'sector': 'Technology', 'industry': 'Consumer Electronics', 'pe': 28.5, 'growth_rate': 8.2},
    'MSFT': {'sector': 'Technology', 'industry': 'Software', 'pe': 35.2, 'growth_rate': 12.5},
    'NVDA': {'sector': 'Technology', 'industry': 'Semiconductors', 'pe': 65.8, 'growth_rate': 45.2},
    'GOOGL': {'sector': 'Technology', 'industry': 'Internet Services', 'pe': 25.3, 'growth_rate': 15.8},
    'AMZN': {'sector': 'Consumer Discretionary', 'industry': 'E-Commerce', 'pe': 78.5, 'growth_rate': 18.5},
    'META': {'sector': 'Technology', 'industry': 'Social Media', 'pe': 28.9, 'growth_rate': 16.2},
    'TSLA': {'sector': 'Consumer Discretionary', 'industry': 'Electric Vehicles', 'pe': 65.2, 'growth_rate': 22.5},
    
    # 中概股
    'BABA': {'sector': 'Technology', 'industry': 'E-Commerce (China)', 'pe': 18.5, 'growth_rate': 12.5},
    'TCEHY': {'sector': 'Technology', 'industry': 'Gaming (China)', 'pe': 22.5, 'growth_rate': 15.2},
    'JD': {'sector': 'Consumer Discretionary', 'industry': 'E-Commerce (China)', 'pe': 35.2, 'growth_rate': 8.5},
    'PDD': {'sector': 'Consumer Discretionary', 'industry': 'E-Commerce (China)', 'pe': 28.5, 'growth_rate': 18.5},
    'BILI': {'sector': 'Technology', 'industry': 'Streaming (China)', 'pe': 25.3, 'growth_rate': 12.8},
    'NIO': {'sector': 'Consumer Discretionary', 'industry': 'EV (China)', 'pe': None, 'growth_rate': 25.5},
    'XPEV': {'sector': 'Consumer Discretionary', 'industry': 'EV (China)', 'pe': None, 'growth_rate': 22.5},
    'LI': {'sector': 'Consumer Discretionary', 'industry': 'EV (China)', 'pe': None, 'growth_rate': 20.5},
    'BYDDY': {'sector': 'Consumer Discretionary', 'industry': 'EV (China)', 'pe': None, 'growth_rate': 18.5},
    
    # 其他
    'NFLX': {'sector': 'Communication Services', 'industry': 'Streaming', 'pe': 42.5, 'growth_rate': 16.5},
    'ASML': {'sector': 'Technology', 'industry': 'Semiconductor Equipment', 'pe': 55.5, 'growth_rate': 28.5},
    'PLTR': {'sector': 'Technology', 'industry': 'AI/Software', 'pe': 85.5, 'growth_rate': 35.5},
    'LKNCY': {'sector': 'Consumer Discretionary', 'industry': 'Food Delivery (China)', 'pe': None, 'growth_rate': 15.5},
    'CVNA': {'sector': 'Consumer Discretionary', 'industry': 'Auto Retail', 'pe': 45.5, 'growth_rate': 18.5},
    'HTHT': {'sector': 'Consumer Discretionary', 'industry': 'Travel', 'pe': 22.5, 'growth_rate': 12.5},
}

# 估值参考
SECTOR_AVERAGE_PE = {
    'Technology': 28.5,
    'Consumer Discretionary': 22.5,
    'Financials': 12.5,
    'Healthcare': 18.5,
    'Energy': 14.5,
    'Consumer Staples': 20.5,
    'Communication Services': 20.5,
}


# ============ WorldQuant Alpha101 因子计算 ============

def calculate_worldquant_alphas(closes: np.ndarray, highs: np.ndarray, 
                                  lows: np.ndarray, volumes: np.ndarray) -> Dict[str, float]:
    """
    计算 WorldQuant Alpha101 部分因子
    基于论文: https://arxiv.org/pdf/1601.00991
    """
    alphas = {}
    n = len(closes)
    
    if n < 60:
        return alphas
    
    try:
        # Alpha001: (close - open) / open
        if len(closes) >= 2:
            daily_returns = np.diff(closes) / closes[:-1]
            alphas['alpha001'] = np.mean(daily_returns) * 100
        
        # Alpha006: -1 * correlation(rank(open), rank(volume), 10)
        if n >= 10:
            opens = closes[:-1] - daily_returns * closes[:-1]
            rank_open = stats.rankdata(opens[-10:])
            rank_vol = stats.rankdata(volumes[-10:].astype(float))
            if np.std(rank_open) > 0 and np.std(rank_vol) > 0:
                corr = np.corrcoef(rank_open, rank_vol)[0, 1]
                alphas['alpha006'] = -1 * corr
        
        # Alpha010: rank(volume) / (rank(volume) + rank(open))
        if n >= 10:
            rank_vol = stats.rankdata(volumes[-10:].astype(float))
            rank_open = stats.rankdata(opens[-10:] if 'opens' in dir() else closes[-11:-1])
            if (rank_vol + rank_open).sum() > 0:
                alphas['alpha010'] = np.mean(rank_vol / (rank_vol + rank_open))
        
        # Alpha028: (close - close(26d ago)) / close(26d ago) * volume
        if n >= 27:
            ret_26d = (closes[-1] - closes[-27]) / (closes[-27] + 0.001)
            alphas['alpha028'] = ret_26d * np.mean(volumes[-10:])
        
        # Alpha041: (high - low) / (high(5) + low(5))
        if n >= 10:
            high_5 = highs[-10:-5].max() if len(highs) >= 15 else highs[-5:].max()
            low_5 = lows[-10:-5].min() if len(lows) >= 15 else lows[-5:].min()
            if (high_5 + low_5) > 0:
                alphas['alpha041'] = (highs[-1] - lows[-1]) / (high_5 + low_5)
        
        # Alpha054: -1 * correlation(rank(high), rank(volume), 5)
        if n >= 5:
            rank_high = stats.rankdata(highs[-5:].astype(float))
            rank_vol = stats.rankdata(volumes[-5:].astype(float))
            if np.std(rank_high) > 0 and np.std(rank_vol) > 0:
                corr = np.corrcoef(rank_high, rank_vol)[0, 1]
                alphas['alpha054'] = -1 * corr
        
        # Alpha060: (close - close(6)) / close(6) * 100
        if n >= 7:
            ret_6d = (closes[-1] - closes[-7]) / (closes[-7] + 0.001) * 100
            alphas['alpha060'] = ret_6d
        
        # Alpha065: (close - min(low, 9)) / (max(high, 9) - min(low, 9))
        if n >= 10:
            min_low = np.min(lows[-10:])
            max_high = np.max(highs[-10:])
            if max_high - min_low > 0:
                alphas['alpha065'] = (closes[-1] - min_low) / (max_high - min_low)
        
        # Alpha076: (close - close(3)) / close(3) * volume
        if n >= 4:
            ret_3d = (closes[-1] - closes[-4]) / (closes[-4] + 0.001)
            alphas['alpha076'] = ret_3d * np.mean(volumes[-10:])
        
        # Alpha100: -1 * correlation(rank(high), rank(close), 5)
        if n >= 5:
            rank_high = stats.rankdata(highs[-5:].astype(float))
            rank_close = stats.rankdata(closes[-5:].astype(float))
            if np.std(rank_high) > 0 and np.std(rank_close) > 0:
                corr = np.corrcoef(rank_high, rank_close)[0, 1]
                alphas['alpha100'] = -1 * corr
        
        # Alpha007: (open - close(1)) / close(1) * 100
        if len(closes) >= 2:
            oa_ret = (closes[-1] - closes[-2]) / (closes[-2] + 0.001) * 100
            alphas['alpha007'] = oa_ret
        
        # Alpha101: 动量因子 - 3M收益 / 波动率
        if n >= 63 and np.std(closes[-63:]) > 0:
            mom_3m = (closes[-1] - closes[-63]) / closes[-63] * 100
            vol = np.std(np.diff(closes[-63:])) * np.sqrt(252) * 100
            alphas['alpha101'] = mom_3m / (vol + 1)
        
        # Alpha008: (close - close(5)) / close(5) * 100
        if n >= 6:
            ret_5d = (closes[-1] - closes[-6]) / (closes[-6] + 0.001) * 100
            alphas['alpha008'] = ret_5d
        
        # Alpha012: 量价相关性
        if n >= 10:
            ret_10d = (closes[-1] - closes[-10]) / (closes[-10] + 0.001)
            vol_change = (np.mean(volumes[-5:]) / (np.mean(volumes[-10:-5]) + 1) - 1)
            if np.std(ret_10d) > 0 and np.std(vol_change) > 0:
                corr = np.corrcoef(ret_10d, vol_change)[0, 1]
                alphas['alpha012'] = corr
        
        # Alpha015: 价格位置因子
        if n >= 20:
            high_20 = np.max(closes[-20:])
            low_20 = np.min(closes[-20:])
            if high_20 - low_20 > 0:
                alphas['alpha015'] = (closes[-1] - low_20) / (high_20 - low_20)
        
        # Alpha030: RSI改进版
        if n >= 14:
            delta = np.diff(closes)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            avg_gain = np.mean(gain[-14:])
            avg_loss = np.mean(loss[-14:])
            rs = avg_gain / (avg_loss + 0.001)
            alphas['alpha030'] = 100 - (100 / (1 + rs))
        
    except Exception as e:
        pass
    
    return alphas


def calculate_enhanced_alphas(closes: np.ndarray, highs: np.ndarray, 
                              lows: np.ndarray, volumes: np.ndarray) -> Dict[str, float]:
    """计算增强版Alpha因子"""
    
    n = len(closes)
    alphas = {}
    
    if n < 60:
        return alphas
    
    try:
        returns = np.diff(closes) / closes[:-1]
        
        # 1. 收益率因子
        for period in [5, 10, 20, 60]:
            if n > period:
                ret = (closes[-1] - closes[-period-1]) / (closes[-period-1] + 0.001)
                alphas[f'return_{period}d'] = ret * 100
        
        # 2. 波动率因子
        alphas['volatility_20d'] = np.std(returns[-20:]) * np.sqrt(252) * 100
        alphas['volatility_60d'] = np.std(returns[-60:]) * np.sqrt(252) * 100
        alphas['volatility_ratio'] = alphas['volatility_20d'] / (alphas['volatility_60d'] + 0.001)
        
        # 3. 偏度和峰度
        if len(returns) >= 20:
            alphas['skewness'] = float(stats.skew(returns[-20:]))
            alphas['kurtosis'] = float(stats.kurtosis(returns[-20:]))
        
        # 4. 量价因子
        avg_vol_20 = np.mean(volumes[-20:])
        vol_change = (volumes[-1] - avg_vol_20) / (avg_vol_20 + 0.001)
        alphas['volume_change'] = vol_change * 100
        
        if len(returns) >= 10 and len(volumes) >= 10:
            corr = np.corrcoef(returns[-10:], volumes[-10:].astype(float)[:len(returns[-10:])])[0, 1]
            alphas['volume_price_corr'] = corr if not np.isnan(corr) else 0
        
        # 5. 趋势因子
        ma5 = np.mean(closes[-5:])
        ma20 = np.mean(closes[-20:])
        ma60 = np.mean(closes[-60:])
        
        alphas['ma5_ma20_ratio'] = ma5 / (ma20 + 0.001)
        alphas['ma20_ma60_ratio'] = ma20 / (ma60 + 0.001)
        alphas['price_ma20_ratio'] = closes[-1] / (ma20 + 0.001)
        alphas['price_ma60_ratio'] = closes[-1] / (ma60 + 0.001)
        
        # 6. 威廉指标
        williams_r = -100 * (np.max(highs[-14:]) - closes[-1]) / (np.max(highs[-14:]) - np.min(lows[-14:]) + 0.001)
        alphas['williams_r'] = williams_r
        
        # 7. RSI
        delta = np.diff(closes)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = np.mean(gain[-14:])
        avg_loss = np.mean(loss[-14:])
        rs = avg_gain / (avg_loss + 0.001)
        alphas['rsi'] = 100 - (100 / (1 + rs))
        
        # 8. MACD
        ema12 = np.convolve(closes, np.ones(12)/12, mode='valid')[-1]
        ema26 = np.convolve(closes, np.ones(26)/26, mode='valid')[-1]
        alphas['macd'] = (ema12 - ema26) / (ema26 + 0.001) * 100
        
        # 9. 布林带位置
        ma20_val = ma20
        bb_std = np.std(closes[-20:])
        alphas['bb_position'] = (closes[-1] - (ma20_val - 2*bb_std)) / (4*bb_std + 0.001)
        
        # 10. ATR
        tr1 = highs[-1] - lows[-1]
        tr2 = np.abs(highs[-1] - closes[-2])
        tr3 = np.abs(lows[-1] - closes[-2])
        true_range = np.max([tr1, tr2, tr3])
        atr = np.mean([true_range] + list(np.abs(np.diff(closes[-15:]))))
        alphas['atr'] = atr / (closes[-1] + 0.001) * 100
        
        # 11. 价格动量
        roc_5 = (closes[-1] - closes[-6]) / (closes[-6] + 0.001) * 100
        roc_10 = (closes[-1] - closes[-11]) / (closes[-11] + 0.001) * 100
        roc_20 = (closes[-1] - closes[-21]) / (closes[-21] + 0.001) * 100
        alphas['roc_5'] = roc_5
        alphas['roc_10'] = roc_10
        alphas['roc_20'] = roc_20
        alphas['momentum_acceleration'] = roc_5 - roc_10
        
        # 12. 52周位置
        high_252 = np.max(closes[-252:]) if n >= 252 else np.max(closes)
        low_252 = np.min(closes[-252:]) if n >= 252 else np.min(closes)
        alphas['high_252_ratio'] = (high_252 - closes[-1]) / (high_252 - low_252 + 0.001)
        alphas['low_252_ratio'] = (closes[-1] - low_252) / (high_252 - low_252 + 0.001)
        
        # 13. 综合评分
        alpha_score = 0
        if alphas.get('roc_20', 0) > 10:
            alpha_score += 1
        elif alphas.get('roc_20', 0) < -10:
            alpha_score -= 1
        if alphas.get('ma5_ma20_ratio', 1) > 1:
            alpha_score += 1
        if alphas.get('ma20_ma60_ratio', 1) > 1:
            alpha_score += 1
        if 40 < alphas.get('rsi', 50) < 70:
            alpha_score += 0.5
        alphas['alpha_composite_score'] = alpha_score
        
    except Exception as e:
        pass
    
    return alphas



class StockAnalysisAgent:
    """美股分析 Agent - 多因子增强版"""
    
    def __init__(self, hold_period: str = "6mo"):
        self.hold_period = hold_period
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_stock_data(self, symbol: str) -> Optional[Dict]:
        """获取股票数据 - 增强版"""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {'range': '3y', 'interval': '1d'}
            
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            result = data.get('chart', {}).get('result', [])
            if not result:
                return None
            
            timestamps = result[0].get('timestamp', [])
            closes = result[0].get('indicators', {}).get('quote', [{}])[0].get('close', [])
            
            if not timestamps or not closes:
                return None
            
            valid_data = [(ts, c) for ts, c in zip(timestamps, closes) if c is not None]
            if len(valid_data) < 60:
                return None
            
            closes = np.array([c for _, c in valid_data])
            timestamps = [ts for ts, _ in valid_data]
            
            current_price = closes[-1]
            
            # ============ 基础收益数据 ============
            returns = {}
            for period, days in [('1w', 5), ('1m', 21), ('3m', 63), ('6m', 126), ('1y', 252)]:
                if len(closes) >= days:
                    ret = ((closes[-1] / closes[-days]) - 1) * 100
                    returns[period] = round(ret, 2)
            
            # ============ 多因子计算 ============
            
            # 1. 动量因子 (Momentum)
            mom_1m = returns.get('1m', 0)
            mom_3m = returns.get('3m', 0)
            mom_6m = returns.get('6m', 0)
            mom_1y = returns.get('1y', 0)
            
            # 动量强度: 短期vs长期
            mom_strength = mom_1m - mom_3m  # 正=加速, 负=减速
            
            # 2. 波动率因子 (Volatility)
            daily_returns = np.diff(closes) / closes[:-1]
            volatility_daily = np.std(daily_returns)
            volatility_annual = volatility_daily * np.sqrt(252) * 100
            
            # 波动率趋势 (近1月vs近3月)
            vol_1m = np.std(daily_returns[-21:]) * np.sqrt(252) * 100 if len(daily_returns) >= 21 else volatility_annual
            vol_trend = "收缩" if vol_1m < volatility_annual * 0.9 else ("扩张" if vol_1m > volatility_annual * 1.1 else "稳定")
            
            # 3. 趋势因子 (Trend)
            ma5 = np.mean(closes[-5:])
            ma20 = np.mean(closes[-20:])
            ma50 = np.mean(closes[-50:])
            ma200 = np.mean(closes[-200:]) if len(closes) >= 200 else ma50
            
            # 均线排列
            if ma5 > ma20 > ma50 > ma200:
                trend_signal = "多头排列"
            elif ma5 < ma20 < ma50 < ma200:
                trend_signal = "空头排列"
            elif ma20 > ma50:
                trend_signal = "上升趋势"
            elif ma20 < ma50:
                trend_signal = "下降趋势"
            else:
                trend_signal = "震荡整理"
            
            # 价格相对均线位置
            ma20_pos = (current_price - ma20) / ma20 * 100
            ma50_pos = (current_price - ma50) / ma50 * 100
            ma200_pos = (current_price - ma200) / ma200 * 100 if ma200 != current_price else 0
            
            # 4. 动量因子增强
            # 威廉指标
            williams_r = -100 * (np.max(closes[-14:]) - closes[-1]) / (np.max(closes[-14:]) - np.min(closes[-14:]) + 0.001)
            
            # RSI
            delta = np.diff(closes)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            avg_gain = np.mean(gain[-14:])
            avg_loss = np.mean(loss[-14:])
            rsi = 50 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
            
            # ROC (Rate of Change)
            roc_10 = ((closes[-1] - closes[-10]) / closes[-10] * 100) if len(closes) >= 10 else 0
            roc_20 = ((closes[-1] - closes[-20]) / closes[-20] * 100) if len(closes) >= 20 else 0
            
            # 5. 成交量因子
            volumes = result[0].get('indicators', {}).get('quote', [{}])[0].get('volume', [])
            volumes = [v for v in volumes[-63:] if v is not None] if volumes else []
            if volumes:
                avg_vol = np.mean(volumes)
                recent_vol = np.mean(volumes[-5:])
                vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1
            else:
                vol_ratio = 1
            
            # 6. 支撑/阻力
            high_52w = np.max(closes[-252:]) if len(closes) >= 252 else np.max(closes)
            low_52w = np.min(closes[-252:]) if len(closes) >= 252 else np.min(closes)
            
            # ============ 基本面数据 ============
            fund = SECTOR_MAP.get(symbol, {'sector': 'Unknown', 'industry': 'Unknown', 'pe': 20, 'growth_rate': 10})
            
            # 相对PE (处理pe=None的情况)
            pe_val = fund.get('pe', 20) or 20
            sector_pe = SECTOR_AVERAGE_PE.get(fund['sector'], 20)
            pe_ratio = pe_val / sector_pe if pe_val else 1.0  # >1=高估, <1=低估
            
            # 估值位置
            pe_percentile = (current_price - low_52w) / (high_52w - low_52w + 0.001) * 100
            
            # ============ 综合评分 ============
            score = 0
            factors = []
            
            # 趋势评分
            if trend_signal == "多头排列":
                score += 3
                factors.append("✓ 多头排列")
            elif trend_signal == "空头排列":
                score -= 3
                factors.append("✗ 空头排列")
            elif trend_signal == "上升趋势":
                score += 1
                factors.append("✓ 上升趋势")
            elif trend_signal == "下降趋势":
                score -= 1
                factors.append("✗ 下降趋势")
            
            # 动量评分
            if mom_strength > 3:
                score += 2
                factors.append("✓ 动量加速")
            elif mom_strength < -5:
                score -= 2
                factors.append("✗ 动量减速")
            
            # RSI评分
            if rsi > 70:
                score -= 1
                factors.append("⚠ RSI超买")
            elif rsi < 30:
                score += 1
                factors.append("✓ RSI超卖")
            
            # 波动率评分
            if volatility_annual > 45:
                score -= 1
                factors.append("⚠ 高波动")
            elif volatility_annual < 20:
                score += 1
                factors.append("✓ 低波动")
            
            # 估值评分
            if pe_ratio < 0.8:
                score += 2
                factors.append("✓ 估值偏低")
            elif pe_ratio > 1.3:
                score -= 2
                factors.append("⚠ 估值偏高")
            
            # 趋势判断
            recent_20 = closes[-20:]
            earlier_20 = closes[-40:-20] if len(closes) >= 40 else closes[:20]
            trend = "上升" if np.mean(recent_20) > np.mean(earlier_20) else ("下降" if np.mean(recent_20) < np.mean(earlier_20) else "震荡")
            
            return {
                'symbol': symbol,
                
                # 基础数据
                'current_price': round(current_price, 2),
                'returns': returns,
                'data_points': len(closes),
                'period': f"{datetime.fromtimestamp(timestamps[0]).strftime('%Y-%m-%d')} ~ {datetime.fromtimestamp(timestamps[-1]).strftime('%Y-%m-%d')}",
                
                # 多因子
                'momentum': {
                    '1m': mom_1m,
                    '3m': mom_3m,
                    '6m': mom_6m,
                    '1y': mom_1y,
                    'strength': round(mom_strength, 2),  # 动量强度
                },
                'volatility': {
                    'annual': round(volatility_annual, 2),
                    'trend': vol_trend,
                    'daily': round(volatility_daily * 100, 3),
                },
                'trend': {
                    'signal': trend_signal,
                    'direction': trend,
                    'ma20_pos': round(ma20_pos, 2),
                    'ma50_pos': round(ma50_pos, 2),
                    'ma200_pos': round(ma200_pos, 2),
                },
                'technical': {
                    'rsi': round(rsi, 1),
                    'williams_r': round(williams_r, 1),
                    'roc_10': round(roc_10, 2),
                    'roc_20': round(roc_20, 2),
                    'ma20': round(ma20, 2),
                    'ma50': round(ma50, 2),
                    'ma200': round(ma200, 2),
                },
                'volume': {
                    'ratio': round(vol_ratio, 2),
                    'trend': "放量" if vol_ratio > 1.2 else ("缩量" if vol_ratio < 0.8 else "正常"),
                },
                'valuation': {
                    'sector': fund['sector'],
                    'industry': fund['industry'],
                    'pe': fund['pe'],
                    'pe_ratio': round(pe_ratio, 2),
                    'pe_percentile': round(pe_percentile, 1),  # 价格在52w区间的位置
                    'growth_rate': fund['growth_rate'],
                    'high_52w': round(high_52w, 2),
                    'low_52w': round(low_52w, 2),
                },
                'composite_score': score,
                'key_factors': factors,
                
                # WorldQuant Alpha101 因子
                'worldquant_alphas': calculate_worldquant_alphas(closes, highs, lows, volumes),
                
                # 增强版因子
                'enhanced_alphas': calculate_enhanced_alphas(closes, highs, lows, volumes),
            }
            
        except Exception as e:
            print(f"   ⚠️  获取 {symbol} 数据失败: {e}")
            return None
    
    async def analyze_single_stock(self, symbol: str, llm_client: LLMClient) -> Dict:
        """分析单只股票"""
        
        stock_data = self.get_stock_data(symbol)
        if not stock_data:
            return {'symbol': symbol, 'error': '数据获取失败'}
        
        prompt = self._get_enhanced_prompt(symbol, stock_data)
        messages = [{"role": "user", "content": prompt}]
        
        result = await llm_client.call(messages, temperature=0.3, max_tokens=3000)
        
        if result["success"]:
            content = result["content"]
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                prediction = json.loads(content)
            except:
                prediction = {"error": "LLM响应解析失败", "raw": content[:1000]}
        else:
            prediction = {"error": result.get("error", "LLM调用失败")}
        
        return {
            'symbol': symbol,
            'stock_data': stock_data,
            'prediction': prediction,
        }
    
    def _get_enhanced_prompt(self, symbol: str, data: Dict) -> str:
        """生成增强版 Prompt"""
        
        m = data['momentum']
        v = data['volatility']
        t = data['trend']
        tech = data['technical']
        val = data['valuation']
        ret = data['returns']
        
        prompt = f"""作为一位资深量化投资分析师，请对 {symbol} 进行多维度深度分析，预测其未来6个月收益表现。

## 核心数据概览

**价格信息:**
- 当前价格: ${data['current_price']}
- 52周区间: ${val['low_52w']} - ${val['high_52w']}
- 当前在52周位置: {val['pe_percentile']:.1f}%

**历史收益:**
- 1周: {ret.get('1w', 'N/A'):+.1f}%
- 1个月: {ret.get('1m', 0):+.1f}%
- 3个月: {ret.get('3m', 0):+.1f}%
- 6个月: {ret.get('6m', 'N/A'):+.1f}%
- 1年: {ret.get('1y', 'N/A'):+.1f}%

## 多因子分析

### 1. 动量因子 (Momentum)
- 近1月收益: {m['1m']:+.1f}%
- 近3月收益: {m['3m']:+.1f}%
- 近6月收益: {m['6m']:+.1f}%
- 动量强度: {m['strength']:+.1f}%"""

        prompt += f"""
- 解读: {'短期动能强劲' if m['1m'] > 10 else ('短期动能疲弱' if m['1m'] < -10 else '短期动能中性')}

### 2. 波动率因子 (Volatility)
- 年化波动率: {v['annual']:.1f}%
- 波动率趋势: {v['trend']}
- 解读: {'高波动风险' if v['annual'] > 40 else ('低波动稳健' if v['annual'] < 25 else '波动率适中')}

### 3. 趋势因子 (Trend)
- 均线系统: {t['signal']}
- MA20位置: {t['ma20_pos']:+.1f}%
- MA50位置: {t['ma50_pos']:+.1f}%
- MA200位置: {t['ma200_pos']:+.1f}%
- 技术趋势: {t['direction']}

### 4. 技术指标
- RSI(14): {tech['rsi']:.1f} ({'超买' if tech['rsi'] > 70 else ('超卖' if tech['rsi'] < 30 else '中性')})
- MA20: ${tech['ma20']:.2f} | MA50: ${tech['ma50']:.2f}

### 5. 估值因子 (Valuation)
- 行业: {val['sector']} / {val['industry']}
- PE: {val['pe']} (行业均值: {SECTOR_AVERAGE_PE.get(val['sector'], 20)})
- 相对PE: {val['pe_ratio']:.2f}x ({'高估' if val['pe_ratio'] > 1.2 else ('低估' if val['pe_ratio'] < 0.9 else '合理')})
- 预期增长率: {val['growth_rate']:.1f}%

## 分析任务

请基于以上因子数据进行深度分析：

1. 动量解读：短期vs中期动量是否一致？
2. 趋势确认：均线支撑/阻力位在哪里？
3. 估值定位：相对行业是否高估/低估？
4. 风险评估：主要下行风险是什么？

## 输出要求

请返回JSON格式：

```json
{{
    "predicted_return": 8.5,
    "confidence": "high",
    "risk_level": "medium",
    "recommendation": "买入",
    "momentum_analysis": "动量持续性分析...",
    "trend_analysis": "趋势强度判断...",
    "valuation_analysis": "估值合理性分析...",
    "upside_factors": ["利好因素1", "利好因素2"],
    "downside_factors": ["利空因素1", "利空因素2"],
    "support_levels": [180, 175],
    "resistance_levels": [200, 210],
    "target_price_6m": 195,
    "specific_insight": "针对{symbol}的独特分析"
}}
```

**关键要求:**
- 必须基于{symbol}的具体数据，不能套用模板
- 给出具体数值预测，不是模糊结论
- 与其他股票的分析有明显区别

请直接返回JSON。"""
        
        return prompt
    
    async def analyze_stocks(self, symbols: List[str]) -> List[Dict]:
        """批量分析股票"""
        print(f"\n{'='*70}")
        print(f"📈 开始多因子分析 {len(symbols)} 只股票")
        print(f"{'='*70}\n")
        
        llm = LLMClient()
        results = []
        
        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] 分析 {symbol}...")
            result = await self.analyze_single_stock(symbol, llm)
            results.append(result)
            
            if 'stock_data' in result:
                data = result['stock_data']
                pred = result.get('prediction', {})
                score = data.get('composite_score', 0)
                pe_ratio = data.get('valuation', {}).get('pe_ratio', 1)
                
                if 'predicted_return' in pred:
                    print(f"   ✅ ${data['current_price']} | 综合:{score:+d} | PE:{pe_ratio:.1f}x | 预测:{pred['predicted_return']:+.1f}% | {pred.get('recommendation', 'N/A')}")
                    print(f"   📊 因子: {', '.join(data.get('key_factors', [])[:3])}")
                else:
                    print(f"   ⚠️ 预测失败")
            else:
                print(f"   ❌ 数据失败")
            
            await asyncio.sleep(0.5)
        
        await llm.close()
        return results
    
    def _normalize_recommendation(self, rec: str) -> str:
        """标准化 recommendation 为中文"""
        if not rec:
            return '观望'
        rec = rec.lower().strip()
        # 买入
        if rec in ['买入', 'buy', 'buying', 'long', 'add']:
            return '买入'
        # 持有
        if rec in ['持有', 'hold', 'holding', 'watch', '观望']:
            return '持有'
        # 卖出
        if rec in ['卖出', 'sell', 'selling', 'short', '减仓']:
            return '卖出'
        return '观望'
    
    def format_result_html(self, results: List[Dict]) -> str:
        """格式化 HTML 报告"""
        
        # 标准化 recommendation
        for r in results:
            pred = r.get('prediction', {})
            if 'recommendation' in pred:
                r['prediction']['recommendation'] = self._normalize_recommendation(pred['recommendation'])
        
        buy = [r for r in results if r.get('prediction', {}).get('recommendation') == '买入']
        hold = [r for r in results if r.get('prediction', {}).get('recommendation') == '持有']
        sell = [r for r in results if r.get('prediction', {}).get('recommendation') == '卖出']
        
        def stock_row(r, color):
            data = r.get('stock_data', {})
            pred = r.get('prediction', {})
            return f"""
            <tr style="background: {color};">
                <td><strong>{r['symbol']}</strong></td>
                <td>${data.get('current_price', 'N/A')}</td>
                <td>{data.get('valuation', {}).get('sector', 'N/A')}</td>
                <td>{data.get('momentum', {}).get('1m', 0):+.1f}%</td>
                <td>{data.get('momentum', {}).get('3m', 0):+.1f}%</td>
                <td>{data.get('volatility', {}).get('annual', 0):.0f}%</td>
                <td>{data.get('valuation', {}).get('pe', 'N/A')}</td>
                <td>{pred.get('predicted_return', 'N/A') or 'N/A':+.1f}%</td>
                <td>{pred.get('confidence', 'N/A')}</td>
                <td><strong>{pred.get('recommendation', 'N/A')}</strong></td>
            </tr>
            """
        
        buy_html = '\n'.join([stock_row(r, '#d4edda') for r in buy]) if buy else '<tr><td colspan="10">无</td></tr>'
        hold_html = '\n'.join([stock_row(r, '#fff3cd') for r in hold]) if hold else '<tr><td colspan="10">无</td></tr>'
        sell_html = '\n'.join([stock_row(r, '#f8d7da') for r in sell]) if sell else '<tr><td colspan="10">无</td></tr>'
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>美股多因子持仓分析</title>
    <style>
        body {{ font-family: Arial, margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        h1 {{ color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ display: flex; gap: 15px; margin: 20px 0; flex-wrap: wrap; }}
        .stat {{ background: #007bff; color: white; padding: 15px 25px; border-radius: 8px; text-align: center; }}
        .stat .num {{ font-size: 28px; font-weight: bold; }}
        .stat .label {{ font-size: 12px; opacity: 0.9; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px; }}
        th {{ background: #333; color: white; padding: 10px; }}
        td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
        .disclaimer {{ margin-top: 40px; padding: 15px; background: #ffeeba; border-radius: 8px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 美股多因子持仓分析报告</h1>
        <p><strong>报告日期:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
        <p><strong>分析维度:</strong> 动量 + 波动率 + 趋势 + 技术指标 + 估值 + 成交量</p>
        
        <div class="summary">
            <div class="stat"><div class="num">{len(results)}</div><div class="label">分析</div></div>
            <div class="stat" style="background:#28a745;"><div class="num">{len(buy)}</div><div class="label">买入</div></div>
            <div class="stat" style="background:#ffc107;color:#333;"><div class="num">{len(hold)}</div><div class="label">持有</div></div>
            <div class="stat" style="background:#dc3545;"><div class="num">{len(sell)}</div><div class="label">卖出</div></div>
        </div>
        
        <h2>🟢 买入推荐 ({len(buy)})</h2>
        <table>
            <tr><th>代码</th><th>价格</th><th>行业</th><th>1M</th><th>3M</th><th>波动</th><th>PE</th><th>预测</th><th>置信</th><th>操作</th></tr>
            {buy_html}
        </table>
        
        <h2>🟡 持有/观望 ({len(hold)})</h2>
        <table>
            <tr><th>代码</th><th>价格</th><th>行业</th><th>1M</th><th>3M</th><th>波动</th><th>PE</th><th>预测</th><th>置信</th><th>操作</th></tr>
            {hold_html}
        </table>
        
        <h2>🔴 卖出/减仓 ({len(sell)})</h2>
        <table>
            <tr><th>代码</th><th>价格</th><th>行业</th><th>1M</th><th>3M</th><th>波动</th><th>PE</th><th>预测</th><th>置信</th><th>操作</th></tr>
            {sell_html}
        </table>
        
        <h2>📊 因子评分汇总</h2>
        <table>
            <tr><th>代码</th><th>价格</th><th>综合评分</th><th>动量</th><th>趋势</th><th>估值</th><th>关键因子</th></tr>
            {''.join([f"<tr><td><strong>{r['symbol']}</strong></td><td>${r.get('stock_data', {}).get('current_price', 'N/A')}</td><td>{r.get('stock_data', {}).get('composite_score', 0):+d}</td><td class='{'positive' if r.get('stock_data', {}).get('momentum', {}).get('1m', 0) > 0 else 'negative'}>{r.get('stock_data', {}).get('momentum', {}).get('1m', 0):+.1f}%</td><td>{r.get('stock_data', {}).get('trend', {}).get('signal', 'N/A')}</td><td class='{'positive' if r.get('stock_data', {}).get('valuation', {}).get('pe_ratio', 1) < 1 else ('negative' if r.get('stock_data', {}).get('valuation', {}).get('pe_ratio', 1) > 1.2 else '')}>{r.get('stock_data', {}).get('valuation', {}).get('pe_ratio', 1):.1f}x</td><td>{', '.join(r.get('stock_data', {}).get('key_factors', [])[:4])}</td></tr>" for r in results])}
        </table>
        
        <div class="disclaimer">
            <strong>免责声明:</strong> 本报告由AI生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。
        </div>
    </div>
</body>
</html>
        """
        return html
    
    def send_email(self, html_content: str, subject: str = None):
        """使用阿里云 DirectMail API 发送邮件"""
        
        access_key_id = os.getenv('ALIYUN_ACCESS_KEY_ID', '')
        access_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET', '')
        
        if not access_key_id or not access_secret:
            print("❌ 未配置阿里云 DirectMail API")
            return False
        
        # 读取收件人列表（支持多个，用分号或逗号分隔）
        recipients_str = os.getenv('STOCK_EMAIL_RECIPIENTS', '42213885@qq.com')
        # 解析收件人
        recipients = [e.strip() for e in recipients_str.replace(',', ';').split(';') if e.strip()]
        
        if not recipients:
            print("❌ 未配置收件人邮箱")
            return False
        
        print(f"📧 发送到: {recipients}")
        
        # 发送到所有收件人
        success_count = 0
        for to_email in recipients:
            params = {
                'Format': 'JSON',
                'Version': '2015-11-23',
                'AccessKeyId': access_key_id,
                'SignatureMethod': 'HMAC-SHA1',
                'Timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'SignatureVersion': '1.0',
                'SignatureNonce': str(datetime.now().timestamp()) + str(len(recipients)),
                'Action': 'SingleSendMail',
                'AccountName': 'no_reply@extmail.codebu.top',
                'ReplyToAddress': 'false',
                'AddressType': '1',
                'ToAddress': to_email,
                'Subject': subject or f"美股多因子分析 {datetime.now().strftime('%Y-%m-%d')}",
                'HtmlBody': html_content,
            }
            
            params['Signature'] = signature('GET', '/', params, access_secret)
            url = 'https://dm.aliyuncs.com/'
            
            try:
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'EnvId' in data:
                        print(f"✅ {to_email}: 成功 (EnvId: {data['EnvId']})")
                        success_count += 1
                    else:
                        print(f"❌ {to_email}: 失败 - {data}")
                else:
                    print(f"❌ {to_email}: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {to_email}: 异常 - {e}")
        
        return success_count > 0


async def main():
    """主函数"""
    
    print("\n" + "="*70)
    print("📈 美股多因子分析 - 增强版")
    print("="*70)
    
    agent = StockAnalysisAgent()
    
    # 分析股票
    symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META']
    results = await agent.analyze_stocks(symbols)
    
    # 生成 HTML
    print(f"\n{'='*70}")
    print("📊 生成报告...")
    html = agent.format_result_html(results)
    
    html_file = f"data/stock_analysis_enhanced_{datetime.now().strftime('%Y-%m-%d')}.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ HTML已保存: {html_file}")
    
    # 发送邮件
    print(f"\n{'='*70}")
    print("📧 发送邮件 (阿里云API)...")
    agent.send_email(html)
    
    # 汇总
    print(f"\n{'='*70}")
    print("📊 因子评分汇总")
    print("="*70)
    
    for r in results:
        data = r.get('stock_data', {})
        score = data.get('composite_score', 0)
        print(f"   {r['symbol']:6s}: ${data.get('current_price', 'N/A'):>7} | 综合:{score:+2d} | 动量:{data.get('momentum', {}).get('1m', 0):+.1f}% | PE:{data.get('valuation', {}).get('pe_ratio', 1):.1f}x")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
