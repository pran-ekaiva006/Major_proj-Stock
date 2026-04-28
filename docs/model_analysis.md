# ML Model Analysis

## Overview

This project compares four machine learning models for next-day stock price prediction using 37 engineered features from raw OHLCV data.

## Feature Engineering

### Technical Indicators Used (37 features)

| Category | Features | Count |
|----------|----------|-------|
| Raw OHLCV | open, high, low, close, volume | 5 |
| Moving Averages | SMA(5,10,20), EMA(12,26), close/SMA ratios | 7 |
| Momentum | RSI(14), MACD line/signal/histogram | 4 |
| Volatility | Bollinger Bands (upper, lower, width, position), daily return, log return, vol(5,20) | 8 |
| Price Ratios | high/low ratio, close/open ratio, price range | 3 |
| Volume | Volume SMA(5,20), volume ratio | 3 |
| Calendar | Day of week, month | 2 |
| Lag Features | close_lag(1,2,3,5), return_lag(1,2,3,5) | 8 |

### Why These Features?

- **Moving Averages**: Capture trend direction and momentum
- **RSI**: Identifies overbought/oversold conditions
- **MACD**: Trend-following momentum indicator
- **Bollinger Bands**: Measure volatility and relative price levels
- **Lag Features**: Capture autoregressive patterns in price series
- **Volume Features**: Volume confirms price movements

## Models Compared

### 1. Linear Regression (Baseline)
- Simple, interpretable baseline
- Assumes linear relationship between features and target
- Fast training, no hyperparameters

### 2. Random Forest Regressor
- Ensemble of 200 decision trees
- Captures non-linear relationships
- Provides feature importance rankings
- Robust to outliers

### 3. XGBoost (Gradient Boosting)
- 300 boosting rounds, learning rate 0.05
- State-of-the-art for tabular data
- Regularization (L1/L2) prevents overfitting
- Built-in early stopping on validation set

### 4. LSTM (Long Short-Term Memory)
- Deep learning model for sequential data
- Uses 60-day sliding window of features
- Architecture: LSTM(128) → Dropout → LSTM(64) → Dropout → Dense(32) → Dense(1)
- Huber loss for robustness, early stopping with patience=10

## Methodology

### Data Splitting (Time-Series Aware)
```
|-------- Train (70%) --------|--- Val (15%) ---|--- Test (15%) ---|
                                                  ↑ Evaluation here
```

**No random shuffling** — this prevents data leakage where future data could influence past predictions.

### Evaluation Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **R²** | 1 - SS_res/SS_tot | % of variance explained (1.0 = perfect) |
| **MAE** | mean(\|y - ŷ\|) | Average absolute error in dollars |
| **RMSE** | √mean((y - ŷ)²) | Penalizes large errors more |
| **MAPE** | mean(\|y - ŷ\|/y) × 100 | Percentage error (scale-independent) |
| **Directional Accuracy** | % correct up/down | Trading signal accuracy |

## How to Run

```bash
# Train all models and generate comparison
python ml_model/train.py

# Generate comparison charts for report
python ml_model/model_comparison.py

# Results saved to ml_model/results/
```

## References

1. Brownlee, J. (2018). *Deep Learning for Time Series Forecasting*. Machine Learning Mastery.
2. Chen, T., & Guestrin, C. (2016). XGBoost: A Scalable Tree Boosting System. *KDD '16*.
3. Hochreiter, S., & Schmidhuber, J. (1997). Long Short-Term Memory. *Neural Computation*.
4. Murphy, J. (1999). *Technical Analysis of the Financial Markets*. New York Institute of Finance.
