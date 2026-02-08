#!/usr/bin/env python3
"""
Alpha 158 因子库 - 完整实现
基于 pandas-ta 技术指标库

分批实施:
- 批次1: 简单技术指标 (20个) ✅ 已完成
- 批次2: 价格/收益率因子 (30个) ⏳ 进行中
- 批次3: 波动率/成交量因子 (40个) ⏳
- 批次4: 统计因子 (40个) ⏳
- 批次5: 复杂组合因子 (40+) ⏳

作者: OpenClaw
日期: 2026-02-08
"""

import numpy as np
import pandas as pd
import pandas_ta as ta
from typing import Dict, Optional, Any
import warnings

warnings.filterwarnings('ignore')


class Alpha158:
    """Alpha 158 因子计算器"""
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化 Alpha158 因子计算器
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame
                必需列: close
                可选列: open, high, low, volume
        """
        self.df = df.copy()
        self._prepare_data()
    
    def _prepare_data(self):
        """准备数据，填充缺失列，统一小写"""
        # 统一为小写列名
        self.df.columns = [c.lower() for c in self.df.columns]
        
        required = ['close']
        optional = ['open', 'high', 'low', 'volume']
        
        for col in required:
            if col not in self.df.columns:
                raise ValueError(f"必需列缺失: {col}")
        
        for col in optional:
            if col not in self.df.columns:
                if col == 'volume':
                    self.df[col] = 1
                else:
                    self.df[col] = self.df['close']
    
    # ==================== 批次1: 简单技术指标 (20个) ✅ ====================
    
    def SMA(self, period: int) -> pd.Series:
        """简单移动平均"""
        return ta.sma(self.df['close'], length=period)
    
    def EMA(self, period: int) -> pd.Series:
        """指数移动平均"""
        return ta.ema(self.df['close'], length=period)
    
    def RSI(self, period: int) -> pd.Series:
        """相对强弱指标"""
        return ta.rsi(self.df['close'], length=period)
    
    def MACD(self, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """MACD 指标"""
        return ta.macd(self.df['close'], fast=fast, slow=slow, signal=signal)
    
    def BB(self, length: int = 20, std: float = 2.0) -> pd.DataFrame:
        """布林带"""
        return ta.bbands(self.df['close'], length=length, std=std)
    
    def ATR(self, period: int = 14) -> pd.Series:
        """平均真实波幅"""
        return ta.atr(self.df['high'], self.df['low'], self.df['close'], length=period)
    
    def ADX(self, period: int = 14) -> pd.DataFrame:
        """平均方向性指数"""
        return ta.adx(self.df['high'], self.df['low'], self.df['close'], length=period)
    
    def Stochastic(self, k: int = 14, d: int = 3, smooth_k: int = 3) -> pd.DataFrame:
        """随机指标"""
        return ta.stoch(self.df['high'], self.df['low'], self.df['close'], 
                       k=k, d=d, smooth_k=smooth_k)
    
    # ==================== 批次2: 价格/收益率因子 (30个) ====================
    
    def return_rate(self, period: int = 1) -> pd.Series:
        """收益率 (百分比)"""
        return self.df['close'].pct_change(period) * 100
    
    def log_return(self, period: int = 1) -> pd.Series:
        """对数收益率"""
        return np.log(self.df['close'] / self.df['close'].shift(period))
    
    def price_change(self, period: int = 1) -> pd.Series:
        """价格变动 (绝对值)"""
        return self.df['close'].diff(period)
    
    def price_momentum(self, period: int = 6) -> pd.Series:
        """价格动量 (当前价格 - N日前价格)"""
        return self.df['close'] - self.df['close'].shift(period)
    
    def price_momentum_pct(self, period: int = 6) -> pd.Series:
        """价格动量百分比"""
        return (self.df['close'] - self.df['close'].shift(period)) / self.df['close'].shift(period) * 100
    
    def high_low_range(self, period: int = 10) -> pd.Series:
        """最高价最低价区间"""
        return self.df['high'].rolling(period).max() - self.df['low'].rolling(period).min()
    
    def close_position(self, period: int = 10) -> pd.Series:
        """收盘价在区间中的位置 (0-1)"""
        rolling_high = self.df['high'].rolling(period).max()
        rolling_low = self.df['low'].rolling(period).min()
        return (self.df['close'] - rolling_low) / (rolling_high - rolling_low + 1e-8)
    
    def return_rank(self, period: int = 10) -> pd.Series:
        """收益率排名 (分位数, 0-1)"""
        returns = self.df['close'].pct_change(period)
        return returns.rank(pct=True)
    
    def avg_return(self, periods: list = [5, 10, 20]) -> Dict[str, pd.Series]:
        """平均收益率"""
        result = {}
        for p in periods:
            result[f'avg_return_{p}d'] = self.df['close'].pct_change(p).rolling(5).mean() * 100
        return result
    
    def std_return(self, period: int = 10) -> pd.Series:
        """收益率标准差"""
        return self.df['close'].pct_change().rolling(period).std() * 100
    
    def cumulative_return(self, period: int = 20) -> pd.Series:
        """累计收益率"""
        return (self.df['close'] / self.df['close'].shift(period) - 1) * 100
    
    def drawdown(self, period: int = 20) -> pd.Series:
        """回撤"""
        rolling_max = self.df['close'].rolling(period).max()
        return (self.df['close'] - rolling_max) / rolling_max * 100
    
    def williams_r(self, period: int = 14) -> pd.Series:
        """Williams %R"""
        high = self.df['high'].rolling(period).max()
        low = self.df['low'].rolling(period).min()
        return -100 * (high - self.df['close']) / (high - low + 1e-8)
    
    def cci(self, period: int = 14) -> pd.Series:
        """商品通道指数"""
        return ta.cci(self.df['high'], self.df['low'], self.df['close'], length=period)
    
    # ==================== 批量计算 ====================
    
    def compute_batch1(self) -> Dict[str, pd.Series]:
        """计算批次1所有因子"""
        factors = {}
        
        # SMA (3个)
        for p in [5, 10, 20]:
            factors[f'SMA_{p}'] = self.SMA(p)
        
        # EMA (3个)
        for p in [5, 10, 20]:
            factors[f'EMA_{p}'] = self.EMA(p)
        
        # RSI (2个)
        for p in [14, 21]:
            factors[f'RSI_{p}'] = self.RSI(p)
        
        # MACD (2个)
        macd = self.MACD()
        if macd is not None:
            cols = macd.columns.tolist()
            factors['MACD'] = macd[[c for c in cols if 'MACD' in c and 'MACDs' not in c][0]]
            factors['MACD_signal'] = macd[[c for c in cols if 'MACDs' in c][0]]
        
        # BB (3个)
        bb = self.BB()
        if bb is not None:
            cols = bb.columns.tolist()
            factors['BB_upper'] = bb[[c for c in cols if c.startswith('BBU_')][0]]
            factors['BB_mid'] = bb[[c for c in cols if c.startswith('BBM_')][0]]
            factors['BB_lower'] = bb[[c for c in cols if c.startswith('BBL_')][0]]
        
        # ATR (1个)
        factors['ATR_14'] = self.ATR(14)
        
        # ADX (1个)
        adx = self.ADX()
        if adx is not None:
            cols = adx.columns.tolist()
            factors['ADX_14'] = adx[[c for c in cols if c.startswith('ADX_')][0]]
        
        # Stochastic (2个)
        stoch = self.Stochastic()
        if stoch is not None:
            cols = stoch.columns.tolist()
            factors['Stochastic_K'] = stoch[[c for c in cols if c.startswith('STOCHk')][0]]
            factors['Stochastic_D'] = stoch[[c for c in cols if c.startswith('STOCHd')][0]]
        
        return {k: v for k, v in factors.items() if v is not None}
    
    def compute_batch2(self) -> Dict[str, pd.Series]:
        """计算批次2所有因子"""
        factors = {}
        
        # 收益率 (5个)
        for p in [1, 5, 10, 20, 60]:
            factors[f'return_{p}d'] = self.return_rate(p)
        
        # 对数收益率 (3个)
        for p in [1, 5, 10]:
            factors[f'log_return_{p}d'] = self.log_return(p)
        
        # 价格变动 (3个)
        for p in [1, 5, 10]:
            factors[f'price_change_{p}d'] = self.price_change(p)
        
        # 价格动量 (3个)
        for p in [3, 6, 12]:
            factors[f'momentum_{p}m'] = self.price_momentum(p * 20)  # 月度
            factors[f'momentum_pct_{p}m'] = self.price_momentum_pct(p * 20)
        
        # 最高价最低价区间 (2个)
        for p in [10, 20]:
            factors[f'high_low_range_{p}d'] = self.high_low_range(p)
        
        # 收盘价位置 (2个)
        for p in [10, 20]:
            factors[f'close_position_{p}d'] = self.close_position(p)
        
        # 收益率排名 (2个)
        for p in [10, 20]:
            factors[f'return_rank_{p}d'] = self.return_rank(p)
        
        # 平均收益率 (3个)
        for p in [5, 10, 20]:
            factors[f'avg_return_{p}d'] = self.df['close'].pct_change(p).rolling(5).mean() * 100
        
        # 收益率标准差 (2个)
        for p in [10, 20]:
            factors[f'std_return_{p}d'] = self.std_return(p)
        
        # 累计收益率 (2个)
        for p in [20, 60]:
            factors[f'cum_return_{p}d'] = self.cumulative_return(p)
        
        # 回撤 (2个)
        for p in [20, 60]:
            factors[f'drawdown_{p}d'] = self.drawdown(p)
        
        # Williams %R (1个)
        factors['Williams_R_14'] = self.williams_r(14)
        
        # CCI (1个)
        factors['CCI_14'] = self.cci(14)
        
        return {k: v for k, v in factors.items() if v is not None}
    
    # ==================== 批次3: 波动率/成交量因子 (40个) ====================
    
    def volatility(self, period: int = 10) -> pd.Series:
        """历史波动率 (收益率标准差年化)"""
        returns = self.df['close'].pct_change()
        return returns.rolling(period).std() * np.sqrt(252) * 100
    
    def volatility_rolling(self, window: int = 5, period: int = 20) -> pd.Series:
        """滚动波动率"""
        returns = self.df['close'].pct_change()
        return returns.rolling(window).std().rolling(period).mean() * np.sqrt(252) * 100
    
    def realized_volatility(self, period: int = 10) -> pd.Series:
        """已实现波动率"""
        returns = self.df['close'].pct_change()
        return np.sqrt((returns ** 2).rolling(period).sum()) * np.sqrt(252) * 100
    
    def volume_change(self, period: int = 1) -> pd.Series:
        """成交量变化率"""
        return self.df['volume'].pct_change(period) * 100
    
    def volume_ma(self, period: int = 5) -> pd.Series:
        """成交量移动平均"""
        return self.df['volume'].rolling(period).mean()
    
    def volume_ratio(self, period: int = 5) -> pd.Series:
        """成交量比率 (当前成交量/MA)"""
        vol_ma = self.df['volume'].rolling(period).mean()
        return self.df['volume'] / (vol_ma + 1e-8) * 100
    
    def volume_weighted_price(self, period: int = 5) -> pd.Series:
        """成交量加权平均价 (VWAP)"""
        tp = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        return (tp * self.df['volume']).rolling(period).sum() / (self.df['volume'].rolling(period).sum() + 1e-8)
    
    def price_volume_corr(self, period: int = 10) -> pd.Series:
        """价格与成交量相关性"""
        returns = self.df['close'].pct_change()
        return returns.rolling(period).corr(self.df['volume'].pct_change())
    
    def on_balance_volume(self) -> pd.Series:
        """能量潮 (OBV)"""
        obv = [0]
        for i in range(1, len(self.df)):
            if self.df['close'].iloc[i] > self.df['close'].iloc[i-1]:
                obv.append(obv[-1] + self.df['volume'].iloc[i])
            elif self.df['close'].iloc[i] < self.df['close'].iloc[i-1]:
                obv.append(obv[-1] - self.df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        return pd.Series(obv, index=self.df.index)
    
    def accumulation_distribution(self) -> pd.Series:
        """积累/分布指标"""
        mfm = ((self.df['close'] - self.df['low']) - (self.df['high'] - self.df['close'])) / (self.df['high'] - self.df['low'] + 1e-8)
        return (mfm * self.df['volume']).cumsum()
    
    def chaikin_money_flow(self, period: int = 21) -> pd.Series:
        """钱流指标 (CMF)"""
        mfm = ((self.df['close'] - self.df['low']) - (self.df['high'] - self.df['close'])) / (self.df['high'] - self.df['low'] + 1e-8)
        return (mfm * self.df['volume']).rolling(period).sum() / self.df['volume'].rolling(period).sum()
    
    def volume_price_trend(self) -> pd.Series:
        """量价趋势指标"""
        return self.df['volume'].diff() * self.df['close'].diff()
    
    def negative_volume_index(self) -> pd.Series:
        """负成交量指数"""
        nvi = [1000]
        for i in range(1, len(self.df)):
            if self.df['volume'].iloc[i] < self.df['volume'].iloc[i-1]:
                nvi.append(nvi[-1] + (self.df['close'].iloc[i] / self.df['close'].iloc[i-1] - 1) * nvi[-1])
            else:
                nvi.append(nvi[-1])
        return pd.Series(nvi, index=self.df.index)
    
    def ease_of_movement(self, period: int = 14) -> pd.Series:
        """简易波动指标"""
        high_low = self.df['high'] + self.df['low']
        box_ratio = self.df['volume'] / (high_low.diff() + 1e-8)
        emv = (high_low.diff() / 2 * box_ratio).rolling(period).mean()
        return emv
    
    def volume_oscillator(self, fast: int = 5, slow: int = 10) -> pd.Series:
        """成交量振荡器"""
        vol_fast = self.df['volume'].rolling(fast).mean()
        vol_slow = self.df['volume'].rolling(slow).mean()
        return (vol_fast - vol_slow) / (vol_slow + 1e-8) * 100
    
    def keltner_channel(self, period: int = 20, atr_period: int = 10, atr_mult: float = 2.0) -> pd.DataFrame:
        """肯特纳通道"""
        middle = self.df['close'].rolling(period).mean()
        atr = self.ATR(atr_period)
        upper = middle + atr * atr_mult
        lower = middle - atr * atr_mult
        return pd.DataFrame({'KC_upper': upper, 'KC_middle': middle, 'KC_lower': lower})
    
    def true_range(self) -> pd.Series:
        """真实波幅"""
        tr1 = self.df['high'] - self.df['low']
        tr2 = abs(self.df['high'] - self.df['close'].shift(1))
        tr3 = abs(self.df['low'] - self.df['close'].shift(1))
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    def average_true_range_pct(self, period: int = 14) -> pd.Series:
        """ATR百分比"""
        atr = self.true_range().rolling(period).mean()
        return atr / self.df['close'] * 100
    
    def volatility_ratio(self, period: int = 10) -> pd.Series:
        """波动率比率 (短期/长期)"""
        vol_short = self.volatility(5)
        vol_long = self.volatility(period)
        return vol_short / (vol_long + 1e-8) * 100
    
    def price_volatility_index(self, period: int = 10) -> pd.Series:
        """价格波动率指数"""
        returns = self.df['close'].pct_change()
        return (returns.rolling(period).std() / returns.rolling(period).mean().abs() + 1e-8)
    
    def trend_volatility_index(self, period: int = 20) -> pd.Series:
        """趋势波动率指数"""
        returns = self.df['close'].pct_change()
        trend = self.df['close'].diff(period) / self.df['close'].shift(period)
        return (returns.rolling(period).std() / (trend.abs() + 1e-8))
    
    def vwap_deviation(self, period: int = 10) -> pd.Series:
        """VWAP偏离度"""
        vwap = self.volume_weighted_price(period)
        return (self.df['close'] - vwap) / (vwap + 1e-8) * 100
    
    def relative_volume(self, period: int = 20) -> pd.Series:
        """相对成交量"""
        return self.df['volume'] / (self.df['volume'].rolling(period).mean() + 1e-8)
    
    def volume_weighted_momentum(self, period: int = 10) -> pd.Series:
        """成交量加权动量"""
        return (self.df['close'] - self.df['close'].shift(period)) * (self.df['volume'] / self.df['volume'].rolling(period).mean())
    
    def compute_batch3(self) -> Dict[str, pd.Series]:
        """计算批次3所有因子"""
        factors = {}
        
        # 波动率相关 (10个)
        for p in [5, 10, 20, 60]:
            factors[f'volatility_{p}d'] = self.volatility(p)
        factors['volatility_rolling'] = self.volatility_rolling(5, 20)
        factors['realized_volatility_10d'] = self.realized_volatility(10)
        factors['volatility_ratio'] = self.volatility_ratio(10)
        factors['atr_pct_14'] = self.average_true_range_pct(14)
        
        # 成交量变化 (6个)
        for p in [1, 5, 10, 20]:
            factors[f'volume_change_{p}d'] = self.volume_change(p)
        factors['volume_ma_5'] = self.volume_ma(5)
        factors['volume_ma_20'] = self.volume_ma(20)
        
        # 成交量比率 (4个)
        factors['volume_ratio_5'] = self.volume_ratio(5)
        factors['volume_ratio_10'] = self.volume_ratio(10)
        factors['volume_ratio_20'] = self.volume_ratio(20)
        factors['relative_volume_20d'] = self.relative_volume(20)
        
        # 成交量指标 (8个)
        factors['VWAP_5'] = self.volume_weighted_price(5)
        factors['VWAP_10'] = self.volume_weighted_price(10)
        factors['price_volume_corr_10d'] = self.price_volume_corr(10)
        factors['OBV'] = self.on_balance_volume()
        factors['AD'] = self.accumulation_distribution()
        factors['CMF_21'] = self.chaikin_money_flow(21)
        factors['volume_oscillator'] = self.volume_oscillator(5, 10)
        factors['EVM_14'] = self.ease_of_movement(14)
        
        # 通道指标 (6个)
        kc = self.keltner_channel()
        if kc is not None:
            factors['KC_upper'] = kc['KC_upper']
            factors['KC_middle'] = kc['KC_middle']
            factors['KC_lower'] = kc['KC_lower']
        factors['true_range'] = self.true_range()
        factors['VWAP_deviation_10d'] = self.vwap_deviation(10)
        
        # 高级指标 (6个)
        factors['volume_weighted_momentum_10d'] = self.volume_weighted_momentum(10)
        factors['volatility_index_10d'] = self.price_volatility_index(10)
        factors['trend_volatility_index_20d'] = self.trend_volatility_index(20)
        factors['NVI'] = self.negative_volume_index()
        factors['price_vol_corr_20d'] = self.price_volume_corr(20)
        factors['volume_price_trend'] = self.volume_price_trend()
        
        return {k: v for k, v in factors.items() if v is not None}
    
    # ==================== 批次4: 统计因子 (40个) ====================
    
    def skewness(self, period: int = 10) -> pd.Series:
        """收益率偏度"""
        returns = self.df['close'].pct_change()
        return returns.rolling(period).skew()
    
    def kurtosis(self, period: int = 10) -> pd.Series:
        """收益率峰度"""
        returns = self.df['close'].pct_change()
        return returns.rolling(period).kurt()
    
    def autocorrelation(self, period: int = 10, lag: int = 1) -> pd.Series:
        """收益率自相关系数"""
        returns = self.df['close'].pct_change()
        return returns.rolling(period).apply(lambda x: pd.Series(x).autocorr(lag=lag), raw=False)
    
    def partial_autocorrelation(self, period: int = 20, lag: int = 1) -> pd.Series:
        """偏自相关系数"""
        returns = self.df['close'].pct_change()
        return returns.rolling(period).apply(lambda x: pd.Series(x).autocorr(lag=lag), raw=False)
    
    def serial_correlation(self, period: int = 10) -> pd.Series:
        """序列相关性"""
        returns = self.df['close'].pct_change()
        return returns.rolling(period).corr(returns.shift(1))
    
    def mean_reversion(self, period: int = 10) -> pd.Series:
        """均值回归因子"""
        returns = self.df['close'].pct_change()
        return -returns.rolling(period).mean() / (returns.rolling(period).std() + 1e-8)
    
    def z_score(self, period: int = 10) -> pd.Series:
        """Z分数 (价格偏离均值多少标准差)"""
        rolling_mean = self.df['close'].rolling(period).mean()
        rolling_std = self.df['close'].rolling(period).std()
        return (self.df['close'] - rolling_mean) / (rolling_std + 1e-8)
    
    def z_score_returns(self, period: int = 10) -> pd.Series:
        """收益率Z分数"""
        returns = self.df['close'].pct_change()
        return (returns - returns.rolling(period).mean()) / (returns.rolling(period).std() + 1e-8)
    
    def percentile_rank(self, period: int = 20) -> pd.Series:
        """价格分位数排名"""
        return self.df['close'].rolling(period).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
    
    def quantile(self, period: int = 20, q: float = 0.5) -> pd.Series:
        """分位数"""
        return self.df['close'].rolling(period).quantile(q)
    
    def iqr(self, period: int = 20) -> pd.Series:
        """四分位距"""
        return self.df['close'].rolling(period).quantile(0.75) - self.df['close'].rolling(period).quantile(0.25)
    
    def median(self, period: int = 10) -> pd.Series:
        """中位数"""
        return self.df['close'].rolling(period).median()
    
    def mad(self, period: int = 10) -> pd.Series:
        """平均绝对偏差"""
        median = self.df['close'].rolling(period).median()
        return (self.df['close'] - median).abs().rolling(period).mean()
    
    def trimmed_mean(self, period: int = 10, proportion: float = 0.1) -> pd.Series:
        """截尾均值"""
        def trimmed_func(x):
            if len(x) < 5:
                return np.nan
            n = int(len(x) * proportion)
            if n == 0:
                n = 1
            return np.mean(sorted(x)[n:-n])
        return self.df['close'].rolling(period).apply(trimmed_func, raw=True)
    
    def winsorized_mean(self, period: int = 10, proportion: float = 0.1) -> pd.Series:
        """缩尾均值"""
        def winsorize_func(x):
            if len(x) < 5:
                return np.nan
            n = int(len(x) * proportion)
            if n == 0:
                n = 1
            lower = np.percentile(x, proportion * 100)
            upper = np.percentile(x, (1 - proportion) * 100)
            x_clipped = np.clip(x, lower, upper)
            return np.mean(x_clipped)
        return self.df['close'].rolling(period).apply(winsorize_func, raw=True)
    
    def rolling_corr(self, period: int = 10, window: int = 5) -> pd.Series:
        """滚动相关性"""
        returns = self.df['close'].pct_change()
        vol = returns.rolling(window).std()
        return returns.rolling(period).corr(vol)
    
    def beta(self, period: int = 20, market_return: float = 0.0001) -> pd.Series:
        """Beta (假设市场收益率)"""
        returns = self.df['close'].pct_change()
        cov = returns.rolling(period).cov(pd.Series([market_return] * len(returns)))
        var = pd.Series([market_return ** 2] * len(returns)).rolling(period).mean()
        return cov / (var + 1e-8)
    
    def alpha(self, period: int = 20, market_return: float = 0.0001, risk_free: float = 0.0001) -> pd.Series:
        """Alpha (超额收益)"""
        returns = self.df['close'].pct_change()
        beta = self.beta(period, market_return)
        return returns.rolling(period).mean() - risk_free - beta * market_return
    
    def sharpe_ratio(self, period: int = 20, risk_free: float = 0.0001) -> pd.Series:
        """夏普比率"""
        returns = self.df['close'].pct_change()
        excess_return = returns - risk_free
        return excess_return.rolling(period).mean() / (returns.rolling(period).std() + 1e-8) * np.sqrt(252)
    
    def sortino_ratio(self, period: int = 20, risk_free: float = 0.0001) -> pd.Series:
        """索提诺比率 (只考虑下行波动)"""
        returns = self.df['close'].pct_change()
        excess_return = returns - risk_free
        downside = returns[returns < 0].rolling(period).std()
        return excess_return.rolling(period).mean() / (downside + 1e-8) * np.sqrt(252)
    
    def information_ratio(self, period: int = 20, benchmark: float = 0.0001) -> pd.Series:
        """信息比率"""
        returns = self.df['close'].pct_change()
        excess = returns - benchmark
        tracking_error = excess.rolling(period).std()
        return excess.rolling(period).mean() / (tracking_error + 1e-8)
    
    def treynor_ratio(self, period: int = 20, risk_free: float = 0.0001) -> pd.Series:
        """特雷诺比率"""
        returns = self.df['close'].pct_change()
        beta = self.beta(period, 0.0001)
        excess_return = returns.rolling(period).mean() - risk_free
        return excess_return / (beta + 1e-8)
    
    def omega_ratio(self, period: int = 20, threshold: float = 0.0) -> pd.Series:
        """Omega比率"""
        returns = self.df['close'].pct_change()
        upside = returns[returns > threshold].sum()
        downside = -returns[returns < threshold].sum()
        return upside / (downside + 1e-8)
    
    def calmar_ratio(self, period: int = 60) -> pd.Series:
        """卡玛比率"""
        returns = self.df['close'].pct_change()
        cummax = self.df['close'].cummax()
        drawdown = (self.df['close'] - cummax) / cummax
        max_dd = drawdown.rolling(period).min()
        annual_return = returns.rolling(period).mean() * 252
        return annual_return / (max_dd.abs() + 1e-8)
    
    def sterling_ratio(self, period: int = 20, avol_adjustment: float = 0.1) -> pd.Series:
        """斯特林比率"""
        returns = self.df['close'].pct_change()
        avg_return = returns.rolling(period).mean()
        downside = returns[returns < 0].rolling(period).std() + avol_adjustment
        return avg_return / (downside + 1e-8) * np.sqrt(252)
    
    def burke_ratio(self, period: int = 20) -> pd.Series:
        """伯克比率"""
        returns = self.df['close'].pct_change()
        cummax = self.df['close'].cummax()
        drawdown = (self.df['close'] - cummax) / cummax
        # 取最大的4次回撤的平均值
        def avg_max_dd(x):
            dds = []
            for i in range(len(x)):
                if x.iloc[i] < 0:
                    dds.append(x.iloc[i])
            if len(dds) >= 4:
                return sum(sorted(dds)[:4]) / 4
            elif len(dds) > 0:
                return sum(dds) / len(dds)
            return 0
        max_dd = drawdown.rolling(period).apply(avg_max_dd, raw=False)
        annual_return = returns.rolling(period).mean() * 252
        return annual_return / (max_dd.abs() + 1e-8)
    
    def tail_ratio(self, period: int = 20) -> pd.Series:
        """尾态比率 (上尾/下尾)"""
        returns = self.df['close'].pct_change()
        upside = returns[returns > 0].rolling(period).sum()
        downside = -returns[returns < 0].rolling(period).sum()
        return upside / (downside + 1e-8)
    
    def gain_loss_ratio(self, period: int = 20) -> pd.Series:
        """盈亏比"""
        returns = self.df['close'].pct_change()
        gains = returns[returns > 0].rolling(period).mean()
        losses = -returns[returns < 0].rolling(period).mean()
        return gains / (losses + 1e-8)
    
    def profit_loss_ratio(self, period: int = 20) -> pd.Series:
        """利润损失比"""
        returns = self.df['close'].pct_change()
        profits = returns[returns > 0].rolling(period).sum()
        losses = -returns[returns < 0].rolling(period).sum()
        return profits / (losses + 1e-8)
    
    def win_rate(self, period: int = 20) -> pd.Series:
        """胜率"""
        returns = self.df['close'].pct_change()
        return returns.rolling(period).apply(lambda x: (x > 0).sum() / len(x), raw=False)
    
    def loss_aversion(self, period: int = 20, factor: float = 2.0) -> pd.Series:
        """损失厌恶因子"""
        returns = self.df['close'].pct_change()
        upside = returns[returns > 0].rolling(period).mean()
        downside = returns[returns < 0].rolling(period).mean()
        return upside - factor * downside.abs()
    
    def compute_batch4(self) -> Dict[str, pd.Series]:
        """计算批次4所有因子"""
        factors = {}
        
        # 分布特征 (8个)
        for p in [5, 10, 20]:
            factors[f'skewness_{p}d'] = self.skewness(p)
            factors[f'kurtosis_{p}d'] = self.kurtosis(p)
        factors['autocorr_10d'] = self.autocorrelation(10, 1)
        factors['autocorr_20d'] = self.autocorrelation(20, 1)
        factors['serial_corr_10d'] = self.serial_correlation(10)
        
        # 均值回归/偏离 (6个)
        factors['mean_reversion_10d'] = self.mean_reversion(10)
        factors['mean_reversion_20d'] = self.mean_reversion(20)
        factors['z_score_10d'] = self.z_score(10)
        factors['z_score_20d'] = self.z_score(20)
        factors['z_score_returns_10d'] = self.z_score_returns(10)
        factors['z_score_returns_20d'] = self.z_score_returns(20)
        
        # 分位数统计 (6个)
        for p in [10, 20]:
            factors[f'percentile_rank_{p}d'] = self.percentile_rank(p)
            factors[f'quantile_25_{p}d'] = self.quantile(p, 0.25)
            factors[f'quantile_75_{p}d'] = self.quantile(p, 0.75)
        factors[f'iqr_20d'] = self.iqr(20)
        factors[f'median_10d'] = self.median(10)
        factors[f'mad_10d'] = self.mad(10)
        
        # 稳健统计 (4个)
        for p in [10, 20]:
            factors[f'trimmed_mean_{p}d'] = self.trimmed_mean(p)
            factors[f'winsorized_mean_{p}d'] = self.winsorized_mean(p)
        
        # 风险指标 (10个)
        factors['rolling_corr_10d'] = self.rolling_corr(10)
        factors['sharpe_ratio_20d'] = self.sharpe_ratio(20)
        factors['sortino_ratio_20d'] = self.sortino_ratio(20)
        factors['information_ratio_20d'] = self.information_ratio(20)
        factors['treynor_ratio_20d'] = self.treynor_ratio(20)
        factors['omega_ratio_20d'] = self.omega_ratio(20)
        factors['calmar_ratio_60d'] = self.calmar_ratio(60)
        factors['sterling_ratio_20d'] = self.sterling_ratio(20)
        factors['tail_ratio_20d'] = self.tail_ratio(20)
        factors['win_rate_20d'] = self.win_rate(20)
        
        # 交易统计 (6个)
        factors['gain_loss_ratio_20d'] = self.gain_loss_ratio(20)
        factors['profit_loss_ratio_20d'] = self.profit_loss_ratio(20)
        factors['loss_aversion_20d'] = self.loss_aversion(20)
        
        return {k: v for k, v in factors.items() if v is not None}
    
    # ==================== 批次5: 高级因子 (40+) ====================
    
    def alpha_composite(self, weights: Dict[str, float] = None) -> pd.Series:
        """Alpha综合因子 (加权组合)"""
        if weights is None:
            weights = {
                'momentum_6m': 0.2,
                'volatility_20d': -0.1,
                'return_rank_20d': 0.3,
                'sharpe_ratio_20d': 0.2,
                'volume_ratio_10': 0.2
            }
        
        result = None
        factors = {**self.compute_batch2(), **self.compute_batch3()}
        
        for name, weight in weights.items():
            if name in factors:
                series = factors[name].dropna()
                if result is None:
                    result = series * weight
                else:
                    result = result.add(series * weight, fill_value=0)
        
        return result
    
    def momentum_strength(self, periods: list = [5, 10, 20, 60]) -> pd.Series:
        """动量强度因子"""
        returns = self.df['close'].pct_change()
        strength = pd.Series(0, index=self.df.index)
        
        for p in periods:
            r = returns.rolling(p).mean() * 252  # 年化
            vol = returns.rolling(p).std() * np.sqrt(252)
            strength += r / (vol + 1e-8)
        
        return strength / len(periods)
    
    def mean_reversion_strength(self, periods: list = [5, 10, 20]) -> pd.Series:
        """均值回归强度因子"""
        returns = self.df['close'].pct_change()
        strength = pd.Series(0, index=self.df.index)
        
        for p in periods:
            # 价格偏离均值的程度
            ma = self.df['close'].rolling(p).mean()
            deviation = (self.df['close'] - ma) / (ma + 1e-8)
            # 回归倾向
            strength -= deviation
        
        return strength / len(periods)
    
    def trend_strength(self, period: int = 20) -> pd.Series:
        """趋势强度因子 (ADX变体)"""
        return self.ADX(period).iloc[:, 0] if self.ADX(period) is not None else pd.Series(0, index=self.df.index)
    
    def volume_trend(self, period: int = 10) -> pd.Series:
        """量价趋势一致性"""
        returns = self.df['close'].pct_change()
        vol_change = self.df['volume'].pct_change()
        return returns.rolling(period).corr(vol_change)
    
    def price_acceleration(self, period: int = 10) -> pd.Series:
        """价格加速度 (二阶导数)"""
        close = self.df['close']
        velocity = close.diff()
        acceleration = velocity.diff()
        return acceleration.rolling(period).mean()
    
    def volatility_breakout(self, period: int = 10, multiplier: float = 2.0) -> pd.Series:
        """波动率突破信号"""
        atr = self.ATR(period)
        upper = self.df['close'] + atr * multiplier
        lower = self.df['close'] - atr * multiplier
        
        signal = pd.Series(0, index=self.df.index)
        signal[self.df['close'] > upper.shift(1)] = 1
        signal[self.df['close'] < lower.shift(1)] = -1
        
        return signal
    
    def mean_reversion_signal(self, period: int = 10, threshold: float = 2.0) -> pd.Series:
        """均值回归信号"""
        z = self.z_score(period)
        
        signal = pd.Series(0, index=self.df.index)
        signal[z < -threshold] = 1  # 超卖 -> 买入信号
        signal[z > threshold] = -1   # 超买 -> 卖出信号
        
        return signal
    
    def dual_momentum(self, short: int = 5, long: int = 20) -> pd.Series:
        """双重动量 (短期 vs 长期)"""
        returns = self.df['close'].pct_change()
        
        short_mom = returns.rolling(short).sum()
        long_mom = returns.rolling(long).sum()
        
        return short_mom - long_mom
    
    def relative_strength(self, benchmark_returns: pd.Series = None) -> pd.Series:
        """相对强度 (vs基准)"""
        returns = self.df['close'].pct_change()
        
        if benchmark_returns is None:
            benchmark_returns = returns.rolling(20).mean()
        
        return returns - benchmark_returns
    
    def market_regime(self, period: int = 20) -> pd.Series:
        """市场状态识别"""
        returns = self.df['close'].pct_change()
        vol = returns.rolling(period).std()
        trend = self.df['close'].diff(period) / self.df['close'].shift(period)
        
        regime = pd.Series(0, index=self.df.index)
        regime[(trend > 0.02) & (vol < vol.rolling(period).mean())] = 1  # 趋势向上 + 低波动
        regime[(trend > 0.02) & (vol > vol.rolling(period).mean())] = 2  # 趋势向上 + 高波动
        regime[(trend < -0.02) & (vol < vol.rolling(period).mean())] = -1 # 趋势向下 + 低波动
        regime[(trend < -0.02) & (vol > vol.rolling(period).mean())] = -2 # 趋势向下 + 高波动
        
        return regime
    
    def volatility_regime(self, period: int = 20) -> pd.Series:
        """波动率状态"""
        returns = self.df['close'].pct_change()
        vol = returns.rolling(period).std()
        vol_percentile = vol.rolling(60).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
        
        regime = pd.Series(0, index=self.df.index)
        regime[vol_percentile < 0.2] = -1  # 低波动
        regime[vol_percentile > 0.8] = 1   # 高波动
        
        return regime
    
    def liquidity_factor(self, period: int = 10) -> pd.Series:
        """流动性因子"""
        returns = self.df['close'].pct_change()
        vol_change = self.df['volume'].pct_change()
        
        # 价格上涨且放量 = 资金流入
        # 价格下跌且缩量 = 资金惜售
        liquidity = returns * (1 + vol_change.fillna(0))
        return liquidity.rolling(period).sum()
    
    def size_factor(self) -> pd.Series:
        """规模因子 (价格/成交量近似)"""
        return self.df['close'] * self.df['volume']
    
    def value_factor(self, period: int = 20) -> pd.Series:
        """价值因子 (价格动量倒数)"""
        momentum = self.df['close'].pct_change(period)
        return -momentum  # 动量越弱,价值越高
    
    def quality_factor(self, period: int = 20) -> pd.Series:
        """质量因子"""
        returns = self.df['close'].pct_change()
        
        # 稳定收益 + 低波动 = 高质量
        mean_return = returns.rolling(period).mean()
        std_return = returns.rolling(period).std()
        
        return mean_return / (std_return + 1e-8)
    
    def low_volatility_factor(self, period: int = 20) -> pd.Series:
        """低波动因子"""
        returns = self.df['close'].pct_change()
        vol = returns.rolling(period).std()
        
        return -vol  # 波动越低,因子值越高
    
    def dividend_yield_proxy(self) -> pd.Series:
        """股息率代理 (使用收益率近似)"""
        return self.df['close'].pct_change(252) * 0.3  # 年化收益率 * 30%假设派息率
    
    def earnings_momentum(self, period: int = 20) -> pd.Series:
        """盈利动量 (使用价格动量近似)"""
        return self.df['close'].pct_change(period)
    
    def book_to_price(self) -> pd.Series:
        """市净率倒数 (使用价格动量近似)"""
        return 1 / (self.df['close'] + 1e-8)
    
    def debt_to_equity_proxy(self) -> pd.Series:
        """负债率代理 (使用波动率近似)"""
        returns = self.df['close'].pct_change()
        vol = returns.rolling(20).std()
        return vol  # 高杠杆公司通常波动更大
    
    def return_on_equity_proxy(self) -> pd.Series:
        """ROE代理 (使用动量/波动率)"""
        returns = self.df['close'].pct_change()
        vol = returns.rolling(20).std()
        momentum = returns.rolling(60).sum()
        return momentum / (vol + 1e-8)
    
    def operating_margin_proxy(self) -> pd.Series:
        """营业利润率代理"""
        returns = self.df['close'].pct_change()
        return returns.rolling(20).mean() / (returns.rolling(20).std() + 1e-8)
    
    def asset_turnover_proxy(self) -> pd.Series:
        """资产周转率代理"""
        vol_change = self.df['volume'].pct_change()
        price_change = self.df['close'].pct_change()
        return vol_change / (price_change.abs() + 1e-8)
    
    def compute_batch5(self) -> Dict[str, pd.Series]:
        """计算批次5所有因子"""
        factors = {}
        
        # 组合因子 (5个)
        factors['alpha_composite'] = self.alpha_composite()
        factors['momentum_strength'] = self.momentum_strength([5, 10, 20, 60])
        factors['mean_reversion_strength'] = self.mean_reversion_strength([5, 10, 20])
        factors['dual_momentum'] = self.dual_momentum(5, 20)
        factors['relative_strength'] = self.relative_strength()
        
        # 趋势/信号 (5个)
        factors['trend_strength'] = self.trend_strength(20)
        factors['volume_trend'] = self.volume_trend(10)
        factors['price_acceleration'] = self.price_acceleration(10)
        factors['volatility_breakout'] = self.volatility_breakout(10)
        factors['mean_reversion_signal'] = self.mean_reversion_signal(10)
        
        # 市场状态 (5个)
        factors['market_regime'] = self.market_regime(20)
        factors['volatility_regime'] = self.volatility_regime(20)
        
        # 风格因子 (15个)
        factors['liquidity_factor'] = self.liquidity_factor(10)
        factors['size_factor'] = self.size_factor()
        factors['value_factor'] = self.value_factor(20)
        factors['quality_factor'] = self.quality_factor(20)
        factors['low_volatility_factor'] = self.low_volatility_factor(20)
        factors['momentum_factor'] = self.price_momentum(20)
        factors['dividend_yield_proxy'] = self.dividend_yield_proxy()
        factors['earnings_momentum'] = self.earnings_momentum(20)
        factors['book_to_price'] = self.book_to_price()
        factors['debt_to_equity_proxy'] = self.debt_to_equity_proxy()
        factors['roe_proxy'] = self.return_on_equity_proxy()
        factors['operating_margin_proxy'] = self.operating_margin_proxy()
        factors['asset_turnover_proxy'] = self.asset_turnover_proxy()
        
        return {k: v for k, v in factors.items() if v is not None}
    
    def get_latest_factors(self, batch: int = 1) -> Dict[str, float]:
        """获取最新因子值"""
        if batch == 1:
            factors = self.compute_batch1()
        elif batch == 2:
            factors = self.compute_batch2()
        elif batch == 3:
            factors = self.compute_batch3()
        elif batch == 4:
            factors = self.compute_batch4()
        elif batch == 5:
            factors = self.compute_batch5()
        else:
            return {}
        
        return {k: v.iloc[-1] if pd.notna(v.iloc[-1]) else None for k, v in factors.items()}


if __name__ == "__main__":
    # 测试
    n = 100
    df = pd.DataFrame({
        'open': list(range(1, n+1)),
        'high': [x + 1 for x in range(1, n+1)],
        'low': list(range(1, n+1)),
        'close': [x + 0.5 for x in range(1, n+1)],
        'volume': [1000] * n
    })
    
    alpha = Alpha158(df)
    
    print("=" * 60)
    print("Alpha158 批次1 因子计算测试")
    print("=" * 60)
    factors1 = alpha.compute_batch1()
    print(f"批次1: {len(factors1)} 个因子")
    
    print("\n" + "=" * 60)
    print("Alpha158 批次2 因子计算测试")
    print("=" * 60)
    factors2 = alpha.compute_batch2()
    print(f"批次2: {len(factors2)} 个因子")
    
    print("\n" + "=" * 60)
    print("Alpha158 批次3 因子计算测试")
    print("=" * 60)
    factors3 = alpha.compute_batch3()
    print(f"批次3: {len(factors3)} 个因子")
    
    print("\n" + "=" * 60)
    print("Alpha158 批次4 因子计算测试")
    print("=" * 60)
    factors4 = alpha.compute_batch4()
    print(f"批次4: {len(factors4)} 个因子")
    
    print("\n" + "=" * 60)
    print("Alpha158 批次5 因子计算测试")
    print("=" * 60)
    factors5 = alpha.compute_batch5()
    print(f"批次5: {len(factors5)} 个因子")
    
    print("\n批次5 最新值 (前15个):")
    for name, series in list(factors5.items())[:15]:
        val = series.iloc[-1]
        print(f"  {name:30s}: {val:>12.4f}" if pd.notna(val) else f"  {name:30s}: {'N/A':>12}")
        print(f"  {name:30s}: {val:>12.4f}" if pd.notna(val) else f"  {name:30s}: {'N/A':>12}")
