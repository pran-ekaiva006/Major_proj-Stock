"""
Predictions Router
===================
ML prediction endpoints with confidence metrics and history tracking.
Heavy ML libraries (pandas, numpy, joblib) are imported lazily to keep startup fast.
"""

import os
import json
import logging

import psycopg
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional

from backend.database import get_db_connection
from backend.models import PredictRequest, PredictResponse

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Predictions"])

# ──────────────────────────────────────────────────────────────────────
# Lazy Model Loading
# ──────────────────────────────────────────────────────────────────────

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'ml_model')
_model = None
_scaler = None
_model_meta = None
_loaded = False


def _load_model_artifacts():
    """Lazily load ML model, scaler, and metadata on first prediction call."""
    global _model, _scaler, _model_meta, _loaded
    if _loaded:
        return

    _loaded = True
    log.info("Loading ML model artifacts (first call)...")

    import joblib

    meta_path = os.path.join(MODEL_DIR, "model_meta.json")
    scaler_path = os.path.join(MODEL_DIR, "scaler.joblib")
    model_path = os.path.join(MODEL_DIR, "stock_predictor.joblib")

    # Load metadata
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            _model_meta = json.load(f)
        log.info(f"Model metadata loaded: best={_model_meta.get('best_model')}")

    # Load scaler
    if os.path.exists(scaler_path):
        _scaler = joblib.load(scaler_path)
        log.info("Feature scaler loaded")

    # Load model
    best_model_type = _model_meta.get("best_model", "linear_regression") if _model_meta else "linear_regression"

    if best_model_type == "lstm":
        try:
            from ml_model.lstm_model import load_lstm_model
            lstm_path = os.path.join(os.path.dirname(__file__), '..', 'ml_model', 'lstm_model.keras')
            if os.path.exists(lstm_path):
                _model = load_lstm_model(lstm_path)
                log.info("LSTM model loaded")
            else:
                log.warning("LSTM model file not found, falling back to joblib model")
                if os.path.exists(model_path):
                    _model = joblib.load(model_path)
        except ImportError:
            log.warning("TensorFlow not available, falling back to joblib model")
            if os.path.exists(model_path):
                _model = joblib.load(model_path)
    else:
        if os.path.exists(model_path):
            _model = joblib.load(model_path)
            log.info(f"ML model loaded ({best_model_type})")
        else:
            log.warning(f"Model file not found at {model_path}")


def _get_model_meta():
    """Get model metadata, loading if needed."""
    _load_model_artifacts()
    return _model_meta


# ──────────────────────────────────────────────────────────────────────
# Feature Engineering for Prediction
# ──────────────────────────────────────────────────────────────────────

def _prepare_features(prices: list):
    """
    Prepare feature vector from price history using the feature engineering pipeline.
    Returns the last row of features (for predicting next day).
    """
    import pandas as pd
    import numpy as np
    from ml_model.feature_engineering import add_technical_indicators, get_feature_columns

    df = pd.DataFrame(prices)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df.set_index('date', inplace=True)

    # Apply feature engineering
    df = add_technical_indicators(df)
    feature_cols = get_feature_columns()

    # Ensure all columns exist
    for c in feature_cols:
        if c not in df.columns:
            df[c] = 0

    # Get the last row
    features = df[feature_cols].iloc[-1:].values

    # Scale if scaler is available
    if _scaler is not None:
        features = _scaler.transform(features)

    return features


# ──────────────────────────────────────────────────────────────────────
# Helper to query stock data (imported lazily to avoid circular import)
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

    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded. Run train.py first.")

    data = _query_stock(req.symbol, conn)
    if not data or not data["prices"]:
        raise HTTPException(status_code=404, detail="No data available for this symbol")

    # Need at least 30 price points for meaningful technical indicators
    if len(data["prices"]) < 30:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 30 data points, got {len(data['prices'])}"
        )

    try:
        import numpy as np
        features = _prepare_features(data["prices"])
        prediction = float(_model.predict(features)[0])
    except Exception as e:
        log.error(f"Prediction failed for {req.symbol}: {e}")
        import pandas as pd
        latest = data["prices"][0]
        df = pd.DataFrame([latest])
        try:
            prediction = float(_model.predict(df[["open", "high", "low", "close", "volume"]])[0])
        except Exception:
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

    # Calculate confidence as a simple function of R²
    confidence = None
    if _model_meta and "best_r2" in _model_meta:
        confidence = round(max(0, min(100, _model_meta["best_r2"] * 100)), 1)

    return PredictResponse(
        symbol=req.symbol.upper(),
        predicted_next_day_close=round(prediction, 2),
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
