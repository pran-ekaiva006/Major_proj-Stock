"""
Test Configuration and Fixtures
=================================
Shared fixtures for all test modules.
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def sample_ohlcv_df():
    """Create a sample OHLCV DataFrame for testing."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=200, freq="B")
    base = 100.0 + np.cumsum(np.random.randn(200) * 2)

    return pd.DataFrame({
        "open": base + np.random.randn(200) * 0.5,
        "high": base + abs(np.random.randn(200)) * 2,
        "low": base - abs(np.random.randn(200)) * 2,
        "close": base,
        "volume": np.random.randint(1_000_000, 10_000_000, 200),
    }, index=dates)


@pytest.fixture
def sample_prices_list():
    """Create a sample prices list as returned by the API."""
    np.random.seed(42)
    base = 150.0
    prices = []
    for i in range(100):
        d = pd.Timestamp("2024-06-01") - pd.Timedelta(days=i)
        close = base + np.random.randn() * 3
        prices.append({
            "date": d.isoformat(),
            "open": close + np.random.randn() * 0.5,
            "high": close + abs(np.random.randn()) * 2,
            "low": close - abs(np.random.randn()) * 2,
            "close": close,
            "volume": int(np.random.randint(1_000_000, 10_000_000)),
        })
        base = close
    return prices
