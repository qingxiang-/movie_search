#!/usr/bin/env python3
"""
Alpha158 排名法多因子选股系统 - 美股TOP 100科技股
✅ 基于因子得分的传统量化方法
✅ 支持邮件发送
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

# ============================================
# TOP 100+ 美股科技股候选池
# ============================================
TECH_100 = [
    # === 巨头 (Mega Cap) ===
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'GOOG', 'AMZN', 'META', 'TSLA',
    'AVGO', 'AMD', 'QCOM', 'ORCL', 'ADBE', 'CRM', 'NFLX',
    
    # === 半导体 (Semiconductors) ===
    'TSM', 'ASML', 'TXN', 'AMAT', 'MU', 'LRCX', 'KLAC', 'MRVL',
    'AMKR', 'MPWR', 'MCHP', 'MXIM', 'ON', 'FSLR', 'SEDG', 'ENPH',
    'RUN', 'TER', 'KEYS', 'CDNS', 'SNPS', 'HIMX', 'CEVA', 'SLAB',
    'DIOD', 'AXTI', 'FORM', 'MXL', 'SIMO', 'DQ', 'LSCC',
    
    # === 软件 (Software) ===
    'NOW', 'WDAY', 'ZM', 'DDOG', 'CRWD', 'ZS', 'OKTA', 'PANW',
    'SPLK', 'MDB', 'ESTC', 'HUBS', 'SNOW', 'PLTR', 'DT', 'GDDY',
    'ANSS', 'VMW', 'INTU', 'ZEN', 'COUP', 'VEEV', 'APP', 'CFLT',
    'FROG', 'PATH', 'TEAM', 'SVM', 'U',
    
    # === 互联网/电商 (Internet) ===
    'SHOP', 'SQ', 'PINS', 'SNAP', 'TTD', 'RBLX', 'HOOD', 'COIN',
    'MSTR', 'BIDU', 'DIS', 'CHTR', 'TTWO', 'EA', 'ATVI',
    
    # === 硬件/设备 (Hardware) ===
    'DELL', 'HPQ', 'HPE', 'IBM', 'WDC', 'STX', 'NTAP', 'NET',
    'CAMT', 'VSAT', 'SSYS', 'COHR',
    
    # === 网络安全 (Cybersecurity) ===
    'NICE', 'FTNT', 'CHK', 'S', 'TENB', 'CYBR',
    
    # === 数据/IT服务 (Data/IT) ===
    'ADP', 'PAYX', 'WEX', 'GPN', 'FIS', 'FISV', 'CME', 'MCO',
    'SPGI', 'NTRS', 'MSCI', 'BLK', 'AXP', 'V', 'MA',
    
    # === 通信 (Telecom) ===
    'TMUS', 'VZ', 'NOK', 'CSCO', 'ERIC', 'CMCSA',
    
    # === 金融科技 (Fintech) ===
    'UPST', 'SOFI', 'PYPL', 'AFRM',
]

# 去重
TECH_100 = list(dict.fromkeys(TECH_100))

# 因子配置：因子名 -> 权重
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
            values = values.fillna(values.median())
            z_values = zscore_normalize(values)
            scores += z_values * weight
    
    return scores

def send_email_report(df_result: pd.DataFrame, top10: list):
    """发送邮件报告"""
    try:
        sys.path.insert(0, '/Users/wangqingxiang/source/movie_search')
        from utils.email_sender import EmailSender
        
        # 生成HTML报告
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
                th {{ background-color: #3498db; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .buy {{ color: green; font-weight: bold; }}
                .avoid {{ color: red; font-weight: bold; }}
                .summary {{ background-color: #ecf0f1; padding: 15px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>📊 Alpha158 多因子选股报告</h1>
            <p>生成时间: {timestamp}</p>
            <p>候选池: {len(df_result)} 只美股科技股</p>
            
            <div class="summary">
                <h3>🏆 TOP 10 推荐</h3>
                <table>
                    <tr><th>排名</th><th>代码</th><th>综合得分</th><th>6月动量</th><th>夏普</th><th>波动</th></tr>
        """
        
        for i, ticker in enumerate(top10):
            row = df_result.loc[ticker]
            mom = row.get('momentum_6m', row.get('momentum_3m', 0))
            sharpe = row.get('sharpe_ratio_20d', 0)
            vol = row.get('volatility_20d', 0)
            html += f"""
                    <tr>
                        <td>{i+1}</td>
                        <td class="buy">{ticker}</td>
                        <td>{row['score']:.3f}</td>
                        <td>{mom:.1f}%</td>
                        <td>{sharpe:.2f}</td>
                        <td>{vol:.2f}</td>
                    </tr>"""
        
        # TOP 3 vs 全市场对比
        top3 = df_result.head(3)
        all_mean = df_result.mean()
        
        html += f"""
                </table>
            </div>
            
            <h3>📈 TOP 3 vs 全市场</h3>
            <table>
                <tr><th>因子</th><th>TOP 3</th><th>全市场</th><th>差异</th></tr>
                <tr><td>6月动量</td><td>{top3['momentum_6m'].mean():.1f}%</td><td>{all_mean.get('momentum_6m', 0):.1f}%</td><td>↑{top3['momentum_6m'].mean() - all_mean.get('momentum_6m', 0):.1f}%</td></tr>
                <tr><td>夏普比率</td><td>{top3['sharpe_ratio_20d'].mean():.2f}</td><td>{all_mean.get('sharpe_ratio_20d', 0):.2f}</td><td>↑{top3['sharpe_ratio_20d'].mean() - all_mean.get('sharpe_20d', 0):.2f}</td></tr>
                <tr><td>趋势强度</td><td>{top3['trend_strength'].mean():.1f}</td><td>{all_mean.get('trend_strength', 0):.1f}</td><td>↑{top3['trend_strength'].mean() - all_mean.get('trend_strength', 0):.1f}</td></tr>
            </table>
            
            <h3>💰 投资建议</h3>
            <ul>
                <li><span class="buy">强烈买入 (TOP 3)</span>: {', '.join(top10[:3])}</li>
                <li><span class="buy">买入 (TOP 10)</span>: {', '.join(top10[:10])}</li>
                <li><span class="avoid">回避</span>: {', '.join(top10[-3:])}</li>
            </ul>
            
            <hr>
            <p><small>Generated by Alpha158 Ranking System</small></p>
        </body>
        </html>
        """
        
        # 发送邮件
        sender = EmailSender()
        if sender.client:
            subject = f"Alpha158 选股报告 - {datetime.now().strftime('%Y-%m-%d')}"
            sender.send_email(subject, html)
            print(f"\n✅ 邮件已发送")
        else:
            print(f"\n⚠️ 邮件客户端未初始化，仅保存HTML")
            
        return html
        
    except Exception as e:
        print(f"\n⚠️ 邮件发送失败: {e}")
        return None

def run_analysis(stock_pool: list = TECH_100, period_days: int = 365):
    """运行分析"""
    print("\n" + "="*80)
    print("🚀 Alpha158 多因子选股系统 - 美股TOP科技股")
    print("="*80)
    print(f"候选池: {len(stock_pool)} 只股票")
    
    # 时间范围
    period2 = int(datetime.now().timestamp())
    period1 = int((datetime.now() - timedelta(days=period_days)).timestamp())
    
    # 获取数据
    print(f"\n📥 获取数据 ({period_days}天)...")
    all_factors = {}
    
    for i, ticker in enumerate(stock_pool):
        print(f"   {i+1}/{len(stock_pool)} {ticker}...", end=" ", flush=True)
        df = get_stock_data(ticker, period1, period2)
        if df is not None and len(df) > 100:
            factors = calculate_factors(df)
            if factors:
                all_factors[ticker] = factors
                print(f"✓ {len(factors)}因子")
            else:
                print("❌ 因子计算失败")
        else:
            print(f"❌ 数据不足")
    
    if not all_factors:
        print("\n❌ 无有效数据")
        return None
    
    print(f"\n✅ 成功获取 {len(all_factors)}/{len(stock_pool)} 只股票数据")
    
    # 构建DataFrame
    df_factors = pd.DataFrame(all_factors).T
    print(f"特征数: {len(df_factors.columns)}")
    
    # 计算得分
    available_factors = [f for f in FACTOR_CONFIG.keys() if f in df_factors.columns]
    print(f"有效因子: {len(available_factors)}/{len(FACTOR_CONFIG)}")
    
    df_subset = df_factors[available_factors].copy()
    scores = calculate_composite_score(df_subset, FACTOR_CONFIG)
    
    df_result = df_factors.copy()
    df_result['score'] = scores
    df_result = df_result.sort_values('score', ascending=False)
    
    # 输出TOP 10
    print(f"\n" + "="*80)
    print("🏆 TOP 10 推荐股票")
    print("="*80)
    print(f"{'排名':<4} {'代码':<8} {'得分':<10} {'6月动量':<12} {'夏普_20d':<10} {'波动':<10}")
    print("-"*70)
    
    top10 = df_result.head(10).index.tolist()
    for i, ticker in enumerate(top10):
        row = df_result.loc[ticker]
        mom = row.get('momentum_6m', row.get('momentum_3m', 0))
        sharpe = row.get('sharpe_ratio_20d', 0)
        vol = row.get('volatility_20d', 0)
        print(f"{i+1:<4} {ticker:<8} {row['score']:<10.3f} {mom:<10.1f}% {sharpe:<10.2f} {vol:<10.2f}")
    
    # TOP 3 vs 全市场
    print(f"\n📈 TOP 3 vs 全市场因子对比")
    top3 = df_result.head(3)
    all_mean = df_result.mean()
    
    for factor in ['momentum_6m', 'sharpe_ratio_20d', 'trend_strength']:
        if factor in top3.columns:
            t3 = top3[factor].mean()
            a = all_mean.get(factor, 0)
            diff = t3 - a
            print(f"   {factor}: TOP3={t3:.2f}, 全市场={a:.2f}, 差异={diff:+.2f}")
    
    # 保存结果
    df_result.to_csv('/Users/wangqingxiang/.openclaw/workspace/ranking_top100.csv')
    print(f"\n💾 结果已保存: ranking_top100.csv")
    
    # 发送邮件
    html = send_email_report(df_result, top10)
    if html:
        with open('/Users/wangqingxiang/.openclaw/workspace/ranking_report.html', 'w') as f:
            f.write(html)
        print(f"📧 邮件报告已保存: ranking_report.html")
    
    return df_result

if __name__ == "__main__":
    df_result = run_analysis()
