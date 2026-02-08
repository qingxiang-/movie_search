#!/usr/bin/env python3
"""
Alpha158 排名法多因子选股系统 - 使用全部87个因子
✅ 基于因子得分的传统量化方法
✅ 支持邮件发送
"""
import sys
sys.path.insert(0, '/Users/wangqingxiang/.openclaw/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import warnings
warnings.filterwarnings('ignore')

# ============================================
# TOP 100+ 美股科技股候选池
# ============================================
TECH_100 = [
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'GOOG', 'AMZN', 'META', 'TSLA',
    'AVGO', 'AMD', 'QCOM', 'ORCL', 'ADBE', 'CRM', 'NFLX',
    'TSM', 'ASML', 'TXN', 'AMAT', 'MU', 'LRCX', 'KLAC', 'MRVL',
    'AMKR', 'MPWR', 'MCHP', 'MXIM', 'ON', 'FSLR', 'SEDG', 'ENPH',
    'RUN', 'TER', 'KEYS', 'CDNS', 'SNPS', 'HIMX', 'CEVA', 'SLAB',
    'DIOD', 'AXTI', 'FORM', 'MXL', 'SIMO', 'DQ', 'LSCC',
    'NOW', 'WDAY', 'ZM', 'DDOG', 'CRWD', 'ZS', 'OKTA', 'PANW',
    'MDB', 'ESTC', 'HUBS', 'SNOW', 'PLTR', 'DT', 'GDDY',
    'ANSS', 'VMW', 'INTU', 'ZEN', 'COUP', 'VEEV', 'APP', 'CFLT',
    'FROG', 'PATH', 'TEAM', 'SVM', 'U',
    'SHOP', 'SQ', 'PINS', 'SNAP', 'TTD', 'RBLX', 'HOOD', 'COIN',
    'MSTR', 'BIDU', 'DIS', 'CHTR', 'TTWO', 'EA', 'ATVI',
    'DELL', 'HPQ', 'HPE', 'IBM', 'WDC', 'STX', 'NTAP', 'NET',
    'CAMT', 'VSAT', 'SSYS', 'COHR',
    'NICE', 'FTNT', 'CHK', 'S', 'TENB', 'CYBR',
    'ADP', 'PAYX', 'WEX', 'GPN', 'FIS', 'FISV', 'CME', 'MCO',
    'SPGI', 'NTRS', 'MSCI', 'BLK', 'AXP', 'V', 'MA',
    'TMUS', 'VZ', 'NOK', 'CSCO', 'ERIC', 'CMCSA',
    'UPST', 'SOFI', 'PYPL', 'AFRM',
]
TECH_100 = list(dict.fromkeys(TECH_100))

# ============================================
# 自动因子权重配置（基于因子语义）
# ============================================
# 因子类型: (前缀匹配, 权重方向, 默认权重)
FACTOR_TYPES = [
    # 正向因子（越大越好）
    ('momentum_', 1, 0.10),
    ('return_', 1, 0.05),
    ('sharpe_', 1, 0.10),
    ('sortino_', 1, 0.08),
    ('calmar_', 1, 0.05),
    ('treynor_', 1, 0.05),
    ('win_rate_', 1, 0.05),
    ('alpha_', 1, 0.08),
    ('trend_strength', 1, 0.08),
    ('momentum_strength', 1, 0.05),
    ('mean_reversion_strength', 1, 0.03),
    ('dual_momentum', 1, 0.03),
    ('relative_strength', 1, 0.05),
    ('relative_volume', 1, 0.02),
    ('vwap_deviation', 1, 0.03),
    ('volume_trend', 1, 0.02),
    ('volume_price_trend', 1, 0.02),
    ('book_to_price', 1, 0.02),
    ('roe_proxy', 1, 0.03),
    ('operating_margin_proxy', 1, 0.02),
    ('asset_turnover_proxy', 1, 0.02),
    ('dividend_yield_proxy', 1, 0.02),
    ('debt_to_equity_proxy', 1, 0.02),
    ('earnings_momentum', 1, 0.03),
    ('quality_factor', 1, 0.05),
    ('liquidity_factor', 1, 0.02),
    ('size_factor', 1, 0.01),
    ('value_factor', 1, 0.02),
    ('low_volatility_factor', 1, 0.05),
    ('price_acceleration', 1, 0.03),

    # 负向因子（越小越好）
    ('volatility_', -1, 0.05),
    ('drawdown_', -1, 0.03),
    ('max_drawdown', -1, 0.03),
    ('realized_volatility', -1, 0.05),
    ('volatility_index', -1, 0.03),
    ('trend_volatility_index', -1, 0.03),
    ('z_score_', -1, 0.02),
    ('z_score_returns', -1, 0.02),
    ('autocorr_', -1, 0.02),
    ('rolling_corr', -1, 0.02),
    ('serial_corr', -1, 0.02),
    ('price_volume_corr', -1, 0.02),
    ('price_vol_corr', -1, 0.02),
    ('tail_ratio', -1, 0.02),
    ('gain_loss_ratio', -1, 0.02),
    ('profit_loss_ratio', -1, 0.02),
    ('omega_ratio', -1, 0.02),
    ('sterling_ratio', -1, 0.02),
    ('information_ratio', -1, 0.02),
    ('loss_aversion', -1, 0.02),
    ('market_regime', 0, 0.01),  # 中性
    ('volatility_regime', 0, 0.01),  # 中性
    ('volatility_breakout', 1, 0.03),  # 正向
    ('mean_reversion_signal', 1, 0.02),  # 正向
]

def get_factor_weight(factor_name: str, available_factors: list) -> float:
    """根据因子名称自动确定权重"""
    for prefix, direction, default_weight in FACTOR_TYPES:
        if factor_name.startswith(prefix):
            return direction * default_weight
    # 默认给一个小权重
    return 0.01

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

def calculate_composite_score(df_factors: pd.DataFrame, factor_weights: dict) -> pd.Series:
    """计算综合得分"""
    scores = pd.Series(0.0, index=df_factors.index)

    for factor, weight in factor_weights.items():
        if factor in df_factors.columns:
            values = df_factors[factor].copy()
            values = values.fillna(values.median())
            z_values = zscore_normalize(values)
            scores += z_values * weight

    return scores

def send_email_report(df_result: pd.DataFrame, top20: list):
    """发送邮件报告"""
    try:
        sys.path.insert(0, '/Users/wangqingxiang/source/movie_search')
        from utils.email_sender import EmailSender

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
                .summary {{ background-color: #ecf0f1; padding: 15px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>📊 Alpha158 多因子选股报告 (147因子)</h1>
            <p>生成时间: {timestamp}</p>
            <p>候选池: {len(df_result)} 只美股科技股 | 因子数: {len(df_result.columns)-1}</p>

            <div class="summary">
                <h3>🏆 TOP 20 推荐</h3>
                <table>
                    <tr><th>排名</th><th>代码</th><th>综合得分</th><th>6月动量</th><th>夏普</th><th>波动</th></tr>
        """

        for i, ticker in enumerate(top20):
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

        html += f"""
                </table>
            </div>
            <hr>
            <p><small>Generated by Alpha158 Ranking System (147 factors)</small></p>
        </body>
        </html>
        """

        sender = EmailSender()
        if sender.client:
            sender.send_email_report(html, f"Alpha158 选股报告 - TOP 20 - {datetime.now().strftime('%Y-%m-%d')}")
        else:
            print(f"\n⚠️ 邮件客户端未初始化，请检查 .env 配置")

        return html

    except Exception as e:
        print(f"\n⚠️ 邮件发送失败: {e}")
        return None

def run_analysis(stock_pool: list = TECH_100, period_days: int = 365):
    """运行分析"""
    print("\n" + "="*80)
    print("🚀 Alpha158 多因子选股系统 (147因子)")
    print("="*80)
    print(f"候选池: {len(stock_pool)} 只股票")

    period2 = int(datetime.now().timestamp())
    period1 = int((datetime.now() - timedelta(days=period_days)).timestamp())

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

    # 自动计算因子权重
    available_factors = [c for c in df_factors.columns]
    factor_weights = {}
    for factor in available_factors:
        factor_weights[factor] = get_factor_weight(factor, available_factors)

    # 过滤掉权重为0的因子
    factor_weights = {k: v for k, v in factor_weights.items() if v != 0}

    print(f"\n📊 因子统计:")
    print(f"   总因子: {len(available_factors)}")
    print(f"   正向因子: {sum(1 for v in factor_weights.values() if v > 0)}")
    print(f"   负向因子: {sum(1 for v in factor_weights.values() if v < 0)}")
    print(f"   中性因子: {sum(1 for v in factor_weights.values() if v == 0)}")

    # 计算得分
    df_subset = df_factors[[f for f in factor_weights.keys() if f in df_factors.columns]].copy()
    scores = calculate_composite_score(df_subset, factor_weights)

    df_result = df_factors.copy()
    df_result['score'] = scores
    df_result = df_result.sort_values('score', ascending=False)

    # 输出TOP 20
    print(f"\n" + "="*80)
    print("🏆 TOP 20 推荐股票 (147因子)")
    print("="*80)
    print(f"{'排名':<4} {'代码':<8} {'得分':<10} {'6月动量':<12} {'夏普':<10} {'波动':<10}")
    print("-"*70)

    top20 = df_result.head(20).index.tolist()
    for i, ticker in enumerate(top20):
        row = df_result.loc[ticker]
        mom = row.get('momentum_6m', row.get('momentum_3m', 0))
        sharpe = row.get('sharpe_ratio_20d', 0)
        vol = row.get('volatility_20d', 0)
        print(f"{i+1:<4} {ticker:<8} {row['score']:<10.3f} {mom:<10.1f}% {sharpe:<10.2f} {vol:<10.2f}")

    # 因子重要性分析
    print(f"\n📈 Top 20 重要因子:")
    imp = pd.Series(factor_weights)
    imp = imp.sort_values(key=abs, ascending=False)
    for i, (factor, weight) in enumerate(imp.head(20).items()):
        direction = "↑" if weight > 0 else "↓"
        print(f"   {i+1:2d}. {factor:<30} {direction}{abs(weight):.3f}")

    # 保存结果
    df_result.to_csv('/Users/wangqingxiang/.openclaw/workspace/ranking_top100.csv')
    print(f"\n💾 结果已保存: ranking_top100.csv")

    # 发送邮件
    html = send_email_report(df_result, top20)
    if html:
        with open('/Users/wangqingxiang/.openclaw/workspace/ranking_report.html', 'w') as f:
            f.write(html)
        print(f"📧 邮件报告已保存: ranking_report.html")

    return df_result

if __name__ == "__main__":
    df_result = run_analysis()
