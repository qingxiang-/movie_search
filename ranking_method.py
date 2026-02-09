#!/usr/bin/env python3
"""
Alpha158 排名法多因子选股系统 - 使用全部87个因子
✅ 基于因子得分的传统量化方法
✅ 支持邮件发送
✅ TOP 5 股票 LLM 深度分析（基于 Playwright 实时新闻搜索）
"""
import sys
sys.path.insert(0, '/Users/wangqingxiang/.openclaw/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import warnings
import json
import asyncio
from bs4 import BeautifulSoup
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

async def fetch_stock_news(symbol: str, max_news: int = None) -> list:
    """
    使用 Playwright 从互联网获取股票最新新闻（优化版：获取第一屏所有新闻）

    Args:
        symbol: 股票代码
        max_news: 最多获取新闻数量（None表示获取所有）

    Returns:
        新闻列表 [{"title": "标题", "source": "来源", "time": "时间", "url": "链接"}]
    """
    from playwright.async_api import async_playwright
    import random

    news_list = []

    # 随机 User-Agent 避免被检测
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]

    try:
        async with async_playwright() as p:
            # 启动浏览器（无头模式）
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']  # 避免被检测为机器人
            )
            context = await browser.new_context(
                user_agent=random.choice(user_agents),
                viewport={'width': 1920, 'height': 1080},
                locale='en-US'
            )
            page = await context.new_page()

            # 添加随机延迟
            await asyncio.sleep(random.uniform(1, 2))

            # 构建搜索 URL（使用 Google Finance 新闻）
            search_url = f"https://www.google.com/search?q={symbol}+stock+news&tbm=nws"

            try:
                await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(2, 3))  # 随机等待

                # 获取页面内容
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # 尝试多种选择器，获取第一屏所有新闻
                selectors = ['div.SoaBEf', 'div.Gx5Zad', 'div.xpd', 'div.BVG0Nb']
                found_results = False

                for selector in selectors:
                    results = soup.select(selector)
                    if results:
                        # 获取所有结果，不限制数量
                        for result in results:
                            # 如果设置了max_news限制
                            if max_news and len(news_list) >= max_news:
                                break

                            try:
                                # 尝试多种标题选择器
                                title_elem = (result.select_one('div.MBeuO') or
                                             result.select_one('h3') or
                                             result.select_one('a'))
                                title = title_elem.get_text(strip=True) if title_elem else ""

                                # 提取来源和时间
                                source_elem = result.select_one('div.NE6WLe')
                                source_time = source_elem.get_text(strip=True) if source_elem else ""

                                # 提取链接
                                link_elem = result.select_one('a')
                                url = link_elem.get('href', '') if link_elem else ""

                                if title and len(title) > 10:
                                    # 解析来源和时间（格式通常为 "来源 - 时间"）
                                    parts = source_time.split(' - ')
                                    source = parts[0] if len(parts) > 0 else "Unknown"
                                    time_str = parts[1] if len(parts) > 1 else source_time

                                    news_list.append({
                                        "title": title[:200],
                                        "source": source[:50],
                                        "time": time_str[:50],
                                        "url": url[:500]
                                    })
                            except:
                                continue

                        if news_list:
                            found_results = True
                            break

                # 备用方案：如果上述选择器都没找到，尝试搜索所有带链接的元素
                if not found_results:
                    all_links = soup.find_all('a', href=True)
                    for link in all_links:
                        # 如果设置了max_news限制
                        if max_news and len(news_list) >= max_news:
                            break

                        href = link.get('href', '')
                        title = link.get_text(strip=True)

                        # 过滤掉不是新闻的链接
                        if (title and len(title) > 15 and len(title) < 200 and
                            'google' not in href and href.startswith('http')):
                            news_list.append({
                                "title": title[:200],
                                "source": "",
                                "time": "",
                                "url": href[:500]
                            })

            except Exception as e:
                print(f"      页面加载失败: {str(e)[:50]}")

            await browser.close()

    except Exception as e:
        print(f"      Playwright 执行失败: {str(e)[:50]}")

    return news_list


def analyze_top5_with_llm(top5_symbols: list, df_result: pd.DataFrame) -> list:
    """
    对 TOP 5 股票进行 LLM 深度分析（基于 Playwright 实时新闻搜索）

    Args:
        top5_symbols: TOP 5 股票代码列表
        df_result: 包含所有因子数据的 DataFrame

    Returns:
        分析结果列表，每个元素包含 symbol, analysis_html
    """
    import os

    # 读取 .env 文件
    env_path = '/Users/wangqingxiang/source/movie_search/.env'
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()

    # Azure OpenAI 配置
    azure_api_key = env_vars.get("AZURE_OPENAI_API_KEY", "")
    azure_endpoint = env_vars.get("AZURE_OPENAI_ENDPOINT", "")
    azure_api_version = env_vars.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    azure_deployment = env_vars.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4")

    print("\n" + "="*60)
    print("🤖 开始 TOP 5 股票 LLM 深度分析（基于实时新闻搜索）...")
    print("="*60)

    results = []

    for i, symbol in enumerate(top5_symbols, 1):
        print(f"\n[{i}/5] 分析 {symbol}...")

        try:
            # 获取因子数据
            row = df_result.loc[symbol]
            factor_summary = f"""
Alpha158 因子得分: {row['score']:.3f}
6月动量: {row.get('momentum_6m', 0):.1f}%
20日收益: {row.get('return_20d', 0):.1f}%
夏普比率: {row.get('sharpe_ratio_20d', 0):.2f}
索提诺比率: {row.get('sortino_ratio_20d', 0):.2f}
波动率: {row.get('volatility_20d', 0):.2f}
最大回撤: {abs(row.get('drawdown_20d', 0)):.1f}%
成交比: {row.get('volume_ratio_20', 0)/100:.2f}
趋势强度: {row.get('trend_strength', 0):.2f}
"""

            # 使用 Playwright 获取实时新闻（获取第一屏所有新闻）
            print(f"   📡 正在搜索 {symbol} 最新新闻...")
            try:
                # 运行异步函数获取新闻（不限制数量，获取第一屏所有新闻）
                loop = asyncio.get_event_loop()
                news_list = loop.run_until_complete(fetch_stock_news(symbol))

                if news_list:
                    print(f"   ✅ 获取到 {len(news_list)} 条最新新闻")
                    # 使用所有新闻构建摘要
                    news_summary = "\n".join([
                        f"- [{n['source']}] {n['title']} ({n['time']})"
                        for n in news_list
                    ])
                else:
                    print(f"   ⚠️  未获取到新闻，使用 LLM 知识库")
                    news_summary = "（未能获取实时新闻，基于 LLM 知识库分析）"

            except Exception as e:
                print(f"   ⚠️  新闻搜索失败: {str(e)[:50]}，使用 LLM 知识库")
                news_summary = "（实时新闻获取失败，基于 LLM 知识库分析）"

            # 构建分析提示（包含实时新闻）
            prompt = f"""请作为专业股票分析师，基于以下信息对 {symbol} 股票进行深度分析：

【量化因子数据】
{factor_summary}

【最新市场动态】（第一屏所有新闻）
{news_summary}

【任务要求】
1. 基于最新市场动态和量化因子数据进行综合分析
2. 如果有实时新闻，请重点分析新闻对股价的影响
3. 输出格式要求 JSON：
{{
    "overview": "公司简要介绍（2-3句话）",
    "latest_news": ["最新动态1", "最新动态2", "最新动态3"],
    "highlights": ["投资亮点1", "投资亮点2", "投资亮点3"],
    "risks": ["风险提示1", "风险提示2"],
    "outlook": "后市展望（1-2句话）",
    "recommendation": "买入/持有/卖出"
}}

请确保分析专业、客观，并紧密结合最新市场动态。"""

            # 调用 Azure OpenAI API
            url = f"{azure_endpoint.rstrip('/')}/openai/deployments/{azure_deployment}/chat/completions?api-version={azure_api_version}"
            headers = {
                "api-key": azure_api_key,
                "Content-Type": "application/json"
            }
            data = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5
            }

            response = requests.post(url, json=data, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()

            # 解析响应
            content = result["choices"][0]["message"]["content"]

            # 解析 JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            analysis = json.loads(content)
            analysis['symbol'] = symbol
            analysis['rank'] = i
            results.append(analysis)
            print(f"   ✅ 分析完成")

        except Exception as e:
            print(f"   ❌ 分析失败: {e}")

            # 重试一次（sleep 5秒）
            if '已重试' not in str(e):  # 避免无限重试
                print(f"   🔄 5秒后重试...")
                import time
                time.sleep(5)

                try:
                    response = requests.post(url, json=data, headers=headers, timeout=60)
                    response.raise_for_status()
                    result = response.json()

                    content = result["choices"][0]["message"]["content"]

                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()

                    analysis = json.loads(content)
                    analysis['symbol'] = symbol
                    analysis['rank'] = i
                    results.append(analysis)
                    print(f"   ✅ 重试成功")
                except Exception as retry_e:
                    print(f"   ❌ 重试失败: {retry_e}")
                    # 创建占位分析
                    results.append({
                        'symbol': symbol,
                        'rank': i,
                        'overview': f'{symbol} 分析暂时不可用',
                        'latest_news': ['数据获取中...'],
                        'highlights': ['量化因子表现优异'],
                        'risks': ['请稍后重试'],
                        'outlook': '待更新',
                        'recommendation': '持有'
                    })
            else:
                # 创建占位分析
                results.append({
                    'symbol': symbol,
                    'rank': i,
                    'overview': f'{symbol} 分析暂时不可用',
                    'latest_news': ['数据获取中...'],
                    'highlights': ['量化因子表现优异'],
                    'risks': ['请稍后重试'],
                    'outlook': '待更新',
                    'recommendation': '持有'
                })

    print(f"\n✅ TOP 5 分析完成，成功 {len(results)}/5")
    return results

def send_email_report(df_result: pd.DataFrame, top20: list, top5_analysis: list = None):
    """发送邮件报告"""
    try:
        sys.path.insert(0, '/Users/wangqingxiang/source/movie_search')
        from utils.email_sender import EmailSender

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; font-size: 12px; }}
                h1 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; font-size: 11px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                th {{ background-color: #3498db; color: white; font-weight: bold; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .buy {{ color: green; font-weight: bold; }}
                .summary {{ background-color: #ecf0f1; padding: 15px; margin: 20px 0; }}
                .positive {{ color: #27ae60; }}
                .negative {{ color: #e74c3c; }}
            </style>
        </head>
        <body>
            <h1>📊 Alpha158 多因子选股报告 (147因子)</h1>
            <p>生成时间: {timestamp}</p>
            <p>候选池: {len(df_result)} 只美股科技股 | 因子数: {len(df_result.columns)-1}</p>

            <div class="summary">
                <h3>🏆 TOP 20 推荐</h3>
                <table>
                    <tr>
                        <th>排名</th>
                        <th>代码</th>
                        <th>综合得分</th>
                        <th>6月动量</th>
                        <th>20日收益</th>
                        <th>夏普</th>
                        <th>索提诺</th>
                        <th>斯特林</th>
                        <th>卡尔马</th>
                        <th>波动率</th>
                        <th>最大回撤</th>
                        <th>成交比</th>
                        <th>趋势强度</th>
                    </tr>
        """

        for i, ticker in enumerate(top20):
            row = df_result.loc[ticker]
            mom = row.get('momentum_6m', row.get('momentum_3m', 0))
            ret = row.get('return_20d', 0)
            sharpe = row.get('sharpe_ratio_20d', 0)
            sortino = row.get('sortino_ratio_20d', 0)
            sterling = row.get('sterling_ratio_20d', 0)
            calmar = row.get('calmar_ratio_60d', 0)  # 修复: calmar_ratio -> calmar_ratio_60d
            vol = row.get('volatility_20d', 0)
            max_dd = row.get('drawdown_20d', 0)
            vol_ratio = row.get('volume_ratio_20', 0) / 100  # 修复: 除以100显示倍数
            trend = row.get('trend_strength', 0)

            # 颜色标记
            mom_class = 'positive' if mom > 0 else 'negative'
            ret_class = 'positive' if ret > 0 else 'negative'
            dd_class = 'negative' if max_dd < -5 else ''  # 只有回撤>5%才标红

            html += f"""
                    <tr>
                        <td>{i+1}</td>
                        <td class="buy">{ticker}</td>
                        <td><strong>{row['score']:.3f}</strong></td>
                        <td class="{mom_class}">{mom:.1f}%</td>
                        <td class="{ret_class}">{ret:.1f}%</td>
                        <td>{sharpe:.2f}</td>
                        <td>{sortino:.2f}</td>
                        <td>{sterling:.2f}</td>
                        <td>{calmar:.2f}</td>
                        <td>{vol:.2f}</td>
                        <td class="{dd_class}">{abs(max_dd):.1f}%</td>
                        <td>{vol_ratio:.2f}</td>
                        <td>{trend:.2f}</td>
                    </tr>"""

        html += f"""
                </table>
            </div>

            <div class="summary">
                <h4>📌 指标说明</h4>
                <ul style="font-size: 11px;">
                    <li><strong>6月动量</strong>: 过去6个月价格涨幅，正值表示上涨趋势</li>
                    <li><strong>20日收益</strong>: 过去20个交易日收益率</li>
                    <li><strong>夏普/索提诺/斯特林/卡尔马</strong>: 风险调整后收益指标，数值越高越好</li>
                    <li><strong>波动率</strong>: 价格波动幅度，数值越小越稳定</li>
                    <li><strong>最大回撤</strong>: 20日内从高点的最大跌幅</li>
                    <li><strong>成交比</strong>: 近期成交量/20日均量，>1 表示放量</li>
                    <li><strong>趋势强度</strong>: ADX指标，数值越大趋势越明显</li>
                </ul>
            </div>
        """

        # 添加 TOP 5 深度分析区域
        if top5_analysis:
            html += f"""
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-left: 5px solid #007bff;">
                <h3 style="color: #007bff; margin-top: 0;">🤖 TOP 5 股票 AI 深度分析</h3>
        """

            for analysis in top5_analysis:
                rec_color = '#28a745' if analysis.get('recommendation') == '买入' else '#ffc107' if analysis.get('recommendation') == '持有' else '#dc3545'

                html += f"""
                <div style="background: white; padding: 15px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h4 style="color: #333; margin-top: 0;">
                        #{analysis['rank']} {analysis['symbol']} -
                        <span style="background: {rec_color}; color: white; padding: 3px 10px; border-radius: 4px; font-size: 12px;">
                            {analysis.get('recommendation', 'N/A')}
                        </span>
                    </h4>

                    <div style="margin: 10px 0;">
                        <strong style="color: #555;">📋 公司概览</strong>
                        <p style="margin: 5px 0; font-size: 13px; color: #666;">{analysis.get('overview', 'N/A')}</p>
                    </div>

                    <div style="margin: 10px 0;">
                        <strong style="color: #555;">📰 最新动态</strong>
                        <ul style="margin: 5px 0; padding-left: 20px; font-size: 13px;">
                """
                for news in analysis.get('latest_news', [])[:3]:
                    html += f"<li>{news}</li>\n"

                html += f"""
                        </ul>
                    </div>

                    <div style="margin: 10px 0;">
                        <strong style="color: #28a745;">💡 投资亮点</strong>
                        <ul style="margin: 5px 0; padding-left: 20px; font-size: 13px;">
                """
                for highlight in analysis.get('highlights', [])[:3]:
                    html += f"<li>{highlight}</li>\n"

                html += f"""
                        </ul>
                    </div>

                    <div style="margin: 10px 0;">
                        <strong style="color: #dc3545;">⚠️ 风险提示</strong>
                        <ul style="margin: 5px 0; padding-left: 20px; font-size: 13px;">
                """
                for risk in analysis.get('risks', [])[:2]:
                    html += f"<li>{risk}</li>\n"

                html += f"""
                        </ul>
                    </div>

                    <div style="margin: 10px 0;">
                        <strong style="color: #007bff;">🔮 后市展望</strong>
                        <p style="margin: 5px 0; font-size: 13px; color: #666;">{analysis.get('outlook', 'N/A')}</p>
                    </div>
                </div>
        """

            html += f"""
            </div>
        """

        html += f"""
            <hr>
            <p><small>Generated by Alpha158 Ranking System (147 factors) + AI Analysis</small></p>
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
    df_result.to_csv('ranking_top100.csv')
    print(f"\n💾 结果已保存: ranking_top100.csv")

    # 对 TOP 5 进行 LLM 深度分析
    top5 = top20[:5]
    top5_analysis = analyze_top5_with_llm(top5, df_result)

    # 发送邮件（包含 TOP 5 分析）
    html = send_email_report(df_result, top20, top5_analysis)
    if html:
        with open('ranking_report.html', 'w') as f:
            f.write(html)
        print(f"📧 邮件报告已保存: ranking_report.html")

    return df_result

if __name__ == "__main__":
    df_result = run_analysis()
