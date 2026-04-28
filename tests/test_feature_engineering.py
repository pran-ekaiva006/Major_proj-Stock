"""
Tests for Feature Engineering Module
======================================
"""

import numpy as np
import pandas as pd
import pytest

from ml_model.feature_engineering import (
    add_technical_indicators,
    get_feature_columns,
    compute_sma,
    compute_ema,
    compute_rsi,
    compute_macd,
    compute_bollinger_bands,
)


class TestComputeSMA:
    def test_basic_sma(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = compute_sma(s, 3)
        assert round(result.iloc[-1], 2) == 4.0  # (3+4+5)/3

    def test_sma_window_1(self):
        s = pd.Series([10, 20, 30])
        result = compute_sma(s, 1)
        assert list(result) == [10, 20, 30]


class TestComputeEMA:
    def test_ema_returns_series(self):
        s = pd.Series(range(20))
        result = compute_ema(s, 12)
        assert len(result) == 20
        assert not result.isna().any()


class TestComputeRSI:
    def test_rsi_range(self):
        np.random.seed(42)
        s = pd.Series(100 + np.cumsum(np.random.randn(100)))
        result = compute_rsi(s, 14)
        assert result.min() >= 0
        assert result.max() <= 100

    def test_rsi_all_gains(self):
        s = pd.Series(range(1, 30))
        result = compute_rsi(s, 14)
        assert result.iloc[-1] > 80  # Should be very high


class TestComputeMACD:
    def test_macd_returns_three_series(self):
        s = pd.Series(range(50), dtype=float)
        macd, signal, hist = compute_macd(s)
        assert len(macd) == 50
        assert len(signal) == 50
        assert len(hist) == 50


class TestComputeBollingerBands:
    def test_bollinger_bands(self):
        s = pd.Series(range(30), dtype=float)
        upper, middle, lower, width = compute_bollinger_bands(s, 20)
        assert (upper >= middle).all()
        assert (middle >= lower).all()


class TestAddTechnicalIndicators:
    def test_output_shape(self, sample_ohlcv_df):
        result = add_technical_indicators(sample_ohlcv_df)
        assert result.shape[0] == sample_ohlcv_df.shape[0]
        assert result.shape[1] > sample_ohlcv_df.shape[1]

    def test_no_nans(self, sample_ohlcv_df):
        result = add_technical_indicators(sample_ohlcv_df)
        feature_cols = get_feature_columns()
        available = [c for c in feature_cols if c in result.columns]
        nan_count = result[available].isna().sum().sum()
        assert nan_count == 0

    def test_feature_columns_exist(self, sample_ohlcv_df):
        result = add_technical_indicators(sample_ohlcv_df)
        feature_cols = get_feature_columns()
        for col in feature_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_calendar_features(self, sample_ohlcv_df):
        result = add_technical_indicators(sample_ohlcv_df)
        assert "day_of_week" in result.columns
        assert "month" in result.columns
        assert result["day_of_week"].min() >= 0
        assert result["day_of_week"].max() <= 6

    def test_lag_features(self, sample_ohlcv_df):
        result = add_technical_indicators(sample_ohlcv_df)
        for lag in [1, 2, 3, 5]:
            assert f"close_lag_{lag}" in result.columns
            assert f"return_lag_{lag}" in result.columns


class TestGetFeatureColumns:
    def test_returns_list(self):
        cols = get_feature_columns()
        assert isinstance(cols, list)
        assert len(cols) > 20  # Should have 30+ features

    def test_includes_core_features(self):
        cols = get_feature_columns()
        for f in ["open", "high", "low", "close", "volume", "rsi_14", "macd", "sma_20"]:
            assert f in cols, f"Missing core feature: {f}"
