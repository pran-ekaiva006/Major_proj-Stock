"""
Feature Engineering Module for Stock Price Prediction
=====================================================
Computes technical indicators from raw OHLCV data.
Used by both the training pipeline and the prediction API.

Technical Indicators:
    - SMA (Simple Moving Average): 5, 10, 20 day
    - EMA (Exponential Moving Average): 12, 26 day
    - RSI (Relative Strength Index): 14 day
    - MACD (Moving Average Convergence Divergence)
    - Bollinger Bands: Upper, Lower, Width
    - Daily Returns & Log Returns
    - Volatility (rolling standard deviation)
    - Price ratios: High/Low, Close/Open
    - Volume features: Volume SMA, Volume ratio
    - Calendar features: Day of week, Month
"""

import pandas as pd
import numpy as np


def compute_sma(series: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=window, min_periods=1).mean()


def compute_ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=span, adjust=False).mean()


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index.
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss over `period` days.
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)  # Neutral when undefined


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal)
    Histogram = MACD - Signal
    Returns: macd_line, signal_line, histogram
    """
    ema_fast = compute_ema(series, fast)
    ema_slow = compute_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0):
    """
    Bollinger Bands.
    Middle = SMA(window)
    Upper = Middle + num_std * STD
    Lower = Middle - num_std * STD
    Returns: upper, middle, lower, bandwidth
    """
    middle = compute_sma(series, window)
    std = series.rolling(window=window, min_periods=1).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    bandwidth = (upper - lower) / middle.replace(0, np.nan)
    return upper, middle, lower, bandwidth.fillna(0)


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all technical indicators to a DataFrame with OHLCV columns.

    Expected input columns: open, high, low, close, volume
    Adds ~25 new feature columns.

    Parameters
    ----------
    df : pd.DataFrame
        Must have columns: open, high, low, close, volume

    Returns
    -------
    pd.DataFrame
        Original DataFrame with technical indicator columns added.
    """
    df = df.copy()

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"].astype(float)

    # ── Moving Averages ──────────────────────────────────────────────
    df["sma_5"] = compute_sma(close, 5)
    df["sma_10"] = compute_sma(close, 10)
    df["sma_20"] = compute_sma(close, 20)
    df["ema_12"] = compute_ema(close, 12)
    df["ema_26"] = compute_ema(close, 26)

    # Price relative to moving averages (normalized)
    df["close_to_sma5"] = close / df["sma_5"].replace(0, np.nan)
    df["close_to_sma20"] = close / df["sma_20"].replace(0, np.nan)

    # ── RSI ──────────────────────────────────────────────────────────
    df["rsi_14"] = compute_rsi(close, 14)

    # ── MACD ─────────────────────────────────────────────────────────
    macd, signal, hist = compute_macd(close)
    df["macd"] = macd
    df["macd_signal"] = signal
    df["macd_hist"] = hist

    # ── Bollinger Bands ──────────────────────────────────────────────
    bb_upper, bb_middle, bb_lower, bb_width = compute_bollinger_bands(close)
    df["bb_upper"] = bb_upper
    df["bb_lower"] = bb_lower
    df["bb_width"] = bb_width
    df["bb_position"] = (close - bb_lower) / (bb_upper - bb_lower).replace(0, np.nan)
    df["bb_position"] = df["bb_position"].fillna(0.5)

    # ── Returns & Volatility ─────────────────────────────────────────
    df["daily_return"] = close.pct_change().fillna(0)
    df["log_return"] = np.log(close / close.shift(1)).fillna(0)
    df["volatility_5"] = df["daily_return"].rolling(window=5, min_periods=1).std()
    df["volatility_20"] = df["daily_return"].rolling(window=20, min_periods=1).std()

    # ── Price Ratios ─────────────────────────────────────────────────
    df["high_low_ratio"] = high / low.replace(0, np.nan)
    df["close_open_ratio"] = close / df["open"].replace(0, np.nan)
    df["price_range"] = high - low

    # ── Volume Features ──────────────────────────────────────────────
    df["volume_sma_5"] = compute_sma(volume, 5)
    df["volume_sma_20"] = compute_sma(volume, 20)
    df["volume_ratio"] = volume / df["volume_sma_20"].replace(0, np.nan)
    df["volume_ratio"] = df["volume_ratio"].fillna(1)

    # ── Calendar Features ────────────────────────────────────────────
    if isinstance(df.index, pd.DatetimeIndex):
        df["day_of_week"] = df.index.dayofweek
        df["month"] = df.index.month
    elif "date" in df.columns:
        dt = pd.to_datetime(df["date"])
        df["day_of_week"] = dt.dt.dayofweek
        df["month"] = dt.dt.month

    # ── Lag Features ─────────────────────────────────────────────────
    for lag in [1, 2, 3, 5]:
        df[f"close_lag_{lag}"] = close.shift(lag)
        df[f"return_lag_{lag}"] = df["daily_return"].shift(lag)

    # Fill any remaining NaN values
    df = df.bfill().ffill().fillna(0)

    return df


def get_feature_columns() -> list:
    """
    Returns the list of feature columns used for model training.
    Excludes raw OHLCV and target columns.
    """
    return [
        # Raw OHLCV (kept as features too)
        "open", "high", "low", "close", "volume",
        # Moving Averages
        "sma_5", "sma_10", "sma_20", "ema_12", "ema_26",
        "close_to_sma5", "close_to_sma20",
        # RSI
        "rsi_14",
        # MACD
        "macd", "macd_signal", "macd_hist",
        # Bollinger Bands
        "bb_upper", "bb_lower", "bb_width", "bb_position",
        # Returns & Volatility
        "daily_return", "log_return", "volatility_5", "volatility_20",
        # Price Ratios
        "high_low_ratio", "close_open_ratio", "price_range",
        # Volume
        "volume_sma_5", "volume_sma_20", "volume_ratio",
        # Calendar
        "day_of_week", "month",
        # Lag Features
        "close_lag_1", "close_lag_2", "close_lag_3", "close_lag_5",
        "return_lag_1", "return_lag_2", "return_lag_3", "return_lag_5",
    ]


if __name__ == "__main__":
    # Quick test with sample data
    print("Testing feature engineering module...")
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    np.random.seed(42)
    base_price = 100.0
    prices = base_price + np.cumsum(np.random.randn(100) * 2)

    test_df = pd.DataFrame({
        "open": prices + np.random.randn(100) * 0.5,
        "high": prices + abs(np.random.randn(100)) * 2,
        "low": prices - abs(np.random.randn(100)) * 2,
        "close": prices,
        "volume": np.random.randint(1_000_000, 10_000_000, 100),
    }, index=dates)

    result = add_technical_indicators(test_df)
    print(f"✅ Input shape: {test_df.shape} → Output shape: {result.shape}")
    print(f"✅ Feature columns ({len(get_feature_columns())}): {get_feature_columns()[:10]}...")
    print(f"✅ NaN count: {result[get_feature_columns()].isna().sum().sum()}")
    print(f"\nSample output (last row):")
    print(result[get_feature_columns()].tail(1).T)
    print("\n✅ Feature engineering module working correctly!")
