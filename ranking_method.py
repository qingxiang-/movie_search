#!/usr/bin/env python3
"""
Alpha158 排名法多因子选股系统
✅ 基于因子得分的传统量化方法
"""
import sys
sys.path.insert(0, '/Users/wangqingxiang/.openclaw/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# 候选股票池
TECH_STOCKS = [
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'GOOG', 'AMZN', 'META', 'TSLA',
    'AVGO', 'AMD', 'QCOM', 'AMAT', 'MU', 'LRCX', 'KLAC', 'MRVL',
    'ORCL', 'ADBE', 'CRM', 'NFLX'
]

# 因子配置：因子名 -> (权重, 排序方向)
# weight > 0: 越大越好
# weight < 0: 越小越好
FACTOR_CONFIG = {
    # 动量因子（正）
    'momentum_3m': 0.10,
    'momentum_6m': 0.15,
    'momentum_12m': 0.10,
    'return_20d': 0.05,
    'return_60d': 0.08,
    
    # 质量因子（正）
    'sharpe_ratio_20d': 0.10,
    'sharpe_ratio_60d': 0.08,
    'sortino_ratio_20d': 0.05,
    'calmar_ratio': 0.03,
    'win_rate_20d': 0.05,
    
    # 趋势因子（正）
    'trend_strength': 0.08,
    'alpha_composite': 0.05,
    'momentum_strength': 0.05,
    
    # 相对强度（正）
    'relative_strength_60d': 0.05,
    'dual_momentum': 0.03,
    
    # 低波动因子（负，越小越好）
    'volatility_20d': -0.05,
    'volatility_60d': -0.05,
    'max_drawdown_20d': -0.03,
    'drawdown_60d': -0.03,
    
    # 风险因子（负）
    'beta_60d': -0.02,
}

def get_stock_data(ticker: str, period1: int, period2: int) -> pd.DataFrame:
    """获取历史数据"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {
        'period1': period1,
        'period2': period2,
        'interval': '1d',
        'includePrePost': 'false',
        'events': 'history'
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        result = data['chart'].get('result')
        if not result:
            return None
        
        df = pd.DataFrame({
            'Open': result[0]['indicators']['quote'][0]['open'],
            'High': result[0]['indicators']['quote'][0]['high'],
            'Low': result[0]['indicators']['quote'][0]['low'],
            'Close': result[0]['indicators']['quote'][0]['close'],
            'Volume': result[0]['indicators']['quote'][0]['volume']
        }, index=pd.to_datetime(result[0]['timestamp'], unit='s'))
        
        return df.dropna()
    except:
        return None

def calculate_factors(df: pd.DataFrame) -> dict:
    """计算因子"""
    sys.path.insert(0, '/Users/wangqingxiang/.openclaw/workspace')
    from alpha158 import Alpha158
    
    try:
        alpha = Alpha158(df)
        all_factors = {**alpha.compute_batch1(), **alpha.compute_batch2(), 
                       **alpha.compute_batch3(), **alpha.compute_batch4(), 
                       **alpha.compute_batch5()}
        
        # 转换为小写
        factors = {}
        for name, series in all_factors.items():
            if hasattr(series, 'iloc') and len(series) > 0:
                val = series.iloc[-1]
                if pd.notna(val) and np.isfinite(val):
                    factors[name.lower()] = float(val)
        
        return factors
    except:
        return {}

def zscore_normalize(series: pd.Series) -> pd.Series:
    """Z-score标准化"""
    mean = series.mean()
    std = series.std()
    if std == 0:
        return pd.Series(0, index=series.index)
    return (series - mean) / std

def calculate_composite_score(df_factors: pd.DataFrame, config: dict) -> pd.Series:
    """计算综合得分"""
    scores = pd.Series(0.0, index=df_factors.index)
    
    for factor, weight in config.items():
        if factor in df_factors.columns:
            values = df_factors[factor].copy()
            # 处理缺失值
            values = values.fillna(values.median())
            
            # Z-score标准化
            z_values = zscore_normalize(values)
            
            # 加权
            scores += z_values * weight
    
    return scores

def rank_stocks(factors_dict: dict) -> pd.DataFrame:
    """排名选股"""
    print("\n" + "="*80)
    print("📊 排名法多因子选股")
    print("="*80)
    
    # 构建因子DataFrame
    df_factors = pd.DataFrame(factors_dict).T
    print(f"候选股票: {len(df_factors)} 只")
    
    # 检查有效因子
    available_factors = [f for f in FACTOR_CONFIG.keys() if f in df_factors.columns]
    print(f"有效因子: {len(available_factors)}/{len(FACTOR_CONFIG)}")
    
    # 计算综合得分
    df_subset = df_factors[available_factors].copy()
    scores = calculate_composite_score(df_subset, FACTOR_CONFIG)
    
    # 构建结果
    df_result = df_factors.copy()
    df_result['score'] = scores
    df_result = df_result.sort_values('score', ascending=False)
    
    # TOP 10
    print(f"\n🏆 TOP 10 推荐股票:")
    print("-"*70)
    print(f"{'排名':<4} {'代码':<8} {'综合得分':<10} {'动量_6m':<10} {'夏普_20d':<10} {'波动_20d':<10}")
    print("-"*70)
    
    for i, (ticker, row) in enumerate(df_result.head(10).iterrows()):
        mom = row.get('momentum_6m', 0)
        sharpe = row.get('sharpe_ratio_20d', 0)
        vol = row.get('volatility_20d', 0)
        print(f"{i+1:<4} {ticker:<8} {row['score']:<10.3f} {mom:<10.1f}% {sharpe:<10.2f} {vol:<10.2f}")
    
    return df_result

def backtest_ranking(df_result: pd.DataFrame, holding_period: int = 20) -> dict:
    """回测排名法策略"""
    print("\n" + "="*80)
    print("📈 回测排名法策略")
    print("="*80)
    
    # 使用最近的因子数据获取未来收益
    # 这里简化处理：直接用因子数据中的趋势作为代理
    df = df_result.copy()
    
    # 策略1: 买入TOP 5
    df['top5'] = df['score'].rank(ascending=False) <= 5
    
    # 策略2: 买入TOP 3
    df['top3'] = df['score'].rank(ascending=False) <= 3
    
    # 简单绩效指标
    print(f"\n策略绩效 (基于因子得分):")
    print("-"*50)
    
    top5_stocks = df[df['top5']].index.tolist()
    top3_stocks = df[df['top3']].index.tolist()
    
    # 计算组合得分
    top5_avg_score = df[df['top5']]['score'].mean()
    top3_avg_score = df[df['top3']]['score'].mean()
    all_avg_score = df['score'].mean()
    
    # 得分分布
    print(f"\n得分分布:")
    print(f"   TOP5 平均得分: {top5_avg_score:.3f}")
    print(f"   TOP3 平均得分: {top3_avg_score:.3f}")
    print(f"   全市场平均: {all_avg_score:.3f}")
    
    # 因子分布分析
    print(f"\nTOP5 因子特征:")
    top5_factors = df[df['top5']][list(FACTOR_CONFIG.keys())[:10]].mean()
    all_factors = df[list(FACTOR_CONFIG.keys())[:10]].mean()
    
    print(f"{'因子':<20} {'TOP5均值':<12} {'全市场':<12} {'差异':<10}")
    print("-"*55)
    for factor in list(FACTOR_CONFIG.keys())[:10]:
        if factor in top5_factors.index:
            t5 = top5_factors[factor]
            a = all_factors[factor]
            diff = t5 - a
            direction = "↑" if diff > 0 else "↓"
            print(f"{factor:<20} {t5:<12.4f} {a:<12.4f} {direction}{abs(diff):.4f}")
    
    return {
        'top5': top5_stocks,
        'top3': top3_stocks,
        'df': df
    }

def generate_signals(df_result: pd.DataFrame) -> pd.DataFrame:
    """生成交易信号"""
    print("\n" + "="*80)
    print("💰 交易信号")
    print("="*80)
    
    df = df_result.copy()
    df['rank'] = df['score'].rank(ascending=False)
    
    # 信号强度
    df['signal'] = '持有'
    df.loc[df['rank'] <= 3, 'signal'] = '强烈买入'
    df.loc[(df['rank'] > 3) & (df['rank'] <= 5), 'signal'] = '买入'
    df.loc[(df['rank'] > 10) & (df['rank'] <= 15), 'signal'] = '观望'
    df.loc[df['rank'] > 15, 'signal'] = '回避'
    
    # 置信度
    max_score = df['score'].max()
    min_score = df['score'].min()
    score_range = max_score - min_score
    
    if score_range > 0:
        df['confidence'] = ((df['score'] - min_score) / score_range * 100).round(1)
    else:
        df['confidence'] = 50.0
    
    print(f"\n信号汇总:")
    print("-"*70)
    print(f"{'代码':<8} {'得分':<10} {'排名':<6} {'信号':<12} {'置信度':<8} {'动量_6m':<10}")
    print("-"*70)
    
    for ticker, row in df.iterrows():
        mom = row.get('momentum_6m', 'N/A')
        mom_str = f"{mom:.1f}%" if isinstance(mom, (int, float)) else str(mom)
        print(f"{ticker:<8} {row['score']:<10.3f} {row['rank']:<6.0f} {row['signal']:<12} {row['confidence']:<8.1f}% {mom_str}")
    
    return df

def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 Alpha158 排名法多因子选股系统")
    print("="*80)
    
    # 时间范围
    period1 = 1609459200  # 2021-01-01
    period2 = 1735689600  # 2025-01-02
    
    # 获取所有股票数据
    print("\n📥 获取股票数据...")
    all_factors = {}
    
    for ticker in TECH_STOCKS:
        print(f"   {ticker}...", end=" ", flush=True)
        df = get_stock_data(ticker, period1, period2)
        if df is not None and len(df) > 200:
            factors = calculate_factors(df)
            if factors:
                all_factors[ticker] = factors
                print(f"✓ {len(factors)} 因子")
            else:
                print("❌ 因子计算失败")
        else:
            print("❌ 数据不足")
    
    if not all_factors:
        print("\n❌ 无有效数据")
        return
    
    print(f"\n✅ 成功获取 {len(all_factors)}/{len(TECH_STOCKS)} 只股票数据")
    
    # 排名选股
    df_result = rank_stocks(all_factors)
    
    # 回测
    bt_result = backtest_ranking(df_result)
    
    # 生成信号
    signals = generate_signals(df_result)
    
    # 保存结果
    df_result.to_csv('/Users/wangqingxiang/.openclaw/workspace/ranking_top20.csv')
    signals.to_csv('/Users/wangqingxiang/.openclaw/workspace/ranking_signals.csv')
    
    print("\n" + "="*80)
    print("✅ 完成!")
    print("="*80)
    print(f"\n💾 结果已保存:")
    print(f"   ranking_top20.csv - TOP20排名")
    print(f"   ranking_signals.csv - 完整信号")
    
    return df_result, signals

if __name__ == "__main__":
    df_result, signals = main()
