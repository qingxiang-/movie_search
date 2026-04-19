#!/usr/bin/env python3
"""
Walk-Forward Backtesting Framework for Alpha158 Multi-Factor Stock Selection System.

Implements walk-forward validation which is more robust than simple single train/test split.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

import pandas as pd
import numpy as np

from utils.performance_metrics import calculate_all_metrics, calculate_drawdown_curve
from ranking_method import _fetch_all_stock_factors, _calculate_factor_weights, _calculate_scores_and_rank

# Configure logging
logger = logging.getLogger(__name__)

# Default settings
DEFAULT_REBALANCE_DAYS = 21  # Monthly rebalancing (about 21 trading days)
DEFAULT_TOP_N = 10  # Select top N stocks each rebalance
TRADING_DAYS_PER_YEAR = 252

class BacktestFramework:
    """
    Walk-Forward Backtesting Framework.

    Features:
    - Strict temporal split: only uses data available up to rebalance date (no future leakage)
    - Walk-forward validation with periodic rebalancing
    - Supports different weighting schemes (equal, market cap)
    - Includes transaction cost modeling
    - Generates comprehensive HTML report with performance metrics and charts
    """

    def __init__(
        self,
        stock_pool: List[str],
        start_date: datetime,
        end_date: datetime,
        rebalance_days: int = DEFAULT_REBALANCE_DAYS,
        top_n_stocks: int = DEFAULT_TOP_N,
        transaction_cost_bps: float = 10,  # 0.1% per trade
        weight_type: str = "equal"
    ):
        """
        Initialize backtest framework.

        Args:
            stock_pool: List of stock symbols to consider
            start_date: Backtest start date
            end_date: Backtest end date
            rebalance_days: Number of calendar days between rebalances
            top_n_stocks: Number of top stocks to select at each rebalance
            transaction_cost_bps: Transaction cost in basis points (1bps = 0.01%)
            weight_type: Weighting scheme: "equal" or "market_cap" (currently only equal implemented)
        """
        self.stock_pool = stock_pool
        self.start_date = start_date
        self.end_date = end_date
        self.rebalance_days = rebalance_days
        self.top_n_stocks = top_n_stocks
        self.transaction_cost_bps = transaction_cost_bps
        self.weight_type = weight_type

        self.results = None
        self.daily_equity = None
        self.metrics = None

    def _generate_rebalance_dates(self) -> List[datetime]:
        """Generate list of rebalance dates between start and end."""
        dates = []
        current = self.start_date
        while current <= self.end_date:
            dates.append(current)
            current += timedelta(days=self.rebalance_days)
        # Add end date as final rebalance for last period
        if dates[-1] < self.end_date:
            dates.append(self.end_date)
        return dates

    def _get_data_for_window(
        self,
        symbol: str,
        rebalance_date: datetime,
        lookback_days: int = 252
    ) -> Optional[Dict]:
        """
        Get factor data for the lookback period ending at rebalance_date.
        Strictly only uses data available before or at rebalance_date (no future leakage).
        """
        period2 = int(rebalance_date.timestamp())
        period1 = int((rebalance_date - timedelta(days=lookback_days)).timestamp())

        from ranking_method import get_stock_data, calculate_factors

        try:
            df = get_stock_data(symbol, period1, period2)
            if df is None or len(df) < 100:
                return None

            factors = calculate_factors(df)
            if factors is None or len(factors) == 0:
                return None

            # Add latest price
            factors['latest_price'] = df['close'].iloc[-1]
            return factors

        except Exception as e:
            logger.warning(f"Failed to get data for {symbol} at {rebalance_date}: {e}")
            return None

    def _select_top_stocks(
        self,
        rebalance_date: datetime,
        lookback_days: int = 252
    ) -> Optional[List[Tuple[str, float]]]:
        """
        Select top N stocks at a given rebalance date using the factor model.

        Returns:
            List of (symbol, score) tuples for top N stocks.
        """
        logger.info(f"Selecting stocks for rebalance date: {rebalance_date.strftime('%Y-%m-%d')}")

        # Fetch factors for all stocks (only data up to rebalance_date)
        all_factors = {}
        for symbol in self.stock_pool:
            factors = self._get_data_for_window(symbol, rebalance_date, lookback_days)
            if factors is not None:
                all_factors[symbol] = factors

        if len(all_factors) < self.top_n_stocks:
            logger.warning(f"Only {len(all_factors)} valid stocks for this rebalance, skipping")
            return None

        # Build dataframe and calculate scores
        df_factors = pd.DataFrame(all_factors).T
        factor_weights = _calculate_factor_weights(df_factors)
        df_result = _calculate_scores_and_rank(df_factors, factor_weights)

        # Select top N
        top_stocks = df_result.head(self.top_n_stocks)
        selected = [(symbol, score) for symbol, score in zip(top_stocks.index, top_stocks['score'])]

        logger.info(f"Selected top {len(selected)} stocks: {', '.join([s[0] for s in selected])}")
        return selected

    def _calculate_period_return(
        self,
        selected_stocks: List[Tuple[str, float]],
        start_date: datetime,
        end_date: datetime,
        start_prices: Dict[str, float]
    ) -> Tuple[float, Dict]:
        """
        Calculate portfolio return over the period from start_date to end_date.

        Args:
            selected_stocks: List of (symbol, score) selected at start of period
        start_date: Start of holding period
        end_date: End of holding period
        start_prices: Prices at start (already fetched)

        Returns:
            (period_return, price_dict)
        """
        from ranking_method import get_stock_data

        n_stocks = len(selected_stocks)
        if n_stocks == 0:
            return 0.0, {}

        total_return = 0.0
        end_prices = {}
        transaction_cost = 0.0

        # Equal weighting
        weight = 1.0 / n_stocks
        tc_per_stock = (self.transaction_cost_bps / 10000)  # convert bps to decimal

        for symbol, _ in selected_stocks:
            start_price = start_prices.get(symbol)
            if start_price is None or start_price <= 0:
                continue

            # Get price at end of period
            period1 = int((start_date - timedelta(days=5)).timestamp())
            period2 = int((end_date + timedelta(days=5)).timestamp())

            try:
                df = get_stock_data(symbol, period1, period2)
                if df is None or df.empty:
                    continue

                # Find closest price after end_date
                df_after = df[df.index >= end_date]
                if df_after.empty:
                    df_after = df[df.index <= end_date]

                if df_after.empty:
                    continue

                end_price = float(df_after['close'].iloc[0])
                end_prices[symbol] = end_price

                # Calculate return for this stock
                ret = (end_price - start_price) / start_price
                total_return += weight * ret

                # Add transaction cost (buy and sell = 2 * tc per stock)
                transaction_cost += weight * 2 * tc_per_stock

            except Exception as e:
                logger.warning(f"Failed to get end price for {symbol}: {e}")
                continue

        # Subtract transaction costs
        net_return = total_return - transaction_cost

        logger.info(f"Period return: {net_return*100:.2f}% (includes {transaction_cost*100:.2f}% transaction costs)")
        return net_return, end_prices

    def run_walk_forward(
        self,
        lookback_days: int = 252
    ) -> Dict[str, Any]:
        """
        Run walk-forward backtest.

        Args:
            lookback_days: Number of lookback days for factor calculation

        Returns:
            Complete backtest result dictionary
        """
        logger.info("=" * 80)
        logger.info("Starting Walk-Forward Backtest")
        logger.info("=" * 80)
        logger.info(f"Stock pool: {len(self.stock_pool)} stocks")
        logger.info(f"Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        logger.info(f"Rebalance every {self.rebalance_days} days, select top {self.top_n_stocks}")
        logger.info(f"Transaction cost: {self.transaction_cost_bps} bps")

        rebalance_dates = self._generate_rebalance_dates()
        logger.info(f"Number of rebalances: {len(rebalance_dates) - 1}")

        # Store results for each period
        period_results = []
        equity_curve = [{
            'date': self.start_date,
            'equity': 1.0,
            'return': 0.0
        }]
        current_equity = 1.0

        # Walk through each rebalance period
        for i in range(len(rebalance_dates) - 1):
            rebalance_date = rebalance_dates[i]
            next_rebalance_date = rebalance_dates[i + 1]

            logger.info(f"\n--- Period {i+1}/{len(rebalance_dates)-1}: {rebalance_date.strftime('%Y-%m-%d')} to {next_rebalance_date.strftime('%Y-%m-%d')}")

            # Select top stocks using only data up to rebalance_date
            selected = self.select_top_stocks(rebalance_date, lookback_days)
            if selected is None:
                logger.warning("Skipping this period due to insufficient data")
                continue

            # Get start prices (already fetched during factor calculation, but extract them)
            start_prices = {}
            for symbol, _ in selected:
                factors = self._get_data_for_window(symbol, rebalance_date, lookback_days)
                if factors and 'latest_price' in factors:
                    start_prices[symbol] = factors['latest_price']

            # Calculate return for the period
            period_ret, end_prices = self._calculate_period_return(
                selected, rebalance_date, next_rebalance_date, start_prices
            )

            # Update equity
            current_equity = current_equity * (1 + period_ret)

            # Record this period
            period_results.append({
                'period': i+1,
                'start_date': rebalance_date.isoformat(),
                'end_date': next_rebalance_date.isoformat(),
                'selected_stocks': [(s[0], float(s[1])) for s in selected],
                'period_return': float(period_ret),
                'current_equity': float(current_equity)
            })

            equity_curve.append({
                'date': next_rebalance_date.isoformat(),
                'equity': float(current_equity),
                'return': float(period_ret)
            })

        logger.info(f"\nBacktest completed. Final equity: {current_equity:.4f} (total return: {(current_equity - 1)*100:.2f}%)")

        # Build dataframe for equity curve and calculate metrics
        df_equity = pd.DataFrame(equity_curve)
        df_equity['date'] = pd.to_datetime(df_equity['date'])
        df_equity = df_equity.set_index('date')

        # Calculate daily returns from equity curve
        df_equity['daily_return'] = df_equity['equity'].pct_change().dropna()

        # Calculate all performance metrics
        metrics = calculate_all_metrics(df_equity['daily_return'], df_equity['equity'])

        # Calculate drawdown curve for plotting
        drawdowns = calculate_drawdown_curve(df_equity['equity'])
        df_equity['drawdown'] = drawdowns

        # Get SPY benchmark
        benchmark_metrics = self._get_benchmark_metrics(self.start_date, self.end_date)

        # Store results
        self.results = {
            'config': {
                'stock_pool_size': len(self.stock_pool),
                'start_date': self.start_date.isoformat(),
                'end_date': self.end_date.isoformat(),
                'rebalance_days': self.rebalance_days,
                'top_n_stocks': self.top_n_stocks,
                'transaction_cost_bps': self.transaction_cost_bps,
                'weight_type': self.weight_type,
                'lookback_days': lookback_days
            },
            'period_results': period_results,
            'equity_curve': df_equity.to_dict(orient='index'),
            'metrics': metrics,
            'benchmark_metrics': benchmark_metrics,
            'generated_at': datetime.now().isoformat()
        }

        self.daily_equity = df_equity
        self.metrics = metrics

        return self.results

    def _get_benchmark_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[Dict]:
        """Get benchmark (SPY S&P 500 ETF) performance for same period."""
        from ranking_method import get_stock_data

        try:
            period1 = int(start_date.timestamp())
            period2 = int(end_date.timestamp())
            df_spy = get_stock_data('SPY', period1, period2)

            if df_spy is None or df_spy.empty:
                return None

            df_spy['daily_return'] = df_spy['close'].pct_change().dropna()
            equity_curve = (1 + df_spy['daily_return']).cumprod()

            metrics = calculate_all_metrics(df_spy['daily_return'], equity_curve)
            metrics['total_return'] = (equity_curve.iloc[-1] - 1)
            return metrics

        except Exception as e:
            logger.warning(f"Failed to get benchmark data: {e}")
            return None

    def save_results(self, output_dir: str = "data/backtest_results") -> str:
        """Save backtest results to JSON file."""
        if self.results is None:
            raise ValueError("No backtest results to save. Run run_walk_forward() first.")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_result_{timestamp}.json"
        full_path = output_path / filename

        # Convert to serializable format
        serializable = self.results.copy()
        if isinstance(serializable['equity_curve'], dict):
            # Already a dict
            pass

        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, indent=2, default=str)

        logger.info(f"Backtest results saved to {full_path}")
        return str(full_path)

    def generate_html_report(self) -> str:
        """Generate HTML backtest report with charts and metrics."""
        if self.results is None or self.daily_equity is None:
            raise ValueError("No backtest results, run run_walk_forward() first.")

        metrics = self.metrics
        bm_metrics = self.results.get('benchmark_metrics')

        # Generate HTML
        html = self._generate_html(metrics, bm_metrics)

        # Save
        output_path = Path(__file__).parent / "backtest_report.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Backtest report generated: {output_path}")
        return str(output_path)

    def _generate_html(self, metrics: Dict, bm_metrics: Optional[Dict]) -> str:
        """Generate HTML report."""

        def format_metric(name: str, value: float, is_percent: bool = False) -> str:
            if is_percent:
                return f"{value*100:.2f}%"
            else:
                return f"{value:.3f}"

        config = self.results['config']

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alpha158 回测报告</title>
    <script src="https://cdn.plot.ly/plotly-2.20.0.min.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 30px; }}
        h1 {{ color: #333; margin-bottom: 20px; text-align: center; }}
        h2 {{ color: #555; margin: 30px 0 15px 0; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .config-table {{ width: 100%; max-width: 600px; margin-bottom: 20px; border-collapse: collapse; }}
        .config-table td, .config-table th {{ padding: 8px 12px; border-bottom: 1px solid #ddd; text-align: left; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .metric-card {{ background: #f8f9fa; border-radius: 6px; padding: 15px; text-align: center; }}
        .metric-name {{ font-size: 14px; color: #666; margin-bottom: 8px; }}
        .metric-value {{ font-size: 28px; font-weight: 700; color: #333; }}
        .metric-value.positive {{ color: #28a745; }}
        .metric-value.negative {{ color: #dc3545; }}
        #equity-chart {{ width: 100%; height: 400px; }}
        #drawdown-chart {{ width: 100%; height: 300px; }}
        .comparison-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        .comparison-table th, .comparison-table td {{ padding: 12px; text-align: center; border-bottom: 1px solid #ddd; }}
        .comparison-table th {{ background: #f8f9fa; }}
        .footer {{ text-align: center; color: #999; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; }}
    </style>
</head>
<body>
<div class="container">
    <h1>Alpha158 多因子选股 - 回测报告</h1>

    <h2>回测配置</h2>
    <table class="config-table">
        <tr><td>股票池大小</td><td>{config['stock_pool_size']} 只股票</td></tr>
        <tr><td>开始日期</td><td>{config['start_date'][:10]}</td></tr>
        <tr><td>结束日期</td><td>{config['end_date'][:10]}</td></tr>
        <tr><td>再平衡周期</td><td>每 {config['rebalance_days']} 天</td></tr>
        <tr><td>每期选择</td><td>top {config['top_n_stocks']} 只股票</td></tr>
        <tr><td>交易成本</td><td>{config['transaction_cost_bps']} bps</td></tr>
    </table>

    <h2>绩效指标</h2>
    <div class="metrics-grid">
"""

        # Add metric cards
        metric_names = {
            'sharpe_ratio': 'Sharpe Ratio',
            'sortino_ratio': 'Sortino Ratio',
            'calmar_ratio': 'Calmar Ratio',
            'cagr': 'CAGR',
            'max_drawdown': '最大回撤',
            'volatility': '年化波动率',
            'win_rate': '胜率',
        }

        for key, name in metric_names.items():
            value = metrics.get(key, 0)
            if key in ['cagr', 'max_drawdown', 'volatility']:
                formatted = format_metric(name, value, True)
            else:
                formatted = format_metric(name, value, False)

            css_class = 'metric-value'
            if key in ['cagr'] and value > 0:
                css_class += ' positive'
            elif key in ['max_drawdown']:
                if value < 0.2:
                    css_class += ' positive'  # smaller drawdown is good

            html += f"""
        <div class="metric-card">
            <div class="metric-name">{name}</div>
            <div class="{css_class}">{formatted}</div>
        </div>
"""

        html += """
    </div>
"""

        # Add comparison with benchmark if available
        if bm_metrics:
            html += """
    <h2>策略 vs 基准 (SPY S&P 500)</h2>
    <table class="comparison-table">
        <thead>
            <tr><th>指标</th><th>策略</th><th>基准 (SPY)</th><th>差额</th></tr>
        </thead>
        <tbody>
"""
            for key, name in metric_names.items():
                s_val = metrics.get(key, 0)
                b_val = bm_metrics.get(key, 0)
                diff = s_val - b_val
                is_pct = key in ['cagr', 'max_drawdown', 'volatility', 'win_rate']
                s_str = format_metric(name, s_val, is_pct)
                b_str = format_metric(name, b_val, is_pct)
                diff_str = f"{diff*100:.2f}%" if is_pct else f"{diff:.3f}"
                diff_class = 'positive' if diff > 0 else 'negative'

                html += f"""
            <tr><td>{name}</td><td>{s_str}</td><td>{b_str}</td><td class="{diff_class}">{diff_str}</td></tr>
"""

            html += """
        </tbody>
    </table>
"""

        # Add charts
        html += """
    <h2>权益曲线</h2>
    <div id="equity-chart"></div>

    <h2>回撤曲线</h2>
    <div id="drawdown-chart"></div>

    <div class="footer">
        ⚠️ 免责声明: 本回测仅供研究参考，不构成投资建议。投资有风险，入市需谨慎。
    </div>
</div>

<script>
// Equity curve data
"""

        # Prepare equity data for Plotly
        equity_data = []
        for date_str, row in self.results['equity_curve'].items():
            equity_data.append({
                'date': date_str,
                'equity': row['equity']
            })
        equity_data.sort(key=lambda x: x['date'])

        # Build equity data JSON string
        equity_json_lines = []
        for d in equity_data:
            equity_json_lines.append(f'{{x: "{d["date"]}", y: {d["equity"]:.4f}}}')
        equity_json_str = ',\n'.join(equity_json_lines)

        # Build drawdown data JSON string
        drawdown_json_lines = []
        for date_str, row in self.results['equity_curve'].items():
            if 'drawdown' in row:
                drawdown_json_lines.append(f'{{x: "{date_str}", y: {row["drawdown"]:.4f}}}')
        drawdown_json_str = ',\n'.join(drawdown_json_lines)

        html += """
<script src="https://cdn.plot.ly/plotly-2.20.0.min.js"></script>
<script>
// Equity curve data
var equityData = [
""" + equity_json_str + """
];

var equityLayout = {
    title: 'Cumulative Equity Curve (Starting from 1.0)',
    xaxis: {title: 'Date'},
    yaxis: {title: 'Equity'},
    hovermode: 'x unified'
};

Plotly.newPlot('equity-chart', [equityData], equityLayout);

// Drawdown data
var drawdownData = [
""" + drawdown_json_str + """
];

var drawdownLayout = {
    title: 'Drawdown',
    xaxis: {title: 'Date'},
    yaxis: {title: 'Drawdown'},
    hovermode: 'x unified'
};

Plotly.newPlot('drawdown-chart', [drawdownData], drawdownLayout);
</script>
</body>
</html>
"""

        return html

def get_sp500_returns(
    start_date: datetime,
    end_date: datetime
) -> pd.DataFrame:
    """Get SPY (S&P 500 ETF) daily returns for benchmark."""
    from ranking_method import get_stock_data

    period1 = int(start_date.timestamp())
    period2 = int(end_date.timestamp())
    df = get_stock_data('SPY', period1, period2)
    return df

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Walk-Forward Backtest for Alpha158")
    parser.add_argument("--start-year", type=int, default=2020, help="Backtest start year")
    parser.add_argument("--end-year", type=int, default=2026, help="Backtest end year")
    parser.add_argument("--rebalance-days", type=int, default=21, help="Rebalance every N calendar days")
    parser.add_argument("--top-n", type=int, default=10, help="Select top N stocks each rebalance")
    parser.add_argument("--transaction-cost", type=float, default=10, help="Transaction cost in bps")
    parser.add_argument("--stock-pool", type=str, help="CSV file with stock pool")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Use default TECH_100 stock pool
    from ranking_method import TECH_100
    stock_pool = TECH_100
    if args.stock_pool:
        import pandas as pd
        df = pd.read_csv(args.stock_pool)
        stock_pool = df['ticker'].tolist() if 'ticker' in df.columns else df.iloc[:, 0].tolist()
        logger.info(f"Loaded custom stock pool: {len(stock_pool)} stocks")

    # Create date range
    start_date = datetime(args.start_year, 1, 1)
    end_date = datetime(args.end_year, 1, 1)

    # Create and run backtest
    backtest = BacktestFramework(
        stock_pool=stock_pool,
        start_date=start_date,
        end_date=end_date,
        rebalance_days=args.rebalance_days,
        top_n_stocks=args.top_n,
        transaction_cost_bps=args.transaction_cost
    )

    results = backtest.run_walk_forward()
    backtest.save_results()
    report_path = backtest.generate_html_report()

    print(f"\n✅ Backtest completed!")
    print(f"📊 Report saved to: {report_path}")
