"""
Predictions Router
===================
ML prediction endpoints with confidence metrics and history tracking.
Uses lightweight numpy-based models for fast startup and predictions.
"""

import os
import json
import logging

import psycopg
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from backend.database import get_db_connection
from backend.models import PredictRequest, PredictResponse

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Predictions"])

# ──────────────────────────────────────────────────────────────────────
# Lazy Model Loading
# ──────────────────────────────────────────────────────────────────────

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'ml_model')
_weights = None
_scaler_mean = None
_scaler_std = None
_model_meta = None
_loaded = False


def _load_model_artifacts():
    """Lazily load ML model weights and metadata on first prediction call."""
    global _weights, _scaler_mean, _scaler_std, _model_meta, _loaded
    if _loaded:
        return

    _loaded = True
    log.info("Loading ML model artifacts...")

    import numpy as np

    meta_path = os.path.join(MODEL_DIR, "model_meta.json")
    weights_path = os.path.join(MODEL_DIR, "lr_weights.npy")
    mean_path = os.path.join(MODEL_DIR, "scaler_mean.npy")
    std_path = os.path.join(MODEL_DIR, "scaler_std.npy")

    # Load metadata
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            _model_meta = json.load(f)
        log.info(f"Model metadata loaded: best={_model_meta.get('best_model')}")

    # Load numpy weights and scaler
    if os.path.exists(weights_path):
        _weights = np.load(weights_path)
        log.info(f"Model weights loaded ({len(_weights)} params)")

    if os.path.exists(mean_path):
        _scaler_mean = np.load(mean_path)
        log.info("Scaler mean loaded")

    if os.path.exists(std_path):
        _scaler_std = np.load(std_path)
        log.info("Scaler std loaded")


def _get_model_meta():
    """Get model metadata, loading if needed."""
    _load_model_artifacts()
    return _model_meta


# ──────────────────────────────────────────────────────────────────────
# Feature Engineering for Prediction
# ──────────────────────────────────────────────────────────────────────

def _prepare_features(prices: list, feature_cols: list):
    """
    Prepare feature vector from price history.
    Returns the last row of features and the current close price.
    """
    import pandas as pd
    import numpy as np
    from ml_model.feature_engineering import add_technical_indicators

    df = pd.DataFrame(prices)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    # Convert Decimal to float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = df[col].astype(float)
    df.set_index('date', inplace=True)

    # Apply feature engineering
    df = add_technical_indicators(df)

    # Get current close price (last row)
    current_close = float(df['close'].iloc[-1])

    # Ensure all feature columns exist
    for c in feature_cols:
        if c not in df.columns:
            df[c] = 0

    # Get the last row of features
    features = df[feature_cols].iloc[-1:].values.astype(float)

    return features, current_close


# ──────────────────────────────────────────────────────────────────────
# Prediction function
# ──────────────────────────────────────────────────────────────────────

def _predict_next_close(features, current_close):
    """
    Predict next-day closing price.
    Model predicts % change, which is applied to current close.
    """
    import numpy as np

    # Standardize features
    if _scaler_mean is not None and _scaler_std is not None:
        features = (features - _scaler_mean) / _scaler_std

    # Add bias term
    X_b = np.column_stack([features, np.ones(len(features))])

    # Predict percentage change
    pct_change = float(X_b @ _weights)

    # Clamp to reasonable range (-10% to +10% daily)
    pct_change = max(-10.0, min(10.0, pct_change))

    # Apply to current price
    predicted_price = current_close * (1 + pct_change / 100)

    return round(predicted_price, 2)


# ──────────────────────────────────────────────────────────────────────
# Helper imports
# ──────────────────────────────────────────────────────────────────────

def _query_stock(symbol: str, conn):
    from backend.routers.stocks import query_stock_data
    return query_stock_data(symbol, conn)

def _get_live(symbol: str, conn):
    from backend.routers.stocks import get_live_info
    return get_live_info(symbol, conn)


# ──────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────

@router.post("/predict", response_model=PredictResponse)
def predict(
    req: PredictRequest,
    conn: psycopg.Connection = Depends(get_db_connection),
):
    """Predict next-day closing price using the best ML model."""
    _load_model_artifacts()

    if _weights is None:
        raise HTTPException(status_code=503, detail="Model not loaded. Run train.py first.")

    data = _query_stock(req.symbol, conn)
    if not data or not data["prices"]:
        raise HTTPException(status_code=404, detail="No data available for this symbol")

    if len(data["prices"]) < 30:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 30 data points, got {len(data['prices'])}"
        )

    # Get feature columns from metadata (excluding 'close')
    feature_cols = _model_meta.get("features_used", []) if _model_meta else []
    if not feature_cols:
        raise HTTPException(status_code=503, detail="Model metadata missing feature list")

    try:
        features, current_close = _prepare_features(data["prices"], feature_cols)
        prediction = _predict_next_close(features, current_close)
    except Exception as e:
        log.error(f"Prediction failed for {req.symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    # Build response
    live = _get_live(req.symbol, conn)
    best_model_name = _model_meta.get("best_model", "unknown") if _model_meta else "unknown"

    # Get metrics for the best model
    metrics_data = None
    if _model_meta and "results" in _model_meta:
        for r in _model_meta["results"]:
            if r.get("Model", "").lower().replace(" ", "_") == best_model_name:
                metrics_data = {
                    "model_name": r["Model"],
                    "r2": r.get("R²"),
                    "mae": r.get("MAE"),
                    "rmse": r.get("RMSE"),
                    "mape": r.get("MAPE (%)"),
                    "directional_accuracy": r.get("Directional Accuracy (%)"),
                }
                break

    confidence = None
    if _model_meta and "best_r2" in _model_meta:
        confidence = round(max(0, min(100, _model_meta["best_r2"] * 100)), 1)

    return PredictResponse(
        symbol=req.symbol.upper(),
        predicted_next_day_close=prediction,
        model_used=best_model_name,
        confidence=confidence,
        metrics=metrics_data,
        live_info=live,
    )


@router.get("/model-info")
def model_info():
    """Return model metadata and comparison results."""
    meta = _get_model_meta()
    if meta is None:
        raise HTTPException(status_code=404, detail="No model metadata found. Run train.py first.")
    return meta


@router.get("/predictions/history")
def prediction_history(
    conn: psycopg.Connection = Depends(get_db_connection),
    limit: int = 50,
):
    """Get recent prediction history."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, symbol, predicted_close, actual_close, model_used, confidence, predicted_at
                FROM prediction_history
                ORDER BY predicted_at DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
    except psycopg.errors.UndefinedTable:
        return []

    return [
        {
            "id": r[0],
            "symbol": r[1],
            "predicted_close": float(r[2]),
            "actual_close": float(r[3]) if r[3] else None,
            "model_used": r[4],
            "confidence": float(r[5]) if r[5] else None,
            "predicted_at": r[6].isoformat() if r[6] else None,
        }
        for r in rows
    ]
