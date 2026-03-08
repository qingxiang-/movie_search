#!/usr/bin/env python3
"""
Alpha158 排名法多因子选股系统 - 使用全部因子
✅ 基于因子得分的传统量化方法
✅ 支持邮件发送
✅ 支持 Qwen LLM 新闻搜索和总结
"""
import sys
import os
import logging
import json
import hashlib
from typing import Dict
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np
import requests
from http import HTTPStatus
import warnings
warnings.filterwarnings('ignore')

# Configuration constants
MAX_WORKERS = 10  # Maximum parallel workers for API calls
MIN_DATA_DAYS = 100  # Minimum days of data required for analysis
CACHE_DIR = Path.home() / ".cache" / "ranking_method" / "stock_data"
PROGRESS_FILE = Path.home() / ".cache" / "ranking_method" / "progress.json"
CACHE_EXPIRY_DAYS = 1  # Cache expiry in days
TRADING_DAYS_PER_YEAR = 252  # Approximate trading days in a year
CALENDAR_DAYS_PER_YEAR = 365  # Calendar days in a year

# Initialize cache directory
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()
OUTPUT_DIR = SCRIPT_DIR  # Output files saved to script directory

# Add paths once at module level
sys.path.insert(0, str(SCRIPT_DIR))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    ('z_score_', -1, 0.02),  # 也匹配 z_score_returns
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

# Build O(1) lookup dict for factor weights (prefix -> direction * weight)
FACTOR_WEIGHT_LOOKUP = {
    prefix: direction * weight
    for prefix, direction, weight in FACTOR_TYPES
}
# Sort prefixes by length (longest first) for most specific match
FACTOR_PREFIXES_SORTED = sorted(FACTOR_WEIGHT_LOOKUP.keys(), key=len, reverse=True)

def get_factor_weight(factor_name: str, available_factors: list = None) -> float:
    """根据因子名称自动确定权重 - O(1) lookup with prefix matching"""
    # Try to find matching prefix (longest first for most specific match)
    for prefix in FACTOR_PREFIXES_SORTED:
        if factor_name.startswith(prefix):
            return FACTOR_WEIGHT_LOOKUP[prefix]
    # Default weight for unknown factors
    return 0.01

def _get_cache_path(ticker: str, period1: int, period2: int) -> Path:
    """Generate cache file path based on ticker and date range."""
    key = f"{ticker}_{period1}_{period2}"
    hash_key = hashlib.md5(key.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{ticker}_{hash_key}.csv"


def _is_cache_valid(cache_path: Path) -> bool:
    """Check if cache file exists and is not expired."""
    if not cache_path.exists():
        return False
    # Check if cache is expired
    mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
    age = datetime.now() - mtime
    return age.days < CACHE_EXPIRY_DAYS


def _load_from_cache(cache_path: Path) -> pd.DataFrame:
    """Load DataFrame from cache file."""
    try:
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        logger.debug(f"Cache hit: {cache_path.name}")
        return df
    except Exception as e:
        logger.debug(f"Cache load error: {e}")
        return None


def _save_to_cache(df: pd.DataFrame, cache_path: Path) -> None:
    """Save DataFrame to cache file."""
    try:
        df.to_csv(cache_path)
        logger.debug(f"Cache saved: {cache_path.name}")
    except Exception as e:
        logger.debug(f"Cache save error: {e}")


def _trading_days_to_calendar_days(trading_days: int) -> int:
    """Convert trading days to calendar days (approximate)."""
    return int(trading_days * CALENDAR_DAYS_PER_YEAR / TRADING_DAYS_PER_YEAR)


def _load_progress() -> dict:
    """Load progress from file."""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Progress load error: {e}")
    return {}


def _save_progress(progress: dict) -> None:
    """Save progress to file."""
    try:
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)
    except Exception as e:
        logger.debug(f"Progress save error: {e}")


def _clear_progress() -> None:
    """Clear progress file."""
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()


def _fetch_stock_with_factors(ticker: str, period1: int, period2: int) -> tuple:
    """
    Fetch stock data and calculate factors for a single ticker.
    Returns: (ticker, factors_dict) on success, (ticker, None) on failure.
    """
    df = get_stock_data(ticker, period1, period2)
    if df is not None and len(df) > MIN_DATA_DAYS:
        factors = calculate_factors(df)
        if factors:
            logger.debug(f"   {ticker}: ✓ {len(factors)} 因子")
            return (ticker, factors)
        else:
            logger.debug(f"   {ticker}: ❌ 因子计算失败")
    else:
        logger.debug(f"   {ticker}: ❌ 数据不足")
    return (ticker, None)


def get_stock_data(ticker: str, period1: int, period2: int) -> pd.DataFrame:
    """获取历史数据（带缓存）"""
    # Check cache first
    cache_path = _get_cache_path(ticker, period1, period2)
    if _is_cache_valid(cache_path):
        cached_df = _load_from_cache(cache_path)
        if cached_df is not None:
            return cached_df

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
            logger.debug(f"{ticker}: HTTP {resp.status_code}")
            return None

        data = resp.json()
        result = data['chart'].get('result')
        if not result:
            logger.debug(f"{ticker}: No chart result")
            return None

        df = pd.DataFrame({
            'Open': result[0]['indicators']['quote'][0]['open'],
            'High': result[0]['indicators']['quote'][0]['high'],
            'Low': result[0]['indicators']['quote'][0]['low'],
            'Close': result[0]['indicators']['quote'][0]['close'],
            'Volume': result[0]['indicators']['quote'][0]['volume']
        }, index=pd.to_datetime(result[0]['timestamp'], unit='s'))

        df = df.dropna()

        # Save to cache
        _save_to_cache(df, cache_path)

        return df
    except requests.exceptions.Timeout:
        logger.debug(f"{ticker}: Request timeout")
        return None
    except requests.exceptions.RequestException as e:
        logger.debug(f"{ticker}: Request error: {e}")
        return None
    except (KeyError, IndexError, TypeError) as e:
        logger.debug(f"{ticker}: Parse error: {e}")
        return None
    except Exception as e:
        logger.debug(f"{ticker}: Unexpected error: {e}")
        return None

def calculate_factors(df: pd.DataFrame) -> dict:
    """计算因子 - 使用并行计算加速"""
    from alpha158 import Alpha158

    try:
        alpha = Alpha158(df)

        # Parallelize batch computations
        def compute_batch(batch_name):
            try:
                batch_func = getattr(alpha, batch_name)
                return batch_func()
            except Exception:
                return {}

        batch_names = ['compute_batch1', 'compute_batch2', 'compute_batch3',
                       'compute_batch4', 'compute_batch5']

        # Use ThreadPoolExecutor for parallel batch computation
        with ThreadPoolExecutor(max_workers=5) as executor:
            batch_results = list(executor.map(compute_batch, batch_names))

        all_factors = {}
        for batch_result in batch_results:
            all_factors.update(batch_result)

        factors = {}
        for name, series in all_factors.items():
            if hasattr(series, 'iloc') and len(series) > 0:
                val = series.iloc[-1]
                if pd.notna(val) and np.isfinite(val):
                    factors[name.lower()] = float(val)

        return factors
    except ImportError as e:
        logger.error(f"Alpha158 import error: {e}")
        return {}
    except AttributeError as e:
        logger.error(f"Alpha158 attribute error: {e}")
        return {}
    except Exception as e:
        logger.debug(f"Factor calculation error: {e}")
        return {}

def zscore_normalize(series: pd.Series) -> pd.Series:
    """Z-score 标准化"""
    mean = series.mean()
    std = series.std()
    # Handle case where all values are NaN or constant
    if pd.isna(mean) or std == 0 or pd.isna(std):
        return pd.Series(0.0, index=series.index)
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
        from utils.email_sender import EmailSender

        # Validate email sender configuration
        logger.info("正在初始化邮件发送器...")
        sender = EmailSender()

        # 详细日志
        logger.info(f"AccessKey ID: {'已配置' if sender.access_key_id else '未配置'}")
        logger.info(f"Sender Email: {sender.sender_email if sender.sender_email else '未配置'}")
        logger.info(f"Recipients: {sender.recipients if sender.recipients else '未配置'}")
        logger.info(f"Client Initialized: {'是' if sender.client else '否'}")

        if not sender.client:
            logger.warning("邮件客户端未初始化，请检查 .env 文件")
            return None

        if not sender.recipients:
            logger.warning("收件人列表为空，请检查 email_config.yaml")
            return None

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
            <h1>📊 Alpha158 多因子选股报告</h1>
            <p>生成时间：{timestamp}</p>
            <p>候选池：{len(df_result)} 只美股科技股 | 因子数：{len(df_result.columns)-1}</p>

            <div class="summary">
                <h3>🏆 TOP 20 推荐</h3>
                <table>
                    <tr><th>排名</th><th>代码</th><th>综合得分</th><th>6 月动量</th><th>夏普</th><th>波动</th></tr>
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
            <p><small>Generated by Alpha158 Ranking System</small></p>
        </body>
        </html>
        """

        subject = f"Alpha158 选股报告 - TOP 20 - {datetime.now().strftime('%Y-%m-%d')}"
        logger.info(f"正在发送邮件：{subject}")
        result = sender.send_email_report(html, subject)

        if result:
            logger.info("邮件发送成功")
        else:
            logger.error("邮件发送失败")

        return html

    except Exception as e:
        logger.error(f"邮件发送异常：{e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def _fetch_all_stock_factors(stock_pool: list, period1: int, period2: int, use_progress: bool = True) -> dict:
    """Fetch factors for all stocks in parallel with progress persistence."""
    logger.info(f"   并行模式：最大工作线程数={MAX_WORKERS}")

    # Load previous progress if available
    progress = _load_progress() if use_progress else {}
    cached_tickers = set(progress.get('tickers', []))

    # Filter out already processed stocks
    remaining_stocks = [t for t in stock_pool if t not in cached_tickers]

    if remaining_stocks:
        logger.info(f"   待处理：{len(remaining_stocks)} 只股票 (已缓存：{len(cached_tickers)} 只)")
    else:
        logger.info(f"   全部使用缓存：{len(cached_tickers)} 只股票")

    all_factors = progress.get('data', {})

    if remaining_stocks:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(_fetch_stock_with_factors, ticker, period1, period2): ticker
                for ticker in remaining_stocks
            }
            completed = 0
            for future in as_completed(futures):
                completed += 1
                ticker, factors = future.result()
                if factors:
                    all_factors[ticker] = factors
                if completed % 5 == 0 or completed == len(remaining_stocks):
                    # Save progress incrementally
                    progress_data = {'tickers': list(all_factors.keys()), 'data': all_factors}
                    _save_progress(progress_data)
                    logger.info(f"   进度：{completed}/{len(remaining_stocks)} (已保存)")

    # Clear progress on successful completion
    if len(all_factors) >= len(stock_pool) * 0.9:  # 90% success rate
        _clear_progress()

    return all_factors


def _calculate_factor_weights(df_factors: pd.DataFrame) -> dict:
    """Calculate and filter factor weights."""
    available_factors = [c for c in df_factors.columns]
    factor_weights = {f: get_factor_weight(f, available_factors) for f in available_factors}
    # Filter out zero weights
    factor_weights = {k: v for k, v in factor_weights.items() if v != 0}
    return factor_weights


def _log_factor_statistics(factor_weights: dict, total_factors: int):
    """Log factor statistics."""
    logger.info(f"\n📊 因子统计:")
    logger.info(f"   总因子：{total_factors}")
    logger.info(f"   正向因子：{sum(1 for v in factor_weights.values() if v > 0)}")
    logger.info(f"   负向因子：{sum(1 for v in factor_weights.values() if v < 0)}")
    logger.info(f"   中性因子：{sum(1 for v in factor_weights.values() if v == 0)}")


def _calculate_scores_and_rank(df_factors: pd.DataFrame, factor_weights: dict) -> pd.DataFrame:
    """Calculate composite scores and rank stocks."""
    df_subset = df_factors[[f for f in factor_weights.keys() if f in df_factors.columns]].copy()
    scores = calculate_composite_score(df_subset, factor_weights)
    df_result = df_factors.copy()
    df_result['score'] = scores
    return df_result.sort_values('score', ascending=False)


def _print_top_stocks(df_result: pd.DataFrame, top_n: int = 20):
    """Print top N stocks with key metrics."""
    logger.info(f"\n" + "="*80)
    logger.info(f"🏆 TOP {top_n} 推荐股票\n" + "="*80)
    logger.info("="*80)
    logger.info(f"{'排名':<4} {'代码':<8} {'得分':<10} {'6 月动量':<12} {'夏普':<10} {'波动':<10}")
    logger.info("-"*70)

    top_n = min(top_n, len(df_result))
    for i, ticker in enumerate(df_result.head(top_n).index.tolist()):
        row = df_result.loc[ticker]
        mom = row.get('momentum_6m', row.get('momentum_3m', 0))
        sharpe = row.get('sharpe_ratio_20d', 0)
        vol = row.get('volatility_20d', 0)
        logger.info(f"{i+1:<4} {ticker:<8} {row['score']:<10.3f} {mom:<10.1f}% {sharpe:<10.2f} {vol:<10.2f}")


def _print_factor_importance(factor_weights: dict, top_n: int = 20):
    """Print top N important factors."""
    logger.info(f"\n📈 Top {top_n} 重要因子:")
    imp = pd.Series(factor_weights)
    imp = imp.sort_values(key=abs, ascending=False)
    for i, (factor, weight) in enumerate(imp.head(top_n).items()):
        direction = "↑" if weight > 0 else "↓"
        logger.info(f"   {i+1:2d}. {factor:<30} {direction}{abs(weight):.3f}")


def _save_results(df_result: pd.DataFrame, top20: list) -> tuple:
    """Save results to CSV and HTML. Returns (csv_path, html_content)."""
    output_csv = OUTPUT_DIR / 'ranking_result.csv'
    df_result.to_csv(output_csv)
    logger.info(f"\n💾 结果已保存：{output_csv}")

    html = None
    output_html = None
    if top20:
        html = send_email_report(df_result, top20)
        if html:
            output_html = OUTPUT_DIR / 'ranking_report.html'
            with open(output_html, 'w') as f:
                f.write(html)
            logger.info(f"📧 邮件报告已保存：{output_html}")

    return output_csv, html, output_html


def _get_top_stock_news(ticker: str, api_key: str, use_azure: bool = False,
                        alpha_factors: Dict = None) -> str:
    """
    使用 LLM 结合 Alpha 因子分析股票新闻
    注意：这里使用 LLM 的内部知识来分析，因为无法获取实时新闻
    """
    try:
        # 如果没有传入 api_key，尝试从环境变量加载
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("DASHSCOPE_API_KEY", "")

        # 构建因子分析信息
        factor_info = ""
        if alpha_factors:
            factor_lines = []
            for key, val in alpha_factors.items():
                if isinstance(val, (int, float)) and val == val:  # not NaN
                    factor_lines.append(f"   - {key}: {val:.4f}" if abs(val) < 1000 else f"   - {key}: {val:.2f}")
            if factor_lines:
                factor_info = "\n\nAlpha 因子数据:\n" + "\n".join(factor_lines[:15])  # 限制最多 15 个因子

        # 构建分析 prompt - 让 LLM 基于因子数据和内部知识进行分析
        prompt = f"""作为资深量化分析师，请对 {ticker} 股票进行深度分析。

{factor_info}

请结合以上因子数据和你的专业知识，分析：
1. 从因子数据看，该股票的技术面特征（动量、波动率、趋势等）
2. 基于你对 {ticker} 的了解，总结其基本面和近期动态
3. 投资建议和风险提示

要求：
- 分析要具体，避免套话
- 基于因子数据给出量化角度的解读
- 结论明确，有可操作性

限制在 400 字以内。"""

        if use_azure:
            # 使用 Azure OpenAI (新版 SDK)
            try:
                from openai import AzureOpenAI
            except ImportError:
                return f"无法获取 {ticker} 分析（需要安装 openai>=1.0.0）"

            azure_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
            azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")

            if not azure_api_key or not azure_endpoint:
                return f"无法获取 {ticker} 分析（Azure 配置缺失）"

            client = AzureOpenAI(
                api_key=azure_api_key,
                api_version=azure_api_version,
                azure_endpoint=azure_endpoint.rstrip('/')
            )

            response = client.chat.completions.create(
                model=azure_deployment,
                messages=[
                    {"role": "system", "content": "你是资深量化分析师，擅长结合技术因子和基本面分析美股。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            return response.choices[0].message.content
        else:
            # 从环境变量加载配置
            from dotenv import load_dotenv
            load_dotenv()

            base_url = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
            model = os.getenv("DASHSCOPE_MODEL", "qwen-max")

            if not api_key:
                return "⚠️ 未设置 DASHSCOPE_API_KEY"

            url = f"{base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是资深量化分析师，擅长结合技术因子和基本面分析美股。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                error_msg = f"HTTP {response.status_code}"
                try:
                    error = response.json()
                    error_msg += f": {error.get('error', {}).get('message', 'Unknown')}"
                except:
                    pass
                return f"无法获取 {ticker} 分析（{error_msg}）"
    except Exception as e:
        return f"无法获取 {ticker} 分析（{str(e)}）"


def _analyze_top_stocks_with_llm(top_stocks: list, df_result: pd.DataFrame, api_key: str) -> list:
    """Use LLM to analyze and summarize top stocks with alpha factors."""
    # Try Azure OpenAI first, then Qwen API
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    use_azure = bool(azure_api_key and azure_api_key != "your_azure_api_key_here")

    if use_azure:
        logger.info(f"   使用 Azure OpenAI 获取分析")
    else:
        logger.info(f"   使用 Qwen API 获取分析")

    results = []
    for ticker in top_stocks:
        row = df_result.loc[ticker]
        mom = row.get('momentum_6m', row.get('momentum_3m', 0))
        sharpe = row.get('sharpe_ratio_20d', 0)
        vol = row.get('volatility_20d', 0)
        score = row.get('score', 0)

        # 提取该股票的 alpha 因子
        alpha_factors = {k: v for k, v in row.items() if k not in ['score']}

        # Get analysis using LLM with alpha factors
        analysis = _get_top_stock_news(ticker, api_key, use_azure=use_azure, alpha_factors=alpha_factors)

        results.append({
            'ticker': ticker,
            'score': score,
            'momentum_6m': mom,
            'sharpe': sharpe,
            'volatility': vol,
            'alpha_factors': alpha_factors,
            'analysis': analysis
        })
        logger.info(f"   ✅ {ticker}: 分析完成")

    return results


def _generate_enhanced_html(top_stocks_analysis: list, df_result: pd.DataFrame, top20: list) -> str:
    """Generate enhanced HTML report with LLM summaries."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
            th {{ background-color: #3498db; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .stock-card {{ border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 8px; background: #fafafa; }}
            .stock-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
            .stock-name {{ font-size: 18px; font-weight: bold; color: #2c3e50; }}
            .stock-score {{ background: #3498db; color: white; padding: 5px 10px; border-radius: 4px; }}
            .news-summary {{ background: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 10px 0; }}
            .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 10px 0; }}
            .metric {{ background: #e8f4f8; padding: 8px; border-radius: 4px; text-align: center; }}
            .metric-label {{ font-size: 12px; color: #666; }}
            .metric-value {{ font-size: 16px; font-weight: bold; color: #2c3e50; }}
        </style>
    </head>
    <body>
        <h1>📊 Alpha158 多因子选股报告 - 增强版</h1>
        <p>生成时间：{timestamp}</p>
        <p>候选池：{len(df_result)} 只美股科技股 | 因子数：{len(df_result.columns)-1}</p>

        <h2>🏆 TOP 20 推荐</h2>
        <table>
            <tr><th>排名</th><th>代码</th><th>综合得分</th><th>6 月动量</th><th>夏普比率</th><th>波动率</th></tr>
    """

    for i, ticker in enumerate(top20):
        row = df_result.loc[ticker]
        mom = row.get('momentum_6m', row.get('momentum_3m', 0))
        sharpe = row.get('sharpe_ratio_20d', 0)
        vol = row.get('volatility_20d', 0)
        html += f"""
            <tr>
                <td>{i+1}</td>
                <td><strong>{ticker}</strong></td>
                <td>{row['score']:.3f}</td>
                <td>{mom:.1f}%</td>
                <td>{sharpe:.2f}</td>
                <td>{vol:.1f}%</td>
            </tr>"""

    html += """
        </table>

        <h2>📰 TOP 5 股票深度分析</h2>
    """

    # Add detailed analysis for top 5 stocks
    for stock in top_stocks_analysis[:5]:
        ticker = stock['ticker']
        analysis = stock.get('analysis', '暂无分析')

        html += f"""
        <div class="stock-card">
            <div class="stock-header">
                <span class="stock-name">{ticker}</span>
                <span class="stock-score">得分：{stock['score']:.3f}</span>
            </div>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">6 月动量</div>
                    <div class="metric-value">{stock['momentum_6m']:.1f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">夏普比率</div>
                    <div class="metric-value">{stock['sharpe']:.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">波动率</div>
                    <div class="metric-value">{stock['volatility']:.1f}%</div>
                </div>
            </div>
            <div class="news-summary">
                <strong>🤖 LLM 因子分析：</strong><br>
                {analysis.replace(chr(10), '<br>')}
            </div>
        </div>
        """

    html += """
        <hr>
        <p><small>Generated by Alpha158 Ranking System with Qwen LLM</small></p>
    </body>
    </html>
    """

    return html


def run_analysis(stock_pool: list = TECH_100, period_days: int = 252, use_trading_days: bool = True):
    """
    运行分析

    Args:
        stock_pool: 股票池列表
        period_days: 时间周期（天数）
        use_trading_days: 如果为 True，period_days 被视为交易日，自动转换为日历日
    """
    logger.info("\n" + "="*80)
    logger.info("🚀 Alpha158 多因子选股系统\n" + "="*80)
    logger.info("="*80)
    logger.info(f"候选池：{len(stock_pool)} 只股票")

    # Convert trading days to calendar days if needed
    if use_trading_days:
        calendar_days = _trading_days_to_calendar_days(period_days)
        logger.info(f"时间周期：{period_days} 交易日 ≈ {calendar_days} 日历日")
    else:
        calendar_days = period_days
        logger.info(f"时间周期：{period_days} 日历日")

    period2 = int(datetime.now().timestamp())
    period1 = int((datetime.now() - timedelta(days=calendar_days)).timestamp())

    logger.info(f"\n📥 获取数据 ({calendar_days}天)...")
    all_factors = _fetch_all_stock_factors(stock_pool, period1, period2)

    if not all_factors:
        logger.error("\n❌ 无有效数据")
        return None

    logger.info(f"\n✅ 成功获取 {len(all_factors)}/{len(stock_pool)} 只股票数据")

    # 构建 DataFrame
    df_factors = pd.DataFrame(all_factors).T

    # 计算因子权重
    factor_weights = _calculate_factor_weights(df_factors)

    # 记录因子统计
    _log_factor_statistics(factor_weights, len(df_factors.columns))

    # 计算得分并排名
    df_result = _calculate_scores_and_rank(df_factors, factor_weights)

    # 输出 TOP 20
    _print_top_stocks(df_result, 20)

    # 因子重要性分析
    _print_factor_importance(factor_weights, 20)

    # 保存结果
    top20 = df_result.head(20).index.tolist()

    # 加载环境变量并获取 API Key
    from dotenv import load_dotenv
    load_dotenv()
    qwen_api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if qwen_api_key:
        logger.info("\n📰 正在获取 TOP 5 股票新闻...")
        top5_stocks = top20[:5]
        top_stocks_analysis = _analyze_top_stocks_with_llm(top5_stocks, df_result, qwen_api_key)

        # 生成增强版 HTML 报告（包含新闻）
        _save_results_with_news(df_result, top20, top_stocks_analysis)
    else:
        logger.warning("\n⚠️  未设置 DASHSCOPE_API_KEY，跳过新闻获取")
        _save_results(df_result, top20)

    return df_result


def _save_results_with_news(df_result: pd.DataFrame, top20: list, top_stocks_analysis: list) -> None:
    """Save results with LLM news summaries."""
    output_csv = OUTPUT_DIR / 'ranking_result.csv'
    df_result.to_csv(output_csv)
    logger.info(f"\n💾 结果已保存：{output_csv}")

    # Generate enhanced HTML with news
    html = _generate_enhanced_html(top_stocks_analysis, df_result, top20)

    if html:
        output_html = OUTPUT_DIR / 'ranking_report_enhanced.html'
        with open(output_html, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"📧 增强版报告已保存：{output_html}")

    # Also send email with enhanced report
    _send_enhanced_email(html, top_stocks_analysis)


def _send_enhanced_email(html: str, top_stocks_analysis: list):
    """Send enhanced email with news summaries."""
    try:
        from utils.email_sender import EmailSender

        logger.info("正在初始化邮件发送器...")
        sender = EmailSender()

        if not sender.client:
            logger.warning("邮件客户端未初始化，请检查 .env 文件")
            return

        if not sender.recipients:
            logger.warning("收件人列表为空，请检查 email_config.yaml")
            return

        subject = f"Alpha158 选股报告 (增强版) - TOP 20 - {datetime.now().strftime('%Y-%m-%d')}"
        logger.info(f"正在发送邮件：{subject}")
        result = sender.send_email_report(html, subject)

        if result:
            logger.info("邮件发送成功")
        else:
            logger.error("邮件发送失败")

    except Exception as e:
        logger.error(f"邮件发送异常：{e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    df_result = run_analysis()

