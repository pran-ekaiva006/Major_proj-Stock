"""
Pydantic Models for Request/Response Validation
=================================================
Defines all data transfer objects used across API endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ──────────────────────────────────────────────────────────────────────
# 🔐 Auth Models
# ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """Registration request."""
    username: str = Field(..., min_length=3, max_length=50, examples=["pranjal"])
    email: str = Field(..., examples=["pranjal@example.com"])
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    """Login request."""
    email: str = Field(..., examples=["pranjal@example.com"])
    password: str = Field(..., min_length=1)


class GoogleAuthRequest(BaseModel):
    """Google OAuth token exchange."""
    token: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    username: str
    email: str


class UserResponse(BaseModel):
    """Current user info."""
    id: int
    username: str
    email: str


# ──────────────────────────────────────────────────────────────────────
# 📊 Stock Models
# ──────────────────────────────────────────────────────────────────────

class PricePoint(BaseModel):
    """Single OHLCV data point."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class LiveInfo(BaseModel):
    """Live/latest price info."""
    currentPrice: Optional[float] = None
    dayHigh: Optional[float] = None
    dayLow: Optional[float] = None
    marketCap: Optional[float] = None
    previousClose: Optional[float] = None
    source: str = "database"


class StockResponse(BaseModel):
    """Stock data response."""
    symbol: str
    company_name: str
    prices: List[PricePoint]
    live_info: Optional[LiveInfo] = None


# ──────────────────────────────────────────────────────────────────────
# 🤖 Prediction Models
# ──────────────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    """Prediction request."""
    symbol: str = Field(..., examples=["AAPL"])


class ModelMetrics(BaseModel):
    """Model performance metrics."""
    model_name: str
    r2: Optional[float] = None
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    directional_accuracy: Optional[float] = None


class PredictResponse(BaseModel):
    """Prediction response with confidence metrics."""
    symbol: str
    predicted_next_day_close: float
    model_used: str
    confidence: Optional[float] = None
    metrics: Optional[ModelMetrics] = None
    live_info: Optional[LiveInfo] = None


# ──────────────────────────────────────────────────────────────────────
# 📋 Watchlist Models
# ──────────────────────────────────────────────────────────────────────

class WatchlistAdd(BaseModel):
    """Add to watchlist request."""
    symbol: str = Field(..., examples=["AAPL"])


class WatchlistItem(BaseModel):
    """Watchlist item response."""
    symbol: str
    added_at: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────
# 📜 Prediction History Models
# ──────────────────────────────────────────────────────────────────────

class PredictionHistoryItem(BaseModel):
    """Single prediction history entry."""
    id: int
    symbol: str
    predicted_close: float
    actual_close: Optional[float] = None
    model_used: Optional[str] = None
    confidence: Optional[float] = None
    predicted_at: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────
# 🔄 Internal Models
# ──────────────────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    """Internal refresh request."""
    symbols: List[str]


class RefreshResult(BaseModel):
    """Refresh result for a single symbol."""
    updated: bool
    reason: str
    latest: Optional[str] = None
    rows_added: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response."""
    ok: bool
    service: str = "stock-predictor"
