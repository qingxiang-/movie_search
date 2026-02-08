# Alpha158 Multi-Factor Stock Selection System

美股科技股多因子选股系统，基于Alpha158因子库

## 📊 Features

### Core: Alpha158 Factor Library
- **154 technical factors** across 5 batches
- Batch 1: Trend & Momentum (SMA, EMA, RSI, MACD, BB, ATR, ADX, Stochastic)
- Batch 2: Returns & Momentum (price changes, drawdowns, CCI, Williams %R)
- Batch 3: Volatility & Volume (VWAP, OBV, AD, CMF, EVM)
- Batch 4: Statistics & Quality (skewness, kurtosis, Sharpe, Sortino, Treynor)
- Batch 5: Composite Factors (alpha composite, trend strength, quality factor)

### ML Models
- **RandomForest** classifier (57.5% accuracy)
- **GradientBoosting** classifier
- No future leakage with time-based train/test split
- Feature importance analysis

### Ranking Method
- **Z-score normalized** multi-factor scoring
- Configurable factor weights
- Top-N stock selection

## 📁 Files

```
alpha158.py              # Core factor library
ml_dataset_builder_v4.py # Dataset builder
ml_train_sklearn.py      # ML training
ranking_method.py        # Ranking strategy
ranking_top20.csv       # Results
```

## 🚀 Quick Start

```bash
# Install dependencies
pip install pandas pandas-ta scikit-learn xgboost

# Run ranking method
python ranking_method.py

# Train ML model
python ml_train_sklearn.py
```

## 📈 Results

### ML Model Performance
| Model | Accuracy | F1 |
|-------|----------|-----|
| RandomForest | 57.5% | 0.54 |
| GradientBoosting | 57.5% | 0.55 |

### Top 5 Stocks (Ranking Method)
1. TSLA (score: 1.155)
2. AAPL (score: 0.703)
3. AVGO (score: 0.592)
4. AMZN (score: 0.374)
5. GOOGL (score: 0.372)

## 🔧 Factor Configuration

```python
FACTOR_CONFIG = {
    # Momentum (positive)
    'momentum_3m': 0.10,
    'momentum_6m': 0.15,
    
    # Quality (positive)
    'sharpe_ratio_20d': 0.10,
    'win_rate_20d': 0.05,
    
    # Trend (positive)
    'trend_strength': 0.08,
    'alpha_composite': 0.05,
    
    # Risk (negative = lower is better)
    'volatility_20d': -0.05,
    'max_drawdown_20d': -0.03,
}
```

## 📊 Data Source

- Yahoo Finance API
- 20 US tech stocks
- Quarterly sampling (2023-2024)

## 🔒 No Future Leakage

- Train period: 2023 Q1 - 2024 Q2
- Test period: 2024 Q3 - 2024 Q4
- All factors computed using only historical data

## 📝 License

MIT License
