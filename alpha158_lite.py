#!/usr/bin/env python3
"""
Alpha 158 因子库 - 轻量版 (纯 pandas/numpy 实现)
不依赖 pandas_ta，兼容 Python 3.11+

作者：OpenClaw
日期：2026-03-08
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Any
import warnings

warnings.filterwarnings('ignore')


class Alpha158:
    """Alpha 158 因子计算器 - 轻量版"""

    def __init__(self, df: pd.DataFrame):
        """
        初始化 Alpha158 因子计算器

        Args:
            df: 包含 OHLCV 数据的 DataFrame
                必需列：close
                可选列：open, high, low, volume
        """
        self.df = df.copy()
        self._prepare_data()

    def _prepare_data(self):
        """准备数据，填充缺失列，统一小写"""
        self.df.columns = [c.lower() for c in self.df.columns]

        required = ['close']
        optional = ['open', 'high', 'low', 'volume']

        for col in required:
            if col not in self.df.columns:
                raise ValueError(f"必需列缺失：{col}")

        for col in optional:
            if col not in self.df.columns:
                if col == 'volume':
                    self.df[col] = 1
                else:
                    self.df[col] = self.df['close']

    # ==================== 辅助函数 ====================

    def _sma(self, series: pd.Series, period: int) -> pd.Series:
        """简单移动平均"""
        return series.rolling(window=period, min_periods=1).mean()

    def _ema(self, series: pd.Series, period: int) -> pd.Series:
        """指数移动平均"""
        return series.ewm(span=period, adjust=False, min_periods=1).mean()

    def _std(self, series: pd.Series, period: int) -> pd.Series:
        """滚动标准差"""
        return series.rolling(window=period, min_periods=1).std()

    # ==================== 技术指标 ====================

    def SMA(self, period: int = 20) -> pd.Series:
        """简单移动平均"""
        return self._sma(self.df['close'], period)

    def EMA(self, period: int = 20) -> pd.Series:
        """指数移动平均"""
        return self._ema(self.df['close'], period)

    def RSI(self, period: int = 14) -> pd.Series:
        """相对强弱指标"""
        delta = self.df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = self._sma(gain, period)
        avg_loss = self._sma(loss, period)

        rs = avg_gain / (avg_loss.replace(0, np.nan))
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    def MACD(self, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """MACD 指标"""
        ema_fast = self._ema(self.df['close'], fast)
        ema_slow = self._ema(self.df['close'], slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal)
        hist = macd_line - signal_line

        return pd.DataFrame({
            'macd': macd_line,
            'macds': signal_line,
            'macdh': hist
        })

    def BB(self, length: int = 20, std: float = 2.0) -> pd.DataFrame:
        """布林带"""
        middle = self._sma(self.df['close'], length)
        std_dev = self._std(self.df['close'], length)
        upper = middle + std * std_dev
        lower = middle - std * std_dev

        return pd.DataFrame({
            'bbl': lower,
            'bbm': middle,
            'bbu': upper,
            'bbb': (upper - lower) / middle,
            'bbp': (self.df['close'] - lower) / (upper - lower)
        })

    def ATR(self, period: int = 14) -> pd.Series:
        """平均真实波幅"""
        high = self.df['high']
        low = self.df['low']
        close = self.df['close'].shift(1)

        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        return self._ema(tr, period)

    def ADX(self, period: int = 14) -> pd.DataFrame:
        """平均方向性指数"""
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']

        # +DM and -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        # TR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Smoothed
        atr = self._ema(tr, period)
        plus_di = 100 * self._ema(plus_dm, period) / atr
        minus_di = 100 * self._ema(minus_dm, period) / atr

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        adx = self._ema(dx, period)

        return pd.DataFrame({
            'adx': adx,
            'plus_di': plus_di,
            'minus_di': minus_di
        })

    def Stochastic(self, k: int = 14, d: int = 3, smooth_k: int = 3) -> pd.DataFrame:
        """随机指标"""
        low_min = self.df['low'].rolling(window=k, min_periods=1).min()
        high_max = self.df['high'].rolling(window=k, min_periods=1).max()

        stoch_k = 100 * (self.df['close'] - low_min) / (high_max - low_min).replace(0, np.nan)
        stoch_k = self._sma(stoch_k, smooth_k)
        stoch_d = self._sma(stoch_k, d)

        return pd.DataFrame({
            'stoch_k': stoch_k,
            'stoch_d': stoch_d
        })

    # ==================== 收益率因子 ====================

    def return_rate(self, period: int = 1) -> pd.Series:
        """收益率"""
        return self.df['close'].pct_change(period) * 100

    def momentum(self, period: int = 20) -> pd.Series:
        """动量"""
        return (self.df['close'] / self.df['close'].shift(period) - 1) * 100

    def roc(self, period: int = 10) -> pd.Series:
        """变化率"""
        return (self.df['close'] - self.df['close'].shift(period)) / self.df['close'].shift(period) * 100

    # ==================== 波动率因子 ====================

    def volatility(self, period: int = 20) -> pd.Series:
        """波动率 (年化)"""
        returns = self.df['close'].pct_change()
        return returns.rolling(window=period, min_periods=1).std() * np.sqrt(252) * 100

    def realized_volatility(self, period: int = 20) -> pd.Series:
        """已实现波动率"""
        log_ret = np.log(self.df['close'] / self.df['close'].shift(1))
        return np.sqrt((log_ret ** 2).rolling(window=period, min_periods=1).sum()) * np.sqrt(252) * 100

    # ==================== 动量因子 ====================

    def momentum_factor(self) -> pd.Series:
        """综合动量因子"""
        mom_1m = self.momentum(20)
        mom_3m = self.momentum(60)
        mom_6m = self.momentum(120)
        return (mom_1m * 0.3 + mom_3m * 0.4 + mom_6m * 0.3)

    def trend_strength(self) -> pd.Series:
        """趋势强度"""
        ma_5 = self.SMA(5)
        ma_10 = self.SMA(10)
        ma_20 = self.SMA(20)

        # 多头排列得分
        score = pd.Series(0.0, index=self.df.index)
        score += (ma_5 > ma_10).astype(float) * 50
        score += (ma_10 > ma_20).astype(float) * 50
        return score

    # ==================== 风险调整收益因子 ====================

    def sharpe_ratio(self, period: int = 20) -> pd.Series:
        """夏普比率"""
        returns = self.df['close'].pct_change()
        mean_ret = returns.rolling(window=period, min_periods=1).mean()
        std_ret = returns.rolling(window=period, min_periods=1).std()
        return (mean_ret / std_ret.replace(0, np.nan) * np.sqrt(252)).fillna(0)

    def sortino_ratio(self, period: int = 20) -> pd.Series:
        """索提诺比率"""
        returns = self.df['close'].pct_change()
        mean_ret = returns.rolling(window=period, min_periods=1).mean() * 252
        downside = returns.where(returns < 0, 0)
        downside_std = downside.rolling(window=period, min_periods=1).std() * np.sqrt(252)
        return (mean_ret / downside_std.replace(0, np.nan)).fillna(0)

    def calmar_ratio(self, period: int = 60) -> pd.Series:
        """卡尔玛比率"""
        returns = self.df['close'].pct_change()
        ann_ret = returns.rolling(window=period, min_periods=1).mean() * 252

        # 最大回撤
        cum_ret = (1 + returns).cumprod()
        rolling_max = cum_ret.rolling(window=period, min_periods=1).max()
        drawdown = (cum_ret - rolling_max) / rolling_max
        max_dd = drawdown.rolling(window=period, min_periods=1).min()

        return (ann_ret / abs(max_dd).replace(0, np.nan)).fillna(0)

    # ==================== 批量计算方法 ====================

    def compute_batch1(self) -> Dict[str, pd.Series]:
        """批次 1: 基础技术指标"""
        result = {}

        # 均线
        for p in [5, 10, 20, 50]:
            result[f'sma_{p}'] = self.SMA(p)
            result[f'ema_{p}'] = self.EMA(p)

        # RSI
        for p in [7, 14, 21]:
            result[f'rsi_{p}'] = self.RSI(p)

        # MACD
        macd = self.MACD()
        result['macd'] = macd['macd']
        result['macds'] = macd['macds']
        result['macdh'] = macd['macdh']

        return result

    def compute_batch2(self) -> Dict[str, pd.Series]:
        """批次 2: 收益率因子"""
        result = {}

        # 收益率
        for p in [1, 5, 10, 20, 60, 120]:
            result[f'return_{p}d'] = self.return_rate(p)
            result[f'momentum_{p}d'] = self.momentum(p)

        # ROC
        result['roc_10d'] = self.roc(10)
        result['roc_20d'] = self.roc(20)

        return result

    def compute_batch3(self) -> Dict[str, pd.Series]:
        """批次 3: 波动率因子"""
        result = {}

        # 波动率
        for p in [10, 20, 60]:
            result[f'volatility_{p}d'] = self.volatility(p)
            result[f'realized_vol_{p}d'] = self.realized_volatility(p)

        # ATR
        result['atr_14'] = self.ATR(14)
        result['atr_20'] = self.ATR(20)

        return result

    def compute_batch4(self) -> Dict[str, pd.Series]:
        """批次 4: 风险调整收益因子"""
        result = {}

        # 夏普比率
        result['sharpe_ratio_20d'] = self.sharpe_ratio(20)
        result['sharpe_ratio_60d'] = self.sharpe_ratio(60)

        # 索提诺比率
        result['sortino_ratio_20d'] = self.sortino_ratio(20)
        result['sortino_ratio_60d'] = self.sortino_ratio(60)

        # 卡尔玛比率
        result['calmar_ratio_20d'] = self.calmar_ratio(20)
        result['calmar_ratio_60d'] = self.calmar_ratio(60)

        return result

    def compute_batch5(self) -> Dict[str, pd.Series]:
        """批次 5: 趋势和动量因子"""
        result = {}

        # 趋势强度
        result['trend_strength'] = self.trend_strength()

        # 动量因子
        result['momentum_factor'] = self.momentum_factor()

        # 布林带
        bb = self.BB()
        result['bb_lower'] = bb['bbl']
        result['bb_middle'] = bb['bbm']
        result['bb_upper'] = bb['bbu']
        result['bb_width'] = bb['bbb']
        result['bb_pct'] = bb['bbp']

        # ADX
        adx = self.ADX()
        result['adx_14'] = adx['adx']
        result['plus_di'] = adx['plus_di']
        result['minus_di'] = adx['minus_di']

        # 随机指标
        stoch = self.Stochastic()
        result['stoch_k'] = stoch['stoch_k']
        result['stoch_d'] = stoch['stoch_d']

        return result

    def compute_all_factors(self) -> Dict[str, pd.Series]:
        """计算所有因子"""
        result = {}
        for batch_name in ['compute_batch1', 'compute_batch2', 'compute_batch3',
                          'compute_batch4', 'compute_batch5']:
            try:
                batch_func = getattr(self, batch_name)
                batch_result = batch_func()
                result.update(batch_result)
            except Exception as e:
                print(f"{batch_name} 错误：{e}")

        return result
