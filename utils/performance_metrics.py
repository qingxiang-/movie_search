"""
Performance Metrics Calculator
Common performance metrics for quantitative trading backtesting.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional

def calculate_sharpe_ratio(
    daily_returns: pd.Series,
    risk_free_rate: float = 0.02,
    annualize: bool = True,
    trading_days: int = 252
) -> float:
    """
    Calculate Sharpe ratio.

    Formula: (E[R] - rf) / std(R)

    Args:
        daily_returns: Series of daily percentage returns
        risk_free_rate: Annual risk-free rate (default 2%)
        annualize: Whether to annualize the result
        trading_days: Number of trading days in a year

    Returns:
        Sharpe ratio
    """
    if len(daily_returns) < 2:
        return 0.0

    daily_rf = (1 + risk_free_rate) ** (1 / trading_days) - 1
    excess_returns = daily_returns - daily_rf

    mean_excess = excess_returns.mean()
    std_excess = excess_returns.std()

    if std_excess == 0 or np.isnan(std_excess):
        return 0.0

    sharpe = mean_excess / std_excess

    if annualize:
        sharpe = sharpe * np.sqrt(trading_days)

    return float(sharpe)

def calculate_sortino_ratio(
    daily_returns: pd.Series,
    risk_free_rate: float = 0.02,
    target_return: float = 0,
    annualize: bool = True,
    trading_days: int = 252
) -> float:
    """
    Calculate Sortino ratio. Only considers downside deviation.

    Formula: (E[R] - rf) / std(negative returns below target)

    Args:
        daily_returns: Series of daily percentage returns
        risk_free_rate: Annual risk-free rate
        target_return: Target return (usually 0)
        annualize: Whether to annualize
        trading_days: Trading days per year

    Returns:
        Sortino ratio
    """
    if len(daily_returns) < 2:
        return 0.0

    daily_rf = (1 + risk_free_rate) ** (1 / trading_days) - 1
    excess_returns = daily_returns - daily_rf - target_return

    downside_returns = excess_returns[excess_returns < 0]

    if len(downside_returns) < 1:
        # No downside risk = infinite Sharpe
        return float('inf') if excess_returns.mean() > 0 else 0.0

    mean_excess = excess_returns.mean()
    downside_std = np.sqrt(np.mean(downside_returns ** 2))

    if downside_std == 0:
        return 0.0

    sortino = mean_excess / downside_std

    if annualize:
        sortino = sortino * np.sqrt(trading_days)

    return float(sortino)

def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """
    Calculate maximum drawdown (maximum peak to trough percentage drop).

    Args:
        equity_curve: Cumulative equity curve (starting from 1.0 or 100)

    Returns:
        Maximum drawdown as positive percentage (0.2 = 20% max drawdown)
    """
    if len(equity_curve) < 2:
        return 0.0

    # Normalize to starting from 1
    if equity_curve.iloc[0] != 1:
        equity_curve = equity_curve / equity_curve.iloc[0]

    running_max = equity_curve.cummax()
    drawdown = (equity_curve / running_max) - 1.0

    max_dd = abs(drawdown.min())
    return float(max_dd) if not pd.isna(max_dd) else 0.0

def calculate_cagr(
    total_return: float,
    years: float
) -> float:
    """
    Calculate Compound Annual Growth Rate (CAGR).

    Args:
        total_return: Total return (e.g., 0.5 for 50% return)
        years: Number of years

    Returns:
        CAGR as decimal
    """
    if years <= 0 or total_return <= -1:
        return 0.0

    if total_return < 0:
        # Negative total return gives negative CAGR
        return -((1 - total_return) ** (1/years) - 1)

    cagr = (1 + total_return) ** (1/years) - 1
    return float(cagr)

def calculate_cagr_from_equity(
    equity_curve: pd.Series,
    trading_days_per_year: int = 252
) -> float:
    """Calculate CAGR from equity curve."""
    if len(equity_curve) < 2:
        return 0.0

    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    years = len(equity_curve) / trading_days_per_year
    return calculate_cagr(total_return, years)

def calculate_win_rate(returns: pd.Series) -> float:
    """Calculate percentage of positive returns."""
    if len(returns) == 0:
        return 0.0
    return float((returns > 0).sum() / len(returns))

def calculate_volatility(
    daily_returns: pd.Series,
    annualize: bool = True,
    trading_days: int = 252
) -> float:
    """Calculate annualized volatility."""
    if len(daily_returns) < 2:
        return 0.0

    vol = daily_returns.std()
    if annualize:
        vol = vol * np.sqrt(trading_days)
    return float(vol)

def calculate_calmar_ratio(
    equity_curve: pd.Series,
    trading_days_per_year: int = 252
) -> float:
    """
    Calculate Calmar ratio = CAGR / max drawdown.

    A higher Calmar ratio indicates better risk-adjusted returns.
    """
    if len(equity_curve) < 2:
        return 0.0

    cagr = calculate_cagr_from_equity(equity_curve, trading_days_per_year)
    max_dd = calculate_max_drawdown(equity_curve)

    if max_dd == 0:
        return float('inf') if cagr > 0 else 0.0

    return float(cagr / max_dd)

def calculate_all_metrics(
    daily_returns: pd.Series,
    equity_curve: pd.Series,
    risk_free_rate: float = 0.02
) -> Dict[str, float]:
    """
    Calculate all common performance metrics.

    Args:
        daily_returns: Series of daily percentage returns
        equity_curve: Cumulative equity curve (can be derived from returns)
        risk_free_rate: Annual risk-free rate

    Returns:
        Dictionary of all metrics
    """
    # If equity_curve not provided, derive from returns
    if equity_curve is None and daily_returns is not None:
        equity_curve = (1 + daily_returns).cumprod()

    metrics = {
        'sharpe_ratio': calculate_sharpe_ratio(daily_returns, risk_free_rate),
        'sortino_ratio': calculate_sortino_ratio(daily_returns, risk_free_rate),
        'max_drawdown': calculate_max_drawdown(equity_curve),
        'cagr': calculate_cagr_from_equity(equity_curve),
        'volatility': calculate_volatility(daily_returns),
        'win_rate': calculate_win_rate(daily_returns),
        'calmar_ratio': calculate_calmar_ratio(equity_curve)
    }

    return metrics

def calculate_drawdown_curve(equity_curve: pd.Series) -> pd.Series:
    """
    Calculate the drawdown curve for plotting.

    Returns:
        Series of drawdowns (negative values, 0 = no drawdown)
    """
    running_max = equity_curve.cummax()
    drawdown = (equity_curve / running_max) - 1.0
    return drawdown
