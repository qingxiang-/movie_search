"""
Performance Tracker - Track historical recommendation performance
Archives every recommendation run and tracks subsequent performance after N days/months.

This helps evaluate how well the system performs over time.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Archive directory
DEFAULT_ARCHIVE_DIR = Path(__file__).parent.parent / "data" / "history"

class PerformanceTracker:
    """
    Track and archive stock recommendation performance over time.

    Features:
    - Archive recommendation results with timestamp
    - Calculate subsequent performance after 1m, 3m, 6m
    - Compare with S&P 500 benchmark
    - Generate performance report HTML
    """

    def __init__(self, archive_dir: str = None):
        if archive_dir is None:
            archive_dir = DEFAULT_ARCHIVE_DIR
        self.archive_dir = Path(archive_dir)
        self._ensure_archive_dir()

    def _ensure_archive_dir(self):
        """Create archive directory if it doesn't exist."""
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _generate_archive_path(self) -> Path:
        """Generate archive file path with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recommendation_{timestamp}.json"
        return self.archive_dir / filename

    @staticmethod
    def _prepare_archive_data(
        df_result: pd.DataFrame,
        top_n: int = 20,
        llm_factors_used: bool = False,
        factors_used: Optional[List[str]] = None
    ) -> Dict:
        """
        Prepare archive data structure from result dataframe.

        Args:
            df_result: Result dataframe from ranking_method
            top_n: Number of top stocks to archive
            llm_factors_used: Whether LLM factors were used
            factors_used: List of factors used in this run

        Returns:
            Archive data dictionary ready to be saved
        """
        top_stocks = []
        for rank, (symbol, row) in enumerate(df_result.head(top_n).iterrows(), 1):
            stock_data = {
                'rank': rank,
                'symbol': symbol,
                'score': float(row.get('score', 0.0)),
                'price_at_recommendation': float(row.get('latest_price', row.get('close', 0.0)))
            }
            # Add factor exposure if available
            factors = {}
            for col in df_result.columns:
                if col not in ['score', 'rank', 'latest_price', 'name']:
                    try:
                        factors[col] = float(row[col])
                    except:
                        pass
            stock_data['factors'] = factors
            top_stocks.append(stock_data)

        archive = {
            'timestamp': datetime.now().isoformat(),
            'date_str': datetime.now().strftime("%Y-%m-%d"),
            'candidate_pool_size': len(df_result),
            'top_n': len(top_stocks),
            'llm_factors_used': llm_factors_used,
            'factors_used': factors_used if factors_used else list(df_result.columns),
            'top_stocks': top_stocks
        }

        return archive

    def archive_recommendation(
        self,
        df_result: pd.DataFrame,
        top_n: int = 20,
        llm_factors_used: bool = False
    ) -> str:
        """
        Archive the current recommendation with timestamp.

        Args:
            df_result: Result dataframe from ranking
            top_n: Number of top stocks to archive
            llm_factors_used: Whether LLM factors were used

        Returns:
            Path to the saved archive file
        """
        factors_used = list(df_result.columns)
        archive_data = self._prepare_archive_data(
            df_result, top_n, llm_factors_used, factors_used
        )

        archive_path = self._generate_archive_path()

        try:
            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump(archive_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Recommendation archived to {archive_path}")
            return str(archive_path)
        except Exception as e:
            logger.error(f"Failed to archive recommendation: {e}")
            return ""

    def list_archives(self) -> List[Path]:
        """List all archived recommendation files."""
        return sorted(list(self.archive_dir.glob("recommendation_*.json")))

    def load_archive(self, archive_path: Path) -> Optional[Dict]:
        """Load an archive from file."""
        try:
            with open(archive_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load archive {archive_path}: {e}")
            return None

    @staticmethod
    def get_stock_price_at_date(symbol: str, target_date: datetime) -> Optional[float]:
        """
        Fetch historical price for symbol at target date using cached data.

        Uses the same Yahoo Finance API as ranking_method.

        Args:
            symbol: Stock symbol
            target_date: Target date to get price

        Returns:
            Closing price at or near target date, or None if unavailable
        """
        from ranking_method import get_stock_data

        # Get data for a range that includes target_date
        start_date = target_date - timedelta(days=10)
        end_date = target_date + timedelta(days=10)
        period1 = int(start_date.timestamp())
        period2 = int(end_date.timestamp())

        try:
            df = get_stock_data(symbol, period1, period2)
            if df is None or df.empty:
                return None

            # Find the closest date on or after target_date
            df_target = df[df.index >= target_date]
            if df_target.empty:
                df_target = df[df.index <= target_date]

            if df_target.empty:
                return None

            # Return closing price
            return float(df_target['close'].iloc[0])

        except Exception as e:
            logger.warning(f"Could not get price for {symbol} at {target_date}: {e}")
            return None

    def calculate_performance_archived(self, archive_path: Path) -> Optional[Dict]:
        """
        Calculate performance of an archived recommendation.

        For each top N stock, calculates return after 1m, 3m, 6m.
        Compares with S&P 500 (SPY) return over the same period.

        Args:
            archive_path: Path to the archive file

        Returns:
            Performance dictionary with calculated metrics
        """
        archive = self.load_archive(archive_path)
        if archive is None:
            return None

        rec_date = datetime.fromisoformat(archive['timestamp'])
        results = []
        sp500_returns = {}

        # Calculate returns for different horizons
        horizons = [
            ('1m', 30),
            ('3m', 90),
            ('6m', 180)
        ]

        # Get SPY (S&P 500 ETF) prices for benchmark
        spy_price_start = self.get_stock_price_at_date('SPY', rec_date)

        for horizon_name, days in horizons:
            target_date = rec_date + timedelta(days=days)
            if target_date > datetime.now():
                # Not enough time passed yet
                continue

            spy_price_end = self.get_stock_price_at_date('SPY', target_date)
            if spy_price_start and spy_price_end:
                sp500_return = (spy_price_end - spy_price_start) / spy_price_start * 100
                sp500_returns[horizon_name] = sp500_return
            else:
                sp500_returns[horizon_name] = None

        # Calculate returns for each stock
        for stock in archive['top_stocks']:
            symbol = stock['symbol']
            price_start = stock['price_at_recommendation']
            stock_result = {
                'symbol': symbol,
                'rank': stock['rank'],
                'price_start': price_start,
                'returns': {}
            }

            for horizon_name, days in horizons:
                target_date = rec_date + timedelta(days=days)
                if target_date > datetime.now():
                    continue

                price_end = self.get_stock_price_at_date(symbol, target_date)
                if price_end is not None and price_start is not None and price_start > 0:
                    ret = (price_end - price_start) / price_start * 100
                    stock_result['returns'][horizon_name] = ret
                else:
                    stock_result['returns'][horizon_name] = None

            results.append(stock_result)

        # Aggregate statistics
        agg_stats = {}
        for horizon_name, _ in horizons:
            returns = [s['returns'][horizon_name] for s in results if s['returns'].get(horizon_name) is not None]
            if not returns:
                continue

            returns = np.array(returns)
            agg_stats[horizon_name] = {
                'count': len(returns),
                'mean_return_pct': float(np.mean(returns)),
                'median_return_pct': float(np.median(returns)),
                'std_pct': float(np.std(returns)) if len(returns) > 1 else 0,
                'win_rate': float(np.sum(returns > 0) / len(returns)),
                'sp500_return_pct': sp500_returns.get(horizon_name)
            }

            # Calculate excess return vs SP500
            if sp500_returns.get(horizon_name) is not None:
                excess = returns - sp500_returns[horizon_name]
                agg_stats[horizon_name]['mean_excess_pct'] = float(np.mean(excess))
                agg_stats[horizon_name]['excess_win_rate'] = float(np.sum(excess > 0) / len(returns))

        full_performance = {
            'archive_path': str(archive_path),
            'recommendation_date': archive['timestamp'],
            'llm_factors_used': archive.get('llm_factors_used', False),
            'top_stocks_count': archive.get('top_n', 20),
            'candidate_pool_size': archive.get('candidate_pool_size', 0),
            'stock_results': results,
            'aggregate_stats': agg_stats,
            'calculated_at': datetime.now().isoformat()
        }

        return full_performance

    def generate_performance_report(self) -> str:
        """
        Generate comprehensive HTML performance report from all archived recommendations.

        Returns:
            Path to the generated HTML report
        """
        archives = self.list_archives()
        all_performances = []

        for archive_path in archives:
            perf = self.calculate_performance_archived(archive_path)
            if perf is not None and perf.get('aggregate_stats'):
                all_performances.append(perf)

        # Generate HTML
        html = self._generate_html_report(all_performances)

        # Save report
        report_path = Path(__file__).parent.parent / "performance_history_report.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Performance report generated: {report_path}")
        return str(report_path)

    def _generate_html_report(self, all_performances: List[Dict]) -> str:
        """Generate HTML report from performance data."""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alpha158 历史推荐表现报告</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 30px; }}
        h1 {{ color: #333; margin-bottom: 20px; text-align: center; }}
        h2 {{ color: #555; margin: 30px 0 15px 0; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ padding: 12px; text-align: right; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: 600; text-align: center; }}
        td:first-child, th:first-child {{ text-align: left; }}
        .positive {{ color: #28a745; font-weight: 600; }}
        .negative {{ color: #dc3545; font-weight: 600; }}
        .neutral {{ color: #6c757d; }}
        .card {{ background: #f8f9fa; border-radius: 6px; padding: 15px; margin-bottom: 15px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .summary-card {{ background: white; border-radius: 6px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .summary-card h3 {{ font-size: 14px; color: #666; margin-bottom: 10px; }}
        .summary-card .value {{ font-size: 24px; font-weight: 700; color: #333; }}
        .footer {{ text-align: center; color: #999; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; }}
    </style>
</head>
<body>
<div class="container">
    <h1>Alpha158 历史推荐表现报告</h1>
    <p style="text-align: center; color: #666; margin-bottom: 30px;">
        生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
        总共 {len(all_performances)} 次存档推荐
    </p>
"""

        # Summary statistics
        all_1m = []
        all_3m = []
        all_6m = []

        for perf in all_performances:
            stats = perf.get('aggregate_stats', {})
            if '1m' in stats:
                all_1m.append(stats['1m'])
            if '3m' in stats:
                all_3m.append(stats['3m'])
            if '6m' in stats:
                all_6m.append(stats['6m'])

        html += """
    <h2>总体汇总统计</h2>
    <div class="summary-grid">
"""

        def add_summary_card(title, value, is_percent=False):
            if is_percent:
                value = f"{value:.2f}%"
            html = f"""
        <div class="summary-card">
            <h3>{title}</h3>
            <div class="value">{value}</div>
        </div>"""
            return html

        if all_1m:
            mean_1m = np.mean([s['mean_return_pct'] for s in all_1m])
            win_rate_1m = np.mean([s['win_rate'] for s in all_1m]) * 100
            html += add_summary_card("平均 1 个月回报", mean_1m, True)
            html += add_summary_card("1 个月胜率", win_rate_1m, True)

        if all_3m:
            mean_3m = np.mean([s['mean_return_pct'] for s in all_3m])
            win_rate_3m = np.mean([s['win_rate'] for s in all_3m]) * 100
            html += add_summary_card("平均 3 个月回报", mean_3m, True)
            html += add_summary_card("3 个月胜率", win_rate_3m, True)

        if all_6m:
            mean_6m = np.mean([s['mean_return_pct'] for s in all_6m])
            win_rate_6m = np.mean([s['win_rate'] for s in all_6m]) * 100
            html += add_summary_card("平均 6 个月回报", mean_6m, True)
            html += add_summary_card("6 个月胜率", win_rate_6m, True)

        html += """
    </div>
"""

        # Detailed by recommendation
        html += """
    <h2>各次推荐详细统计</h2>
    <table>
        <thead>
            <tr>
                <th>推荐日期</th>
                <th>LLM 因子</th>
                <th>周期</th>
                <th>样本数</th>
                <th>平均回报 (%)</th>
                <th>中位数回报 (%)</th>
                <th>胜率 (%)</th>
                <th>标普 500 (%)</th>
                <th>超额收益 (%)</th>
                <th>超额胜率 (%)</th>
            </tr>
        </thead>
        <tbody>
"""

        for perf in all_performances:
            stats = perf.get('aggregate_stats', {})
            rec_date = perf['recommendation_date'].split('T')[0]
            llm_used = "✓" if perf.get('llm_factors_used') else "-"

            for horizon, stat in stats.items():
                mean_ret = stat['mean_return_pct']
                median_ret = stat['median_return_pct']
                win_rate = stat['win_rate'] * 100
                sp500_ret = stat.get('sp500_return_pct')
                mean_excess = stat.get('mean_excess_pct')
                excess_win_rate = stat.get('excess_win_rate')

                mean_ret_class = "positive" if mean_ret > 0 else "negative" if mean_ret < 0 else "neutral"
                median_ret_class = "positive" if median_ret > 0 else "negative" if median_ret < 0 else "neutral"

                html += f'<tr><td>{rec_date}</td><td style="text-align:center">{llm_used}</td><td style="text-align:center">{horizon}</td>'
                html += f'<td style="text-align:center">{stat["count"]}</td>'
                html += f'<td class="{mean_ret_class}">{mean_ret:.2f}</td>'
                html += f'<td class="{median_ret_class}">{median_ret:.2f}</td>'
                html += f'<td>{win_rate:.1f}</td>'

                if sp500_ret is not None:
                    sp500_class = "positive" if sp500_ret > 0 else "negative" if sp500_ret < 0 else "neutral"
                    html += f'<td class="{sp500_class}">{sp500_ret:.2f}</td>'
                else:
                    html += '<td>-</td>'

                if mean_excess is not None:
                    excess_class = "positive" if mean_excess > 0 else "negative" if mean_excess < 0 else "neutral"
                    html += f'<td class="{excess_class}">{mean_excess:.2f}</td>'
                else:
                    html += '<td>-</td>'

                if excess_win_rate is not None:
                    html += f'<td>{(excess_win_rate * 100):.1f}</td>'
                else:
                    html += '<td>-</td>'

                html += '</tr>\n'

        html += """
        </tbody>
    </table>

    <div class="footer">
        ⚠️ 免责声明: 本报告由 AI 生成，仅供研究参考，不构成投资建议。投资有风险，入市需谨慎。
    </div>
</div>
</body>
</html>
"""

        return html

# Global instance
performance_tracker = PerformanceTracker()
