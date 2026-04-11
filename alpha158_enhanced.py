"""
Alpha158 因子库增强版 - 添加新的因子类型和优化计算方法
"""

import numpy as np
import pandas as pd
import pandas_ta as ta
from typing import Dict, Optional, Any
import warnings
from alpha158 import Alpha158

warnings.filterwarnings('ignore')


class Alpha158Enhanced(Alpha158):
    """Alpha158 因子库增强版"""

    # ==================== 新增: 基本面因子 (20个) ====================

    def price_to_earnings(self) -> pd.Series:
        """市盈率 (PE) 代理因子"""
        return self.df['close'] / (self.df['close'].rolling(20).mean() + 1e-8)

    def price_to_book(self) -> pd.Series:
        """市净率 (PB) 代理因子"""
        return self.df['close'] / (self.df['close'].rolling(60).mean() + 1e-8)

    def price_to_sales(self) -> pd.Series:
        """市销率 (PS) 代理因子"""
        return self.df['close'] / (self.df['volume'].rolling(20).mean() + 1e-8)

    def dividend_yield(self) -> pd.Series:
        """股息率代理因子"""
        return (self.df['close'].pct_change(252) * 0.3).rolling(20).mean() * 100

    def earnings_per_share(self) -> pd.Series:
        """每股收益 (EPS) 代理因子"""
        return self.df['close'].rolling(20).mean() * 0.05

    def book_value_per_share(self) -> pd.Series:
        """每股净资产代理因子"""
        return self.df['close'].rolling(60).mean() * 0.7

    def sales_growth(self) -> pd.Series:
        """销售额增长代理因子"""
        return self.df['volume'].pct_change(20).rolling(10).mean() * 100

    def earnings_growth(self) -> pd.Series:
        """盈利增长代理因子"""
        return self.df['close'].pct_change(20).rolling(10).mean() * 100

    def return_on_equity(self) -> pd.Series:
        """净资产收益率 (ROE) 代理因子"""
        return self.df['close'].pct_change(20) / (self.df['close'].pct_change(60) + 1e-8)

    def return_on_assets(self) -> pd.Series:
        """资产收益率 (ROA) 代理因子"""
        return self.df['close'].pct_change(20) / (self.df['volume'].pct_change(60) + 1e-8)

    def profit_margin(self) -> pd.Series:
        """利润率代理因子"""
        return self.df['close'].pct_change(10) / (self.df['volume'].pct_change(10) + 1e-8)

    def operating_margin(self) -> pd.Series:
        """营业利润率代理因子"""
        return self.df['close'].pct_change(20) / (self.df['volume'].pct_change(20) + 1e-8)

    def gross_margin(self) -> pd.Series:
        """毛利率代理因子"""
        return self.df['close'].pct_change(30) / (self.df['volume'].pct_change(30) + 1e-8)

    def debt_to_equity(self) -> pd.Series:
        """负债权益比代理因子"""
        return self.df['close'].rolling(20).std() / (self.df['close'].rolling(60).std() + 1e-8)

    def current_ratio(self) -> pd.Series:
        """流动比率代理因子"""
        return self.df['volume'].rolling(20).mean() / (self.df['volume'].rolling(60).mean() + 1e-8)

    def quick_ratio(self) -> pd.Series:
        """速动比率代理因子"""
        return self.df['volume'].rolling(10).mean() / (self.df['volume'].rolling(30).mean() + 1e-8)

    def cash_ratio(self) -> pd.Series:
        """现金比率代理因子"""
        return self.df['volume'].rolling(5).mean() / (self.df['volume'].rolling(20).mean() + 1e-8)

    def interest_coverage_ratio(self) -> pd.Series:
        """利息覆盖比率代理因子"""
        return self.df['close'].rolling(20).mean() / (self.df['close'].rolling(20).std() + 1e-8)

    def inventory_turnover(self) -> pd.Series:
        """存货周转率代理因子"""
        return self.df['volume'].pct_change(20)

    def compute_fundamental_factors(self) -> Dict[str, pd.Series]:
        """计算所有基本面因子"""
        factors = {}

        factors['pe_ratio'] = self.price_to_earnings()
        factors['pb_ratio'] = self.price_to_book()
        factors['ps_ratio'] = self.price_to_sales()
        factors['dividend_yield'] = self.dividend_yield()
        factors['eps'] = self.earnings_per_share()
        factors['bvps'] = self.book_value_per_share()
        factors['sales_growth'] = self.sales_growth()
        factors['earnings_growth'] = self.earnings_growth()
        factors['roe'] = self.return_on_equity()
        factors['roa'] = self.return_on_assets()
        factors['profit_margin'] = self.profit_margin()
        factors['operating_margin'] = self.operating_margin()
        factors['gross_margin'] = self.gross_margin()
        factors['debt_to_equity'] = self.debt_to_equity()
        factors['current_ratio'] = self.current_ratio()
        factors['quick_ratio'] = self.quick_ratio()
        factors['cash_ratio'] = self.cash_ratio()
        factors['interest_coverage'] = self.interest_coverage_ratio()
        factors['inventory_turnover'] = self.inventory_turnover()

        return {k: v for k, v in factors.items() if v is not None and len(v) > 0}

    # ==================== 新增: 机器学习因子 (25个) ====================

    def price_momentum_features(self) -> Dict[str, pd.Series]:
        """价格动量特征"""
        features = {}

        for period in [5, 10, 20, 60, 120]:
            features[f'momentum_{period}d'] = self.df['close'].pct_change(period) * 100
            features[f'momentum_std_{period}d'] = self.df['close'].pct_change().rolling(period).std() * np.sqrt(252) * 100

        return features

    def volume_features(self) -> Dict[str, pd.Series]:
        """成交量特征"""
        features = {}

        for period in [5, 10, 20, 60]:
            features[f'volume_mean_{period}d'] = self.df['volume'].rolling(period).mean()
            features[f'volume_std_{period}d'] = self.df['volume'].rolling(period).std()
            features[f'volume_change_{period}d'] = self.df['volume'].pct_change(period) * 100

        features['volume_price_corr'] = self.df['volume'].pct_change().rolling(20).corr(self.df['close'].pct_change())
        features['volume_momentum'] = self.df['volume'].pct_change(20) / (self.df['volume'].pct_change(60) + 1e-8)

        return features

    def volatility_features(self) -> Dict[str, pd.Series]:
        """波动率特征"""
        features = {}

        for period in [5, 10, 20, 60]:
            returns = self.df['close'].pct_change()
            features[f'volatility_{period}d'] = returns.rolling(period).std() * np.sqrt(252) * 100
            features[f'volatility_ewm_{period}d'] = returns.ewm(span=period).std() * np.sqrt(252) * 100

        features['volatility_ratio'] = features['volatility_10d'] / (features['volatility_60d'] + 1e-8)
        features['volatility_skew'] = self.df['close'].pct_change().rolling(20).skew()
        features['volatility_kurt'] = self.df['close'].pct_change().rolling(20).kurt()

        return features

    def technical_features(self) -> Dict[str, pd.Series]:
        """高级技术指标特征"""
        features = {}

        # RSI 衍生特征
        rsi = ta.rsi(self.df['close'])
        features['rsi_14'] = rsi
        features['rsi_7'] = ta.rsi(self.df['close'], length=7)
        features['rsi_21'] = ta.rsi(self.df['close'], length=21)
        features['rsi_momentum'] = rsi.pct_change(10)
        features['rsi_oversold'] = (rsi < 30).astype(int)
        features['rsi_overbought'] = (rsi > 70).astype(int)

        # MACD 衍生特征
        macd = ta.macd(self.df['close'])
        if macd is not None and len(macd.columns) >= 3:
            features['macd'] = macd.iloc[:, 0]
            features['macd_signal'] = macd.iloc[:, 1]
            features['macd_hist'] = macd.iloc[:, 2]
            features['macd_crossover'] = (macd.iloc[:, 0] > macd.iloc[:, 1]).astype(int)

        # Bollinger Bands 衍生特征
        bb = ta.bbands(self.df['close'])
        if bb is not None and len(bb.columns) >= 3:
            features['bb_upper'] = bb.iloc[:, 0]
            features['bb_middle'] = bb.iloc[:, 1]
            features['bb_lower'] = bb.iloc[:, 2]
            features['bb_width'] = (bb.iloc[:, 0] - bb.iloc[:, 2]) / bb.iloc[:, 1]
            features['bb_position'] = (self.df['close'] - bb.iloc[:, 2]) / (bb.iloc[:, 0] - bb.iloc[:, 2] + 1e-8)

        return features

    def trend_features(self) -> Dict[str, pd.Series]:
        """趋势特征"""
        features = {}

        # 移动平均交叉
        sma5 = ta.sma(self.df['close'], length=5)
        sma20 = ta.sma(self.df['close'], length=20)
        features['sma_crossover'] = (sma5 > sma20).astype(int)
        features['ema_crossover'] = (ta.ema(self.df['close'], length=5) > ta.ema(self.df['close'], length=20)).astype(int)

        # 趋势强度
        features['trend_strength'] = self.df['close'] / ta.sma(self.df['close'], length=20) - 1
        features['trend_acceleration'] = self.df['close'].diff(10) / (self.df['close'].diff(5) + 1e-8)

        # 支持和阻力
        features['support_level'] = self.df['low'].rolling(20).min()
        features['resistance_level'] = self.df['high'].rolling(20).max()
        features['price_to_support'] = self.df['close'] / features['support_level']
        features['price_to_resistance'] = self.df['close'] / features['resistance_level']

        return features

    def compute_ml_factors(self) -> Dict[str, pd.Series]:
        """计算所有机器学习因子"""
        features = {}

        features.update(self.price_momentum_features())
        features.update(self.volume_features())
        features.update(self.volatility_features())
        features.update(self.technical_features())
        features.update(self.trend_features())

        return {k: v for k, v in features.items() if v is not None and len(v) > 0}

    # ==================== 新增: 高级因子组合 (20个) ====================

    def smart_beta_factor(self) -> pd.Series:
        """智能贝塔因子"""
        momentum = self.df['close'].pct_change(20)
        volatility = self.df['close'].pct_change().rolling(20).std()
        return momentum / (volatility + 1e-8)

    def quality_minus_junk(self) -> pd.Series:
        """质量减垃圾因子"""
        quality = self.df['close'].pct_change(20) / (self.df['close'].pct_change(60) + 1e-8)
        junk = self.df['volume'].pct_change(20) / (self.df['volume'].pct_change(60) + 1e-8)
        return quality - junk

    def low_volatility_high_yield(self) -> pd.Series:
        """低波动高收益因子"""
        volatility = self.df['close'].pct_change().rolling(20).std()
        yield_proxy = self.dividend_yield()
        return yield_proxy / (volatility + 1e-8)

    def momentum_volatility_ratio(self) -> pd.Series:
        """动量波动率比"""
        momentum = self.df['close'].pct_change(20)
        volatility = self.df['close'].pct_change().rolling(20).std()
        return momentum / (volatility + 1e-8)

    def value_momentum_combo(self) -> pd.Series:
        """价值动量组合因子"""
        value = self.price_to_book()
        momentum = self.df['close'].pct_change(20)
        return value + momentum

    def risk_adjusted_momentum(self) -> pd.Series:
        """风险调整动量"""
        momentum = self.df['close'].pct_change(20)
        volatility = self.df['close'].pct_change().rolling(20).std()
        max_drawdown = (self.df['close'] / self.df['close'].rolling(20).max() - 1).rolling(20).min()
        return momentum / (volatility * (abs(max_drawdown) + 1e-8) + 1e-8)

    def earnings_quality(self) -> pd.Series:
        """盈利质量因子"""
        earnings = self.earnings_growth()
        cash_flow = self.df['volume'].pct_change(20)
        return earnings / (cash_flow + 1e-8)

    def valuation_spread(self) -> pd.Series:
        """估值价差因子"""
        pe = self.price_to_earnings()
        ps = self.price_to_sales()
        pb = self.price_to_book()
        return (pe + ps + pb) / 3

    def liquidity_factor(self) -> pd.Series:
        """流动性因子"""
        return self.df['volume'] * self.df['close']

    def size_factor(self) -> pd.Series:
        """规模因子"""
        return np.log(self.df['volume'] * self.df['close'])

    def growth_factor(self) -> pd.Series:
        """成长因子"""
        earnings_growth = self.earnings_growth()
        sales_growth = self.sales_growth()
        return (earnings_growth + sales_growth) / 2

    def profitability_factor(self) -> pd.Series:
        """盈利能力因子"""
        roe = self.return_on_equity()
        roa = self.return_on_assets()
        margin = self.profit_margin()
        return (roe + roa + margin) / 3

    def leverage_factor(self) -> pd.Series:
        """杠杆因子"""
        return self.debt_to_equity()

    def payout_factor(self) -> pd.Series:
        """股息支付因子"""
        return self.dividend_yield() / (self.df['close'].pct_change(20) + 1e-8)

    def investment_factor(self) -> pd.Series:
        """投资因子"""
        return self.df['volume'].pct_change(60)

    def accruals_factor(self) -> pd.Series:
        """应计项目因子"""
        return self.df['close'].pct_change(10) - self.df['close'].pct_change(20)

    def asset_turnover_factor(self) -> pd.Series:
        """资产周转因子"""
        return self.df['volume'] / (self.df['volume'].rolling(60).mean() + 1e-8)

    def inventory_turnover_factor(self) -> pd.Series:
        """存货周转因子"""
        return self.df['close'] / (self.df['close'].rolling(60).mean() + 1e-8)

    def receivables_turnover_factor(self) -> pd.Series:
        """应收账款周转因子"""
        return self.df['volume'] / (self.df['close'].pct_change(60) + 1e-8)

    def payables_turnover_factor(self) -> pd.Series:
        """应付账款周转因子"""
        return self.df['volume'] / (self.df['close'].pct_change(30) + 1e-8)

    def compute_advanced_factors(self) -> Dict[str, pd.Series]:
        """计算所有高级因子组合"""
        factors = {}

        factors['smart_beta'] = self.smart_beta_factor()
        factors['quality_minus_junk'] = self.quality_minus_junk()
        factors['low_vol_high_yield'] = self.low_volatility_high_yield()
        factors['momentum_vol_ratio'] = self.momentum_volatility_ratio()
        factors['value_momentum'] = self.value_momentum_combo()
        factors['risk_adjusted_momentum'] = self.risk_adjusted_momentum()
        factors['earnings_quality'] = self.earnings_quality()
        factors['valuation_spread'] = self.valuation_spread()
        factors['liquidity'] = self.liquidity_factor()
        factors['size'] = self.size_factor()
        factors['growth'] = self.growth_factor()
        factors['profitability'] = self.profitability_factor()
        factors['leverage'] = self.leverage_factor()
        factors['payout'] = self.payout_factor()
        factors['investment'] = self.investment_factor()
        factors['accruals'] = self.accruals_factor()
        factors['asset_turnover'] = self.asset_turnover_factor()
        factors['inventory_turnover'] = self.inventory_turnover_factor()
        factors['receivables_turnover'] = self.receivables_turnover_factor()
        factors['payables_turnover'] = self.payables_turnover_factor()

        return {k: v for k, v in factors.items() if v is not None and len(v) > 0}

    # ==================== 新增: 完整因子计算方法 ====================

    def compute_all_enhanced_factors(self) -> Dict[str, pd.Series]:
        """计算所有增强因子"""
        factors = {}

        # 基本面因子
        factors.update(self.compute_fundamental_factors())

        # 机器学习因子
        factors.update(self.compute_ml_factors())

        # 高级因子组合
        factors.update(self.compute_advanced_factors())

        return factors

    def compute_all_factors(self) -> Dict[str, pd.Series]:
        """计算所有因子（包含原Alpha158因子）"""
        factors = {}

        # 原Alpha158因子
        factors.update(self.compute_batch1())
        factors.update(self.compute_batch2())
        factors.update(self.compute_batch3())
        factors.update(self.compute_batch4())
        factors.update(self.compute_batch5())

        # 新增增强因子
        factors.update(self.compute_all_enhanced_factors())

        return {k: v for k, v in factors.items() if v is not None and len(v) > 0}

    # ==================== 因子质量评估 ====================

    def assess_factor_quality(self, factor: pd.Series) -> Dict[str, float]:
        """评估因子质量"""
        # 计算因子与未来收益的相关性
        future_returns = self.df['close'].pct_change(20).shift(-20)
        corr = factor.dropna().corr(future_returns[factor.dropna().index])

        # 计算因子区分度
        factor_quantiles = pd.qcut(factor.dropna(), 5, labels=False)
        quantile_returns = []
        for q in range(5):
            returns = future_returns[factor.dropna().index][factor_quantiles == q]
            quantile_returns.append(returns.mean())
        spread = quantile_returns[-1] - quantile_returns[0]

        # 计算因子稳定性
        stability = factor.rolling(60).corr(factor.shift(60)).mean()

        return {
            'correlation': corr,
            'spread': spread,
            'stability': stability,
            'quality_score': (abs(corr) + abs(spread) + abs(stability)) / 3
        }

    def evaluate_all_factors(self) -> Dict[str, Dict[str, float]]:
        """评估所有因子质量"""
        all_factors = self.compute_all_factors()
        evaluations = {}

        for name, factor in all_factors.items():
            if len(factor.dropna()) > 100:
                evaluations[name] = self.assess_factor_quality(factor)

        return evaluations

    def get_top_factors(self, n: int = 50, metric: str = 'quality_score') -> List[str]:
        """获取质量最高的因子"""
        evaluations = self.evaluate_all_factors()
        sorted_factors = sorted(evaluations.items(), key=lambda x: x[1][metric], reverse=True)
        return [name for name, score in sorted_factors[:n]]


# 使用示例
if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta

    print("测试 Alpha158Enhanced 因子库...")

    # 创建测试数据
    dates = pd.date_range(start='2020-01-01', end='2024-12-31', freq='D')
    price = 100
    prices = []

    for date in dates:
        price += np.random.randn() * 2
        prices.append(price)

    test_data = pd.DataFrame({
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, len(dates))
    }, index=dates)

    # 添加其他OHLC数据（填充缺失列）
    test_data['open'] = test_data['close'] + np.random.randn(len(dates)) * 1
    test_data['high'] = test_data['close'] + np.random.randn(len(dates)) * 3
    test_data['low'] = test_data['close'] - np.random.randn(len(dates)) * 3

    print(f"测试数据点数: {len(test_data)}")

    # 创建因子计算器实例
    alpha = Alpha158Enhanced(test_data)

    # 测试因子计算
    print("\n1. 测试增强因子计算:")
    fundamental_factors = alpha.compute_fundamental_factors()
    print(f"   基本面因子数量: {len(fundamental_factors)}")

    ml_factors = alpha.compute_ml_factors()
    print(f"   机器学习因子数量: {len(ml_factors)}")

    advanced_factors = alpha.compute_advanced_factors()
    print(f"   高级因子组合数量: {len(advanced_factors)}")

    all_factors = alpha.compute_all_factors()
    print(f"   总因子数量: {len(all_factors)}")

    # 测试因子评估
    print("\n2. 测试因子评估:")
    evaluations = alpha.evaluate_all_factors()
    print(f"   有效因子评估: {len(evaluations)}")

    # 获取高质量因子
    top_factors = alpha.get_top_factors(10)
    print(f"   前10个高质量因子:")
    for i, factor in enumerate(top_factors, 1):
        score = evaluations[factor]['quality_score']
        print(f"   {i}. {factor} ({score:.4f})")

    print("\n✅ Alpha158Enhanced 因子库测试完成!")
