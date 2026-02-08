#!/usr/bin/env python3
"""
Alpha158 机器学习数据集构建 - 修复版
✅ 正确匹配所有因子名称
"""
import sys
sys.path.insert(0, '/Users/wangqingxiang/.openclaw/workspace')

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from alpha158 import Alpha158
import warnings
warnings.filterwarnings('ignore')

# 科技股池
TECH_STOCKS = [
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'GOOG', 'AMZN', 'META', 'TSLA',
    'AVGO', 'AMD', 'QCOM', 'AMAT', 'MU', 'LRCX', 'KLAC', 'MRVL',
    'ORCL', 'ADBE', 'CRM', 'NFLX'
]

# 训练/测试时间
TRAIN_END = datetime(2024, 6, 30)
TEST_END = datetime(2024, 12, 31)

def get_stock_data(ticker: str) -> pd.DataFrame:
    """获取历史数据"""
    period1 = 1609459200  # 2021-01-01
    period2 = 1735689600  # 2025-01-02
    
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
        resp = requests.get(url, params=params, headers=headers, timeout=15)
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

def calculate_all_factors(df: pd.DataFrame) -> dict:
    """计算所有因子并规范化名称"""
    try:
        alpha = Alpha158(df)
        all_factors = {**alpha.compute_batch1(), **alpha.compute_batch2(), 
                       **alpha.compute_batch3(), **alpha.compute_batch4(), 
                       **alpha.compute_batch5()}
        
        result = {}
        for name, series in all_factors.items():
            if hasattr(series, 'iloc') and len(series) > 0:
                val = series.iloc[-1]
                if pd.notna(val) and np.isfinite(val):
                    # 规范化名称为小写
                    normalized = name.lower()
                    result[normalized] = float(val)
        
        return result
    except:
        return {}

def find_nearest_date(df: pd.DataFrame, target: datetime) -> datetime:
    """找到最接近的目标日期"""
    if target in df.index:
        return target
    
    idx = df.index[df.index >= target]
    if len(idx) > 0:
        return idx[0]
    
    return df.index[-1]

def get_sample_dates(df: pd.DataFrame) -> dict:
    """获取采样日期"""
    dates = {'train': [], 'test': []}
    
    quarters = [
        (2023, 3, 31), (2023, 6, 30), (2023, 9, 30), (2023, 12, 31),
        (2024, 3, 31), (2024, 6, 30), (2024, 9, 30), (2024, 12, 31)
    ]
    
    for y, m, d in quarters:
        date = datetime(y, m, d)
        actual = find_nearest_date(df, date)
        
        if actual <= TRAIN_END:
            dates['train'].append(actual)
        elif actual <= TEST_END:
            dates['test'].append(actual)
    
    return dates

def build_sample(ticker: str, df: pd.DataFrame, sample_date: datetime) -> dict:
    """构建样本"""
    df_hist = df[df.index <= sample_date].copy()
    if len(df_hist) < 60:
        return None
    
    # 计算所有因子
    factors = calculate_all_factors(df_hist)
    if not factors:
        return None
    
    # 计算未来收益
    future_start = sample_date + timedelta(days=1)
    future_end = sample_date + timedelta(days=21)
    df_future = df[(df.index >= future_start) & (df.index < future_end)]
    
    if len(df_future) < 10:
        return None
    
    price_now = df.loc[sample_date, 'Close']
    price_future = df_future['Close'].iloc[-1]
    future_return = (price_future - price_now) / price_now
    
    return {
        'ticker': ticker,
        'date': sample_date.strftime('%Y-%m-%d'),
        'price': price_now,
        'future_return_20d': future_return,
        'label': 1 if future_return > 0.02 else (-1 if future_return < -0.02 else 0),
        **factors
    }

def main():
    print("\n" + "="*80)
    print("📊 Alpha158 机器学习数据集构建 - 修复版")
    print("   股票: 20只 | 采样: 季度 | 因子: 所有有效因子")
    print("="*80)
    
    all_samples = []
    
    for i, ticker in enumerate(TECH_STOCKS):
        print(f"\n[{i+1}/{len(TECH_STOCKS)}] 📥 {ticker}...", end=" ", flush=True)
        
        df = get_stock_data(ticker)
        if df is None or len(df) < 200:
            print(f"❌ 数据不足")
            continue
        
        print(f"✓ {len(df)}天 ", end="")
        
        dates = get_sample_dates(df)
        sample_count = 0
        
        for date in dates['train'] + dates['test']:
            sample = build_sample(ticker, df, date)
            if sample:
                sample['dataset'] = 'train' if date <= TRAIN_END else 'test'
                all_samples.append(sample)
                sample_count += 1
        
        print(f"{sample_count}样本")
    
    if not all_samples:
        print("\n❌ 无有效样本")
        return
    
    df_all = pd.DataFrame(all_samples)
    
    # 统计
    print(f"\n\n" + "="*80)
    print("📊 数据集统计")
    print("="*80)
    print(f"   总样本: {len(df_all)}")
    print(f"   训练集: {len(df_all[df_all['dataset']=='train'])}")
    print(f"   测试集: {len(df_all[df_all['dataset']=='test'])}")
    
    feature_cols = [c for c in df_all.columns if c not in 
                   ['ticker','date','price','future_return_20d','label','dataset']]
    print(f"   特征数: {len(feature_cols)}")
    
    # 标签分布
    print(f"\n🏷️ 标签分布:")
    for ds in ['train', 'test']:
        subset = df_all[df_all['dataset']==ds]
        counts = subset['label'].value_counts().sort_index()
        print(f"   {ds}: 上涨={counts.get(1,0)}, 震荡={counts.get(0,0)}, 下跌={counts.get(-1,0)}")
    
    # 目标收益统计
    print(f"\n📈 未来20日收益 (%):")
    for ds in ['train', 'test']:
        subset = df_all[df_all['dataset']==ds]
        print(f"   {ds}: 均值={subset['future_return_20d'].mean()*100:.2f}, 标准差={subset['future_return_20d'].std()*100:.2f}")
    
    # 特征示例
    print(f"\n🔢 特征示例 (前10个):")
    for feat in feature_cols[:10]:
        vals = df_all[feat].dropna()
        if len(vals) > 0:
            print(f"   {feat}: 均值={vals.mean():.4f}, 范围=[{vals.min():.4f}, {vals.max():.4f}]")
    
    # 保存
    df_all.to_csv('/Users/wangqingxiang/.openclaw/workspace/ml_dataset_full.csv', index=False)
    df_all[df_all['dataset']=='train'].to_csv('/Users/wangqingxiang/.openclaw/workspace/ml_dataset_train.csv', index=False)
    df_all[df_all['dataset']=='test'].to_csv('/Users/wangqingxiang/.openclaw/workspace/ml_dataset_test.csv', index=False)
    
    with open('/Users/wangqingxiang/.openclaw/workspace/ml_features.txt', 'w') as f:
        for feat in feature_cols:
            f.write(f"{feat}\n")
    
    print(f"\n💾 已保存:")
    print(f"   ml_dataset_full.csv")
    print(f"   ml_dataset_train.csv")
    print(f"   ml_dataset_test.csv")
    print(f"   ml_features.txt ({len(feature_cols)} 特征)")

if __name__ == "__main__":
    main()
