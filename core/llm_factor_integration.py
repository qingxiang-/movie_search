"""
LLM Factor Integration Module
Integrate LLM analysis predictions into Alpha158 multi-factor ranking system.

This module coordinates with StockAnalysisAgent to get LLM predictions
and converts them into numerical factors for the multi-factor model.
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

from agents.stock_agent import StockAnalysisAgent
from utils.llm_factor_cache import llm_factor_cache

logger = logging.getLogger(__name__)

@dataclass
class LLMFactors:
    """Container for LLM-derived numerical factors."""
    llm_predicted_return: float    # Predicted 6-month return percentage
    llm_confidence: float          # Confidence score (1.0 = high, 0.5 = medium, 0.0 = low)
    llm_risk_score: float          # Risk score (-1.0 = low risk, -0.5 = medium, 0.0 = high)
    llm_buy_signal: float          # Buy signal encoding (1.0 = buy, 0 = hold, -1.0 = sell)

def convert_llm_to_factors(llm_result: Dict) -> Dict[str, float]:
    """
    Convert LLM prediction output to numerical factors.

    Args:
        llm_result: The prediction dictionary from StockAnalysisAgent
            Expected fields:
            - predicted_return: float (6-month predicted return %)
            - confidence: str ("high"|"medium"|"low")
            - risk_level: str ("high"|"medium"|"low")
            - recommendation: str ("买入"|"持有"|"卖出")

    Returns:
        Dictionary of factor name -> numerical value
    """
    prediction = llm_result.get('prediction', {})

    # Handle predicted return
    predicted_return = prediction.get('predicted_return', 0.0)
    if predicted_return is None:
        predicted_return = 0.0

    # Encode confidence: high -> 1.0, medium -> 0.5, low -> 0.0
    confidence_map = {
        'high': 1.0,
        'medium': 0.5,
        'low': 0.0
    }
    confidence_str = prediction.get('confidence', 'medium')
    confidence = confidence_map.get(confidence_str.lower() if confidence_str else 'medium', 0.5)

    # Encode risk: low risk -> -1.0 (should increase score), high risk -> 0.0
    # Because higher risk should lower final composite score
    risk_map = {
        'low': -1.0,
        'medium': -0.5,
        'high': 0.0
    }
    risk_str = prediction.get('risk_level', 'medium')
    risk_score = risk_map.get(risk_str.lower() if risk_str else 'medium', -0.5)

    # Encode recommendation: buy -> 1.0, hold -> 0, sell -> -1.0
    rec_map = {
        '买入': 1.0,
        '持有': 0.0,
        '卖出': -1.0
    }
    rec_str = prediction.get('recommendation', '持有')
    buy_signal = rec_map.get(rec_str, 0.0)

    return {
        'llm_predicted_return': float(predicted_return),
        'llm_confidence': float(confidence),
        'llm_risk_score': float(risk_score),
        'llm_buy_signal': float(buy_signal)
    }

async def fetch_llm_predictions(
    symbols: List[str],
    agent: Optional[StockAnalysisAgent] = None,
    max_concurrent: int = 5,
    use_cache: bool = True
) -> Dict[str, Dict[str, float]]:
    """
    Fetch LLM predictions for a list of symbols using StockAnalysisAgent.

    Args:
        symbols: List of stock symbols to analyze
        agent: Optional existing StockAnalysisAgent instance (created if None)
        max_concurrent: Maximum number of concurrent LLM requests
        use_cache: Whether to use cached results if available

    Returns:
        Dict mapping symbol -> dict of LLM factors
    """
    if agent is None:
        agent = StockAnalysisAgent()

    results: Dict[str, Dict[str, float]] = {}

    # Check cache first
    symbols_to_fetch = []
    for symbol in symbols:
        if use_cache:
            cached = llm_factor_cache.get(symbol)
            if cached is not None:
                results[symbol] = cached
                logger.info(f"LLM factors for {symbol} loaded from cache")
                continue
        symbols_to_fetch.append(symbol)

    if not symbols_to_fetch:
        return results

    logger.info(f"Fetching LLM predictions for {len(symbols_to_fetch)} symbols...")

    # Use semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)

    async def analyze_symbol(symbol: str) -> Optional[Dict[str, float]]:
        async with semaphore:
            try:
                from core.llm_client import LLMClient
                llm_client = LLMClient()
                result = await agent.analyze_single_stock(symbol, llm_client)
                if result is None or 'prediction' not in result:
                    logger.warning(f"No prediction returned for {symbol}")
                    return None

                factors = convert_llm_to_factors(result)

                # Cache the result
                if use_cache:
                    llm_factor_cache.set(symbol, factors)

                logger.info(f"Successfully got LLM analysis for {symbol}")
                return factors
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {str(e)}")
                return None

    # Run all tasks
    tasks = [analyze_symbol(symbol) for symbol in symbols_to_fetch]
    task_results = await asyncio.gather(*tasks)

    # Collect results
    for symbol, factors in zip(symbols_to_fetch, task_results):
        if factors is not None:
            results[symbol] = factors

    logger.info(f"Completed LLM fetch: got {len(results)}/{len(symbols)} results")
    return results

def get_llm_factors_sync(
    symbols: List[str],
    max_concurrent: int = 5,
    use_cache: bool = True
) -> Dict[str, Dict[str, float]]:
    """
    Synchronous wrapper for fetch_llm_predictions.

    Args:
        symbols: List of stock symbols to analyze
        max_concurrent: Maximum concurrent requests
        use_cache: Whether to use cache

    Returns:
        Dict mapping symbol -> LLM factors
    """
    return asyncio.run(fetch_llm_predictions(symbols, max_concurrent=max_concurrent, use_cache=use_cache))
