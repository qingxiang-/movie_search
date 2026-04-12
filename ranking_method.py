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
# Import LLM factor integration if available
try:
    from core.llm_factor_integration import get_llm_factors_sync
    LLM_FACTOR_AVAILABLE = True
except ImportError:
    LLM_FACTOR_AVAILABLE = False
    get_llm_factors_sync = None

# Configure logging
def configure_logging(log_level):
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"无效的日志级别: {log_level}")

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)

# ============================================
# TOP 100+ 美股科技股候选池
# ============================================
# TOP 60 Core + Chinese Internet Tech Stocks (default candidate pool)
# 核心60只科技股票 - 美股科技巨头 + 头部中概科技互联网（市值Top 10）
TECH_TOP_50 = [
    # 科技巨头 (7)
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA',
    # 半导体巨头 (10)
    'AVGO', 'AMD', 'INTC', 'QCOM', 'ASML', 'TXN', 'AMAT', 'MU', 'LRCX', 'KLAC',
    # 半导体设备/材料/设计 (8)
    'MRVL', 'MPWR', 'MCHP', 'ON', 'TER', 'KEYS', 'CDNS', 'SNPS',
    # 软件/SaaS (11)
    'ORCL', 'ADBE', 'CRM', 'NFLX', 'NOW', 'INTU', 'PLTR', 'CRWD', 'PANW', 'ZM', 'DDOG',
    # AI/云/网络 (6)
    'SNOW', 'MDB', 'NET', 'SMH', 'TSM', 'PYPL',
    # 新能源/光伏 (4)
    'FSLR', 'ENPH', 'SEDG', 'RUN',
    # 金融科技/其他 (4)
    'COIN', 'UPST', 'SOFI', 'DELL',
    # 中概科技互联网头部 - 市值Top 10 (美股上市) (10)
    'BABA',   # 阿里巴巴 - 电商/云计算
    'TCEHY',  # 腾讯控股 - 社交/游戏/云 (ADR)
    'PDD',    # 拼多多 - 电商/跨境
    'JD',     # 京东 - 电商/物流
    'BIDU',   # 百度 - 搜索/AI
    'NIO',    # 蔚来 - 电动车
    'NTES',   # 网易 - 游戏/互联网
    'LI',     # 理想汽车 - 电动车
    'XPEV',   # 小鹏汽车 - 电动车
    'DIDI',   # 滴滴 - 出行
]

# FULL LIST (140+ stocks - kept but not used by default)
# 完整名单（保留但默认不使用）
TECH_FULL = [
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
    'INTC', 'SMH', 'XOM', 'CVX', 'MARA', 'RIOT',
    'UPST', 'SOFI', 'PYPL', 'AFRM',
]

# 股票名称映射（中文优先）
STOCK_NAMES = {
    # 科技巨头
    'AAPL': {'cn': '苹果', 'en': 'Apple'},
    'MSFT': {'cn': '微软', 'en': 'Microsoft'},
    'NVDA': {'cn': '英伟达', 'en': 'NVIDIA'},
    'GOOGL': {'cn': '谷歌-A', 'en': 'Google-A'},
    'GOOG': {'cn': '谷歌-C', 'en': 'Google-C'},
    'AMZN': {'cn': '亚马逊', 'en': 'Amazon'},
    'META': {'cn': 'Meta', 'en': 'Meta/Facebook'},
    'TSLA': {'cn': '特斯拉', 'en': 'Tesla'},

    # 半导体设备
    'AVGO': {'cn': '博通', 'en': 'Broadcom'},
    'AMD': {'cn': 'AMD', 'en': 'AMD'},
    'QCOM': {'cn': '高通', 'en': 'Qualcomm'},
    'ORCL': {'cn': '甲骨文', 'en': 'Oracle'},
    'TSM': {'cn': '台积电', 'en': 'TSMC'},
    'ASML': {'cn': '阿斯麦', 'en': 'ASML'},
    'TXN': {'cn': '德州仪器', 'en': 'Texas Instruments'},
    'AMAT': {'cn': '应用材料', 'en': 'Applied Materials'},
    'MU': {'cn': '美光', 'en': 'Micron'},
    'LRCX': {'cn': '拉姆研究', 'en': 'Lam Research'},
    'KLAC': {'cn': '科磊', 'en': 'KLA'},
    'MRVL': {'cn': '迈威尔', 'en': 'Marvell'},
    'TER': {'cn': '泰瑞达', 'en': 'Teradyne'},
    'KEYS': {'cn': '是德科技', 'en': 'Keysight'},
    'CDNS': {'cn': '铿腾电子', 'en': 'Cadence'},
    'SNPS': {'cn': '新思科技', 'en': 'Synopsys'},
    'AMKR': {'cn': '安靠', 'en': 'Amkor'},
    'MPWR': {'cn': 'Monolithic Power', 'en': 'Monolithic Power'},
    'MCHP': {'cn': '微芯', 'en': 'Microchip'},
    'ON': {'cn': '安森美', 'en': 'ON Semiconductor'},
    'FORM': {'cn': 'FormFactor', 'en': 'FormFactor'},
    'CAMT': {'cn': 'Camtek', 'en': 'Camtek'},

    # 光伏/新能源
    'FSLR': {'cn': '第一太阳能', 'en': 'First Solar'},
    'SEDG': {'cn': 'SolarEdge', 'en': 'SolarEdge'},
    'ENPH': {'cn': 'Enphase', 'en': 'Enphase Energy'},
    'RUN': {'cn': 'Sunrun', 'en': 'Sunrun'},

    # 存储芯片
    'WDC': {'cn': '西部数据', 'en': 'Western Digital'},
    'STX': {'cn': '希捷', 'en': 'Seagate'},
    'NTAP': {'cn': 'NetApp', 'en': 'NetApp'},

    # 软件/云/SaaS
    'ADBE': {'cn': 'Adobe', 'en': 'Adobe'},
    'CRM': {'cn': '赛富时', 'en': 'Salesforce'},
    'NFLX': {'cn': '奈飞', 'en': 'Netflix'},
    'NOW': {'cn': 'ServiceNow', 'en': 'ServiceNow'},
    'WDAY': {'cn': 'Workday', 'en': 'Workday'},
    'ZM': {'cn': 'Zoom', 'en': 'Zoom'},
    'DDOG': {'cn': 'Datadog', 'en': 'Datadog'},
    'CRWD': {'cn': 'CrowdStrike', 'en': 'CrowdStrike'},
    'ZS': {'cn': 'Zscaler', 'en': 'Zscaler'},
    'PANW': {'cn': 'Palo Alto', 'en': 'Palo Alto Networks'},
    'SNOW': {'cn': 'Snowflake', 'en': 'Snowflake'},
    'PLTR': {'cn': 'Palantir', 'en': 'Palantir'},
    'INTU': {'cn': 'Intuit', 'en': 'Intuit'},
    'MDB': {'cn': 'MongoDB', 'en': 'MongoDB'},
    'ESTC': {'cn': 'Elastic', 'en': 'Elastic'},
    'HUBS': {'cn': 'HubSpot', 'en': 'HubSpot'},
    'OKTA': {'cn': 'Okta', 'en': 'Okta'},
    'NET': {'cn': 'Cloudflare', 'en': 'Cloudflare'},
    'DT': {'cn': 'Dynatrace', 'en': 'Dynatrace'},
    'GDDY': {'cn': 'GoDaddy', 'en': 'GoDaddy'},
    'APP': {'cn': 'AppLovin', 'en': 'AppLovin'},
    'CFLT': {'cn': 'Confluent', 'en': 'Confluent'},
    'PATH': {'cn': 'UiPath', 'en': 'UiPath'},
    'TEAM': {'cn': 'Atlassian', 'en': 'Atlassian'},
    'U': {'cn': 'Unity', 'en': 'Unity Software'},
    'ANSS': {'cn': 'Ansys', 'en': 'Ansys'},
    'ZEN': {'cn': 'Zendesk', 'en': 'Zendesk'},
    'COUP': {'cn': 'Coupa', 'en': 'Coupa'},
    'VEEV': {'cn': 'Veeva', 'en': 'Veeva Systems'},
    'FROG': {'cn': 'JFrog', 'en': 'JFrog'},

    # 电商/支付/金融科技
    'SHOP': {'cn': 'Shopify', 'en': 'Shopify'},
    'SQ': {'cn': 'Block', 'en': 'Block/Square'},
    'PYPL': {'cn': 'PayPal', 'en': 'PayPal'},
    'COIN': {'cn': 'Coinbase', 'en': 'Coinbase'},
    'HOOD': {'cn': 'Robinhood', 'en': 'Robinhood'},
    'UPST': {'cn': 'Upstart', 'en': 'Upstart'},
    'SOFI': {'cn': 'SoFi', 'en': 'SoFi Technologies'},
    'AFRM': {'cn': 'Affirm', 'en': 'Affirm'},

    # 社交媒体/游戏
    'PINS': {'cn': 'Pinterest', 'en': 'Pinterest'},
    'SNAP': {'cn': 'Snap', 'en': 'Snapchat'},
    'TTD': {'cn': 'Trade Desk', 'en': 'Trade Desk'},
    'RBLX': {'cn': 'Roblox', 'en': 'Roblox'},
    'TTWO': {'cn': 'Take-Two', 'en': 'Take-Two Interactive'},
    'EA': {'cn': '艺电', 'en': 'Electronic Arts'},

    # 金融
    'V': {'cn': 'Visa', 'en': 'Visa'},
    'MA': {'cn': '万事达', 'en': 'Mastercard'},
    'AXP': {'cn': '运通', 'en': 'American Express'},
    'BLK': {'cn': '贝莱德', 'en': 'BlackRock'},
    'ADP': {'cn': 'ADP', 'en': 'ADP'},
    'PAYX': {'cn': 'Paychex', 'en': 'Paychex'},
    'FIS': {'cn': 'FIS', 'en': 'Fidelity National'},
    'FISV': {'cn': 'Fiserv', 'en': 'Fiserv'},
    'CME': {'cn': '芝商所', 'en': 'CME Group'},
    'MCO': {'cn': '穆迪', 'en': "Moody's"},
    'SPGI': {'cn': '标普全球', 'en': 'S&P Global'},
    'NTRS': {'cn': '北方信托', 'en': 'Northern Trust'},
    'MSCI': {'cn': 'MSCI', 'en': 'MSCI'},

    # 通信
    'TMUS': {'cn': 'T-Mobile', 'en': 'T-Mobile'},
    'VZ': {'cn': '威瑞森', 'en': 'Verizon'},
    'NOK': {'cn': '诺基亚', 'en': 'Nokia'},
    'CSCO': {'cn': '思科', 'en': 'Cisco'},
    'ERIC': {'cn': '爱立信', 'en': 'Ericsson'},
    'CMCSA': {'cn': '康卡斯特', 'en': 'Comcast'},
    'CHTR': {'cn': '特许通讯', 'en': 'Charter Communications'},

    # 其他科技
    'DIS': {'cn': '迪士尼', 'en': 'Disney'},
    'BIDU': {'cn': '百度', 'en': 'Baidu'},
    'IBM': {'cn': 'IBM', 'en': 'IBM'},
    'DELL': {'cn': '戴尔', 'en': 'Dell'},
    'HPQ': {'cn': '惠普', 'en': 'HP'},
    'HPE': {'cn': '慧与', 'en': 'HPE'},
    'MSTR': {'cn': '微策', 'en': 'MicroStrategy'},
    'ATVI': {'cn': '动视暴雪', 'en': 'Activision Blizzard'},
    'NICE': {'cn': 'Nice', 'en': 'Nice'},
    'FTNT': {'cn': 'Fortinet', 'en': 'Fortinet'},
    'CYBR': {'cn': 'CyberArk', 'en': 'CyberArk'},
    'TENB': {'cn': 'Tenable', 'en': 'Tenable'},
    'S': {'cn': 'SentinelOne', 'en': 'SentinelOne'},

    # 小盘/其他
    'AXTI': {'cn': 'AXT', 'en': 'AXT Inc'},
    'HIMX': {'cn': '奇景光电', 'en': 'Himax Technologies'},
    'CEVA': {'cn': 'CEVA', 'en': 'CEVA'},
    'SLAB': {'cn': 'Silicon Labs', 'en': 'Silicon Laboratories'},
    'DIOD': {'cn': 'Diodes', 'en': 'Diodes Inc'},
    'MXL': {'cn': 'MaxLinear', 'en': 'MaxLinear'},
    'SIMO': {'cn': '硅力杰', 'en': 'Silicon Motion'},
    'DQ': {'cn': '大全新能源', 'en': 'Daqo New Energy'},
    'LSCC': {'cn': 'Lattice', 'en': 'Lattice Semiconductor'},
    'VSAT': {'cn': 'ViaSat', 'en': 'Viasat'},
    'SSYS': {'cn': 'Stratasys', 'en': 'Stratasys'},
    'COHR': {'cn': '相干', 'en': 'Coherent'},
    'CHK': {'cn': '切萨皮克', 'en': 'Chesapeake Energy'},
    'MXIM': {'cn': '美信', 'en': 'Maxim Integrated'},
}

def get_stock_name(ticker: str) -> str:
    """获取股票中文名称"""
    info = STOCK_NAMES.get(ticker, {})
    return info.get('cn', '') or info.get('en', ticker[:8])
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

    # LLM-derived factors (higher weight because LLM provides unique insight)
    ('llm_predicted_return', 1, 2.0),  # 正向: 更高预期回报 = 更好
    ('llm_confidence', 1, 0.5),  # 正向: 更高信心 = 更好
    ('llm_risk_score', 1, 1.0),  # 正向: 风险分数已经编码为负权重 = 低风险更好
    ('llm_buy_signal', 1, 1.5),  # 正向: 买入信号更好
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
    """获取历史数据（使用智能缓存和增量更新）"""
    from utils.data_cache import stock_cache

    # 尝试从智能缓存中获取历史数据
    cache_key = f"history:{ticker}:{period1}:{period2}"
    cached_df = stock_cache.get_history(ticker, period1=period1, period2=period2)

    if cached_df is not None:
        logger.debug(f"{ticker}: 从缓存获取历史数据")
        return cached_df

    logger.debug(f"{ticker}: 从 Yahoo Finance 获取历史数据")
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

        # 保存到智能缓存
        stock_cache.set_history(ticker, df, period1=period1, period2=period2)

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
    # Try enhanced version first (with additional factors), fallback to full or lite version
    try:
        from alpha158_enhanced import Alpha158Enhanced
        logger.debug("使用增强版因子库")
        alpha = Alpha158Enhanced(df)
        # 计算所有因子，包括增强因子
        all_factors = alpha.compute_all_factors()
    except ImportError:
        try:
            from alpha158 import Alpha158
            logger.debug("使用完整因子库")
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
        except ImportError:
            from alpha158_lite import Alpha158
            logger.debug("使用轻量级因子库")
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

    # 处理因子数据提取
    factors = {}
    for name, series in all_factors.items():
        if hasattr(series, 'iloc') and len(series) > 0:
            val = series.iloc[-1]
            if pd.notna(val) and np.isfinite(val):
                factors[name.lower()] = float(val)

    return factors

def get_momentum(row, default=0):
    """获取 6 月动量值，支持多种命名方式 (momentum_120d, momentum_6m, momentum_60d)"""
    for col in ['momentum_120d', 'momentum_6m', 'momentum_60d', 'momentum_3m']:
        if col in row.index:
            val = row[col]
            if pd.notna(val):
                return val
    return default

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
    """发送邮件报告 - 移动端优化版"""
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

        # 获取最新价格
        prices = {}
        try:
            for ticker in top20:
                df = get_stock_data(ticker, int((datetime.now() - timedelta(days=7)).timestamp()), int(datetime.now().timestamp()))
                if df is not None and len(df) > 0:
                    prices[ticker] = df['Close'].iloc[-1]
        except Exception as e:
            logger.debug(f"获取价格失败: {e}")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <title>Alpha158 选股报告</title>
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #f0f2f5;
                    padding: 10px;
                    font-size: 14px;
                    line-height: 1.5;
                }}
                .container {{ max-width: 100%; }}
                h1 {{
                    font-size: 18px;
                    color: #1a1a1a;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 8px;
                    margin-bottom: 10px;
                }}
                .date {{ color: #666; font-size: 12px; margin-bottom: 15px; }}
                .summary {{
                    background: #e8f4f8;
                    padding: 10px;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    font-size: 13px;
                }}
                .stock-card {{
                    background: white;
                    border-radius: 8px;
                    margin-bottom: 10px;
                    padding: 12px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    border-left: 4px solid #3498db;
                }}
                .card-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                }}
                .symbol-name {{ display: flex; flex-direction: column; }}
                .symbol {{ font-size: 16px; font-weight: bold; color: #1a1a1a; }}
                .name {{ font-size: 12px; color: #666; }}
                .price {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #3498db;
                }}
                .metrics {{
                    display: flex;
                    gap: 15px;
                    border-top: 1px solid #eee;
                    padding-top: 8px;
                }}
                .metric {{ display: flex; flex-direction: column; }}
                .metric .label {{ font-size: 11px; color: #888; }}
                .metric .value {{ font-size: 14px; font-weight: 500; }}
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
                .rank {{
                    background: #3498db;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    margin-right: 8px;
                }}
                .footer {{
                    margin-top: 20px;
                    padding: 10px;
                    background: #fff3cd;
                    border-radius: 8px;
                    font-size: 11px;
                    color: #856404;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Alpha158 多因子选股报告</h1>
                <p class="date">{timestamp}</p>
                <div class="summary">
                    候选池：{len(df_result)} 只美股科技股 | 因子数：{len(df_result.columns)-1}
                </div>

                <h2 style="font-size:15px;color:#333;margin:15px 0 10px;padding-left:8px;border-left:3px solid #3498db;">🏆 TOP 20 推荐</h2>
        """

        for i, ticker in enumerate(top20):
            row = df_result.loc[ticker]
            mom = get_momentum(row)
            sharpe = row.get('sharpe_ratio_20d', 0)
            vol = row.get('volatility_20d', 0)
            name = get_stock_name(ticker)
            price = prices.get(ticker, 'N/A')
            price_str = f"${price:.2f}" if isinstance(price, (int, float)) else price

            html += f"""
                <div class="stock-card">
                    <div class="card-header">
                        <div class="symbol-name">
                            <span class="symbol"><span class="rank">{i+1}</span>{ticker}</span>
                            <span class="name">{name}</span>
                        </div>
                        <div class="price">{price_str}</div>
                    </div>
                    <div class="metrics">
                        <div class="metric">
                            <span class="label">得分</span>
                            <span class="value">{row['score']:.3f}</span>
                        </div>
                        <div class="metric">
                            <span class="label">6月动量</span>
                            <span class="value {'positive' if mom > 0 else 'negative'}">{mom:+.1f}%</span>
                        </div>
                        <div class="metric">
                            <span class="label">夏普</span>
                            <span class="value">{sharpe:.2f}</span>
                        </div>
                        <div class="metric">
                            <span class="label">波动</span>
                            <span class="value">{vol:.1f}%</span>
                        </div>
                    </div>
                </div>
            """

        html += f"""
                <div class="footer">
                    ⚠️ 免责声明: 本报告由AI生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。
                </div>
            </div>
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
        mom = get_momentum(row)
        sharpe = row.get('sharpe_ratio_20d', 0)
        vol = row.get('volatility_20d', 0)
        logger.info(f"{i+1:<4} {ticker:<8} {row['score']:<10.3f} {mom:<10.1f}% {sharpe:<10.2f} {vol:<10.2f}")


def _print_factor_importance(factor_weights: dict, top_n: int = 20):
    """Print top N important factors."""
    logger.info(f"\n📈 Top {top_n} 重要因子:")
    imp = pd.Series(factor_weights)
    # 对 pandas < 1.1.0 版本兼容的排序方法
    imp = imp.reindex(imp.abs().sort_values(ascending=False).index)
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
    使用 Brave Search 获取真实新闻，再结合 LLM 和 Alpha 因子进行分析
    """
    try:
        # 加载环境变量
        from dotenv import load_dotenv
        load_dotenv()

        # ============ 1. 使用 Brave Search 获取真实新闻 ============
        brave_api_key = os.getenv("BRAVE_API_KEY", "")
        news_content = ""

        if brave_api_key:
            try:
                news_content = _fetch_brave_news(ticker, brave_api_key)
            except Exception as e:
                logger.warning(f"Brave 新闻获取失败：{e}")

        # ============ 2. 构建因子分析信息 ============
        factor_info = ""
        if alpha_factors:
            factor_lines = []
            for key, val in alpha_factors.items():
                if isinstance(val, (int, float)) and val == val:  # not NaN
                    factor_lines.append(f"   - {key}: {val:.4f}" if abs(val) < 1000 else f"   - {key}: {val:.2f}")
            if factor_lines:
                factor_info = "\n\nAlpha 因子数据:\n" + "\n".join(factor_lines[:15])  # 限制最多 15 个因子

        # ============ 3. 构建分析 Prompt ============
        if news_content:
            prompt = f"""作为资深量化分析师，请对 {ticker} 股票进行深度分析。

## 最新新闻

{news_content}

## Alpha 因子数据
{factor_info}

请结合以上新闻和因子数据进行深度分析：

1. **新闻解读**（30%）
   - 从新闻中提取关键信息（财报、产品、并购、监管等）
   - 评估新闻对股价的潜在影响

2. **因子解读**（30%）
   - 从因子数据看，该股票的技术面特征（动量、波动率、趋势等）
   - 新闻与因子信号是否一致

3. **基本面分析**（20%）
   - 基于估值因子的合理性分析
   - 行业对比和竞争地位

4. **投资建议**（20%）
   - 明确的操作建议（买入/持有/卖出）
   - 目标价位和止损位
   - 关键催化剂和风险因素

要求：
- 分析要具体，避免套话
- 基于真实新闻和因子数据，不要编造
- 结论要有可操作性

限制在 500 字以内。"""
        else:
            # 没有新闻时，仅基于因子分析
            prompt = f"""作为资深量化分析师，请对 {ticker} 股票进行深度分析。

## Alpha 因子数据
{factor_info}

请结合以上因子数据和你的专业知识进行分析：

1. **因子解读**（40%）
   - 从因子数据看，该股票的技术面特征（动量、波动率、趋势等）

2. **基本面分析**（30%）
   - 基于你对 {ticker} 的了解，总结其基本面和近期动态
   - 基于估值因子的合理性分析

3. **投资建议**（30%）
   - 明确的操作建议（买入/持有/卖出）
   - 目标价位和止损位
   - 关键催化剂和风险因素

要求：
- 分析要具体，避免套话
- 基于因子数据给出量化角度的解读
- 结论要有可操作性

限制在 400 字以内。"""

        # ============ 4. 调用 LLM 进行分析 ============
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
            # 使用 Qwen API
            base_url = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
            model = os.getenv("DASHSCOPE_MODEL", "qwen3.5-plus")

            logger.debug(f"使用 DASHSCOPE_API_KEY: {api_key[:5]}...")
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

            # 使用代理（如果配置了环境变量）
            proxies = None
            http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
            https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
            if https_proxy or http_proxy:
                proxies = {"http": http_proxy, "https": https_proxy or http_proxy}

            # 重试逻辑：最多重试 3 次，指数退避
            max_retries = 3
            last_error = None
            for attempt in range(max_retries):
                try:
                    # 超时设置: 连接 30 秒，读取 120 秒
                    response = requests.post(
                        url,
                        headers=headers,
                        json=data,
                        timeout=(30, 120),
                        proxies=proxies
                    )

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
                except requests.exceptions.Timeout as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # 1, 2, 4 秒
                        logger.warning(f"   {ticker} API 超时，{wait_time}秒后重试 ({attempt+1}/{max_retries})")
                        import time
                        time.sleep(wait_time)
                    continue
                except Exception as e:
                    return f"无法获取 {ticker} 分析（{str(e)}）"

            return f"无法获取 {ticker} 分析（超时，重试 {max_retries} 次后失败）"
    except Exception as e:
        return f"无法获取 {ticker} 分析（{str(e)}）"


def _fetch_brave_news(ticker: str, api_key: str, count: int = 5) -> str:
    """
    使用 Brave Search API 获取股票新闻

    Args:
        ticker: 股票代码
        api_key: Brave API Key
        count: 获取新闻数量

    Returns:
        新闻内容字符串
    """
    url = "https://api.search.brave.com/res/v1/news/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": f"{ticker} stock news",
        "count": count,
        "freshness": "7d",  # 最近 7 天的新闻
    }

    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()

    result = response.json()
    news_items = result.get("results", [])

    if not news_items:
        return f"未找到 {ticker} 的最近新闻"

    news_content = []
    for i, item in enumerate(news_items, 1):
        title = item.get("title", "N/A")
        description = item.get("description", "N/A")
        url = item.get("url", "N/A")
        date = item.get("age", "N/A")
        source = item.get("language", "unknown").split("-")[0].upper() if item.get("language") else "N/A"

        news_content.append(f"{i}. [{source}] {title}")
        news_content.append(f"   {description}")
        news_content.append(f"   来源：{url} | 时间：{date}")
        news_content.append("")

    return "\n".join(news_content)


def _analyze_top_stocks_with_llm(top_stocks: list, df_result: pd.DataFrame, api_key: str) -> list:
    """Use LLM to analyze and summarize top stocks with alpha factors."""
    # 强制使用 Qwen API
    use_azure = False
    logger.info(f"   使用 Qwen API 获取分析")

    results = []
    for ticker in top_stocks:
        row = df_result.loc[ticker]
        mom = get_momentum(row)
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
            'momentum_120d': mom,
            'sharpe': sharpe,
            'volatility': vol,
            'alpha_factors': alpha_factors,
            'analysis': analysis
        })
        logger.info(f"   ✅ {ticker}: 分析完成")

    return results


def _generate_enhanced_html(top_stocks_analysis: list, df_result: pd.DataFrame, top20: list) -> str:
    """Generate enhanced HTML report with LLM summaries - 移动端优化版"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 获取最新价格
    prices = {}
    try:
        for ticker in top20[:10]:  # 只获取前10只的价格
            df = get_stock_data(ticker, int((datetime.now() - timedelta(days=7)).timestamp()), int(datetime.now().timestamp()))
            if df is not None and len(df) > 0:
                prices[ticker] = df['Close'].iloc[-1]
    except Exception as e:
        logger.debug(f"获取价格失败: {e}")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Alpha158 选股报告</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f0f2f5;
                padding: 10px;
                font-size: 14px;
                line-height: 1.5;
            }}
            .container {{ max-width: 100%; }}
            h1 {{
                font-size: 18px;
                color: #1a1a1a;
                border-bottom: 2px solid #3498db;
                padding-bottom: 8px;
                margin-bottom: 10px;
            }}
            h2 {{
                font-size: 15px;
                color: #333;
                margin: 15px 0 10px;
                padding-left: 8px;
                border-left: 3px solid #3498db;
            }}
            .date {{ color: #666; font-size: 12px; margin-bottom: 15px; }}
            .summary {{
                background: #e8f4f8;
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 15px;
                font-size: 13px;
            }}
            .stock-card {{
                background: white;
                border-radius: 8px;
                margin-bottom: 10px;
                padding: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                border-left: 4px solid #3498db;
            }}
            .card-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }}
            .symbol-name {{ display: flex; flex-direction: column; }}
            .symbol {{ font-size: 16px; font-weight: bold; color: #1a1a1a; }}
            .name {{ font-size: 12px; color: #666; }}
            .price {{
                font-size: 18px;
                font-weight: bold;
                color: #3498db;
            }}
            .metrics {{
                display: flex;
                gap: 15px;
                border-top: 1px solid #eee;
                padding-top: 8px;
            }}
            .metric {{ display: flex; flex-direction: column; }}
            .metric .label {{ font-size: 11px; color: #888; }}
            .metric .value {{ font-size: 14px; font-weight: 500; }}
            .positive {{ color: #28a745; }}
            .negative {{ color: #dc3545; }}
            .rank {{
                background: #3498db;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 12px;
                margin-right: 8px;
            }}
            .analysis-card {{
                background: white;
                border-radius: 8px;
                margin-bottom: 10px;
                padding: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                border-left: 4px solid #28a745;
            }}
            .analysis-title {{
                font-size: 16px;
                font-weight: bold;
                color: #1a1a1a;
                margin-bottom: 8px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .analysis-metrics {{
                display: flex;
                gap: 15px;
                margin-bottom: 10px;
                padding-bottom: 8px;
                border-bottom: 1px solid #eee;
            }}
            .analysis-content {{
                background: #f8f9fa;
                padding: 10px;
                border-radius: 6px;
                font-size: 13px;
                line-height: 1.6;
            }}
            .recommendation-box {{
                background: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 4px;
                padding: 8px 12px;
                margin-bottom: 10px;
                color: #155724;
                font-weight: 500;
            }}
            .footer {{
                margin-top: 20px;
                padding: 10px;
                background: #fff3cd;
                border-radius: 8px;
                font-size: 11px;
                color: #856404;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Alpha158 多因子选股报告</h1>
            <p class="date">{timestamp}</p>
            <div class="summary">
                候选池：{len(df_result)} 只美股科技股 | 因子数：{len(df_result.columns)-1}
            </div>

            <h2>🏆 TOP 20 推荐</h2>
    """

    for i, ticker in enumerate(top20):
        row = df_result.loc[ticker]
        mom = get_momentum(row)
        sharpe = row.get('sharpe_ratio_20d', 0)
        vol = row.get('volatility_20d', 0)
        name = get_stock_name(ticker)
        price = prices.get(ticker, 'N/A')
        price_str = f"${price:.2f}" if isinstance(price, (int, float)) else price

        html += f"""
            <div class="stock-card">
                <div class="card-header">
                    <div class="symbol-name">
                        <span class="symbol"><span class="rank">{i+1}</span>{ticker}</span>
                        <span class="name">{name}</span>
                    </div>
                    <div class="price">{price_str}</div>
                </div>
                <div class="metrics">
                    <div class="metric">
                        <span class="label">得分</span>
                        <span class="value">{row['score']:.3f}</span>
                    </div>
                    <div class="metric">
                        <span class="label">6月动量</span>
                        <span class="value {'positive' if mom > 0 else 'negative'}">{mom:+.1f}%</span>
                    </div>
                    <div class="metric">
                        <span class="label">夏普</span>
                        <span class="value">{sharpe:.2f}</span>
                    </div>
                    <div class="metric">
                        <span class="label">波动</span>
                        <span class="value">{vol:.1f}%</span>
                    </div>
                </div>
            </div>
        """

    html += """
            <h2>📰 TOP 5 股票深度分析</h2>
    """

    # Add detailed analysis for top 5 stocks
    for stock in top_stocks_analysis[:5]:
        ticker = stock['ticker']
        analysis = stock.get('analysis', '暂无分析')
        name = get_stock_name(ticker)
        price = prices.get(ticker, 'N/A')
        price_str = f"${price:.2f}" if isinstance(price, (int, float)) else price

        # Extract operation recommendation from analysis text
        import re
        recommendation_text = '暂无'
        lines = analysis.splitlines()
        found = False

        # Strategy 1: Look for "操作建议: ..." anywhere in text
        matches = re.search(r'(操作建议|投资建议)[:：]\s*(.+?)(?=\n\s*###|$)', analysis, re.DOTALL)
        if matches:
            candidate = matches.group(2).strip()
            if candidate and not candidate.startswith('###') and len(candidate) > 2:
                recommendation_text = candidate
                found = True

        # Strategy 2: Line by line search
        if not found:
            for i, line in enumerate(lines):
                if '操作建议' in line or '投资建议' in line:
                    # Check if the recommendation is on this line after the label
                    matches = re.search(r'(操作建议|投资建议)[:：]\s*(.+)', line)
                    if matches and matches.group(2).strip():
                        candidate = matches.group(2).strip()
                        if not candidate.startswith('###'):
                            recommendation_text = candidate
                            found = True
                            break
                    # If not on this line, check next 1-2 lines
                    for j in range(i+1, min(i+3, len(lines))):
                        candidate = lines[j].strip()
                        if candidate and not candidate.startswith('###'):
                            recommendation_text = candidate
                            found = True
                            break
                if found:
                    break

        # Strategy 3: Look for heading like "### 投资建议" and get next line
        if not found:
            for i, line in enumerate(lines):
                if '###' in line and ('投资建议' in line or '操作建议' in line):
                    for j in range(i+1, min(i+3, len(lines))):
                        candidate = lines[j].strip()
                        if candidate:
                            # Remove any bullet points or extra markers
                            candidate = re.sub(r'^[*-]\s*', '', candidate)
                            recommendation_text = candidate
                            found = True
                            break
                if found:
                    break

        # Fallback: just get any line containing the action keywords
        if not found:
            for line in lines:
                if any(keyword in line for keyword in ['买入', '持有', '卖出']):
                    recommendation_text = line.strip()
                    found = True
                    break

        html += f"""
        <div class="analysis-card">
            <div class="analysis-title">
                <span>{ticker} <span style="font-size:12px;color:#666;font-weight:normal;">{name}</span></span>
                <span style="color:#3498db;">{price_str}</span>
            </div>
            <div class="analysis-metrics">
                <div class="metric">
                    <span class="label">得分</span>
                    <span class="value">{stock['score']:.3f}</span>
                </div>
                <div class="metric">
                    <span class="label">6月动量</span>
                    <span class="value {'positive' if stock['momentum_120d'] > 0 else 'negative'}">{stock['momentum_120d']:+.1f}%</span>
                </div>
                <div class="metric">
                    <span class="label">夏普</span>
                    <span class="value">{stock['sharpe']:.2f}</span>
                </div>
                <div class="metric">
                    <span class="label">波动</span>
                    <span class="value">{stock['volatility']:.1f}%</span>
                </div>
            </div>
            <div class="analysis-content">
                <strong>🤖 LLM 分析：</strong><br>
                <div class="recommendation-box">
                    <strong>💡 操作建议：</strong> {recommendation_text}
                </div>
                <hr>
                {analysis.replace(chr(10), '<br>')}
            </div>
        </div>
        """

    html += """
            <div class="footer">
                ⚠️ 免责声明: 本报告由AI生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。
            </div>
        </div>
    </body>
    </html>
    """

    return html


def run_analysis(stock_pool: list = TECH_TOP_50, period_days: int = 252, use_trading_days: bool = True, use_llm_factor: bool = False, enable_archive: bool = True):
    """
    运行分析

    Args:
        stock_pool: 股票池列表
        period_days: 时间周期（天数）
        use_trading_days: 如果为 True，period_days 被视为交易日，自动转换为日历日
        use_llm_factor: 如果为 True，启用 LLM 预测因子集成（将 LLM 预测作为额外因子加入排名）
        enable_archive: 如果为 True，将推荐结果存档用于历史表现跟踪
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

    if use_llm_factor:
        if not LLM_FACTOR_AVAILABLE:
            logger.warning("⚠️  LLM 因子模块不可用，将跳过 LLM 因子集成")
            use_llm_factor = False
        else:
            logger.info("✅ LLM 因子集成已启用 - LLM 预测将作为额外因子参与排名")

    period2 = int(datetime.now().timestamp())
    period1 = int((datetime.now() - timedelta(days=calendar_days)).timestamp())

    logger.info(f"\n📥 获取数据 ({calendar_days}天)...")
    all_factors = _fetch_all_stock_factors(stock_pool, period1, period2)

    if not all_factors:
        logger.error("\n❌ 无有效数据")
        return None

    logger.info(f"\n✅ 成功获取 {len(all_factors)}/{len(stock_pool)} 只股票数据")

    # Integrate LLM factors if enabled
    if use_llm_factor and LLM_FACTOR_AVAILABLE and get_llm_factors_sync is not None:
        symbols = list(all_factors.keys())
        logger.info(f"\n🤖 获取 LLM 预测因子（{len(symbols)} 只股票）...")
        try:
            llm_factors_dict = get_llm_factors_sync(symbols)
            if llm_factors_dict:
                # Merge LLM factors into all_factors
                for symbol, llm_factors in llm_factors_dict.items():
                    if symbol in all_factors:
                        all_factors[symbol].update(llm_factors)
                logger.info(f"✅ 成功集成 {len(llm_factors_dict)} 个 LLM 因子")
            else:
                logger.warning("⚠️  未获取到任何 LLM 因子，将跳过 LLM 集成")
        except Exception as e:
            logger.error(f"❌ LLM 因子获取失败: {e}，将跳过 LLM 集成")

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

    # Archive recommendation for performance tracking (if enabled)
    if enable_archive:
        try:
            from utils.performance_tracker import performance_tracker
            archive_path = performance_tracker.archive_recommendation(df_result, top_n=20, llm_factors_used=use_llm_factor)
            if archive_path:
                logger.info(f"\n💾 推荐已存档用于历史表现跟踪: {archive_path}")
        except Exception as e:
            logger.warning(f"\n⚠️  推荐存档失败: {e}")

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
    import argparse

    parser = argparse.ArgumentParser(description="Alpha158 多因子选股系统")
    parser.add_argument("--stock-pool", type=str, help="股票池文件路径（CSV 格式）")
    parser.add_argument("--period-days", type=int, default=252, help="时间周期（天数）")
    parser.add_argument("--use-trading-days", action="store_true", help="将 period-days 视为交易日而非日历日")
    parser.add_argument("--use-llm-factor", action="store_true", help="启用 LLM 预测因子集成（将 LLM 预测作为额外因子加入排名）")
    parser.add_argument("--no-archive", action="store_true", help="不存档推荐结果（跳过历史表现跟踪）")
    parser.add_argument("--backtest", action="store_true", help="运行回测（walk-forward 验证）")
    parser.add_argument("--backtest-start-year", type=int, default=2020, help="回测开始年份")
    parser.add_argument("--backtest-end-year", type=int, default=2026, help="回测结束年份")
    parser.add_argument("--rebalance-days", type=int, default=21, help="再平衡周期（天数）")
    parser.add_argument("--backtest-top-n", type=int, default=10, help="每期选择 top N 只股票")
    parser.add_argument("--transaction-cost", type=float, default=10, help="交易成本（基点，1bps=0.01%）")
    parser.add_argument("--log-level", type=str, default="INFO", help="日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）")
    parser.add_argument("--limit", type=int, default=None, help="只运行前 N 只股票（用于分批抓取提升成功率）")

    args = parser.parse_args()

    # 配置日志
    configure_logging(args.log_level)

    # 处理股票池
    stock_pool = TECH_TOP_50  # 默认使用TOP 50核心科技股票
    if args.stock_pool:
        try:
            import pandas as pd
            df_pool = pd.read_csv(args.stock_pool)
            stock_pool = df_pool['ticker'].tolist() if 'ticker' in df_pool.columns else df_pool.iloc[:, 0].tolist()
            logger.info(f"从文件加载股票池：{len(stock_pool)} 只股票")
        except Exception as e:
            logger.error(f"股票池文件加载失败：{e}")
            logger.info("使用默认股票池")

    # Limit to first N stocks if requested (for batch processing to improve success rate)
    if args.limit is not None and args.limit > 0 and args.limit < len(stock_pool):
        logger.info(f"⚠️  限制只运行前 {args.limit}/{len(stock_pool)} 只股票（分批抓取）")
        stock_pool = stock_pool[:args.limit]

    # Check if running backtest
    if args.backtest:
        # Run backtest instead of normal analysis
        from datetime import datetime
        from backtest_framework import BacktestFramework

        start_date = datetime(args.backtest_start_year, 1, 1)
        end_date = datetime(args.backtest_end_year, 1, 1)

        logger.info(f"\n🚀 Starting walk-forward backtest from {start_date.date()} to {end_date.date()}")

        backtest = BacktestFramework(
            stock_pool=stock_pool,
            start_date=start_date,
            end_date=end_date,
            rebalance_days=args.rebalance_days,
            top_n_stocks=args.backtest_top_n,
            transaction_cost_bps=args.transaction_cost
        )

        results = backtest.run_walk_forward()
        backtest.save_results()
        report_path = backtest.generate_html_report()

        logger.info(f"\n✅ Backtest completed!")
        logger.info(f"📊 Report saved to: {report_path}")
        print(f"\n✅ Backtest completed!")
        print(f"📊 Report saved to: {report_path}")
    else:
        # Run normal analysis
        df_result = run_analysis(
            stock_pool=stock_pool,
            period_days=args.period_days,
            use_trading_days=args.use_trading_days,
            use_llm_factor=args.use_llm_factor,
            enable_archive=not args.no_archive
        )

