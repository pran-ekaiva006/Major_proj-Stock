"""
Multi-Model Stock Price Prediction Training Pipeline
=====================================================
Trains and compares multiple ML models using engineered features.

Models:
    1. Linear Regression (baseline)
    2. Random Forest Regressor
    3. XGBoost (Gradient Boosting)
    4. LSTM (Deep Learning)

Process:
    1. Fetch data from PostgreSQL
    2. Apply feature engineering (technical indicators)
    3. Time-series aware train/val/test split (70/15/15)
    4. Train all models with proper scaling
    5. Evaluate: MAE, RMSE, MAPE, R², Directional Accuracy
    6. Auto-select best model → save to disk
    7. Output comparison CSV for project report
"""

import os
import sys
import json
import warnings
import logging

import psycopg
import pandas as pd
import numpy as np
import joblib
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from ml_model.feature_engineering import add_technical_indicators, get_feature_columns

warnings.filterwarnings('ignore')

# Setup
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
MODEL_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(MODEL_DIR, "results")
BACKEND_MODEL_DIR = os.path.join(MODEL_DIR, '..', 'backend', 'ml_model')

# Sequence length for LSTM
LSTM_SEQ_LEN = 60


# ──────────────────────────────────────────────────────────────────────
# 📊 Metrics
# ──────────────────────────────────────────────────────────────────────

def mean_absolute_percentage_error(y_true, y_pred):
    """MAPE — ignores zeros in y_true to avoid division errors."""
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def directional_accuracy(y_true, y_pred):
    """
    Percentage of times the model correctly predicts the direction of change.
    Compares sign(y_pred[t] - y_true[t-1]) vs sign(y_true[t] - y_true[t-1]).
    """
    if len(y_true) < 2:
        return 0.0
    actual_direction = np.sign(np.diff(y_true))
    pred_direction = np.sign(y_pred[1:] - y_true[:-1])
    return np.mean(actual_direction == pred_direction) * 100


def evaluate_model(y_true, y_pred, model_name="Model"):
    """Compute all evaluation metrics and return as a dict."""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = mean_absolute_percentage_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    da = directional_accuracy(y_true, y_pred)

    metrics = {
        "Model": model_name,
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "MAPE (%)": round(mape, 2),
        "R²": round(r2, 4),
        "Directional Accuracy (%)": round(da, 2),
    }

    log.info(
        f"  {model_name:25s} | R²={r2:.4f} | MAE={mae:.4f} | "
        f"RMSE={rmse:.4f} | MAPE={mape:.2f}% | DA={da:.1f}%"
    )
    return metrics


# ──────────────────────────────────────────────────────────────────────
# 🗄️ Data Loading
# ──────────────────────────────────────────────────────────────────────

def load_data():
    """Fetch all stock price data from PostgreSQL."""
    log.info("Connecting to database...")
    conn = psycopg.connect(DATABASE_URL)

    df = pd.read_sql(
        "SELECT date, open, high, low, close, volume FROM stock_prices ORDER BY date",
        conn
    )
    conn.close()

    if df.empty:
        raise ValueError("No data found in database. Run the data pipeline first.")

    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df = df.sort_index()

    log.info(f"Loaded {len(df):,} records from {df.index.min().date()} to {df.index.max().date()}")
    return df


# ──────────────────────────────────────────────────────────────────────
# 🧠 Training Pipeline
# ──────────────────────────────────────────────────────────────────────

def train_and_save_model():
    """Main training pipeline: engineer features, train models, compare, save best."""

    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(BACKEND_MODEL_DIR, exist_ok=True)

    # ── 1. Load and engineer features ─────────────────────────────────
    df = load_data()

    log.info("Applying feature engineering (technical indicators)...")
    df = add_technical_indicators(df)

    # Target: next day's close price
    df['target'] = df['close'].shift(-1)
    df.dropna(subset=['target'], inplace=True)

    feature_cols = get_feature_columns()
    # Ensure all feature columns exist
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        log.warning(f"Missing feature columns (will be filled with 0): {missing}")
        for c in missing:
            df[c] = 0

    X = df[feature_cols].values
    y = df['target'].values

    log.info(f"Feature matrix: {X.shape[0]:,} samples × {X.shape[1]} features")

    # ── 2. Time-series split (70/15/15) ───────────────────────────────
    n = len(X)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]

    log.info(
        f"Split: Train={len(X_train):,} | "
        f"Val={len(X_val):,} | Test={len(X_test):,}"
    )

    # ── 3. Scale features ────────────────────────────────────────────
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    # Scale target for LSTM (separate scaler)
    target_scaler = StandardScaler()
    y_train_scaled = target_scaler.fit_transform(y_train.reshape(-1, 1)).flatten()
    y_val_scaled = target_scaler.transform(y_val.reshape(-1, 1)).flatten()
    y_test_scaled = target_scaler.transform(y_test.reshape(-1, 1)).flatten()

    # ── 4. Train models ──────────────────────────────────────────────
    results = []
    models = {}

    # --- Model 1: Linear Regression (baseline) ---
    log.info("\n📈 Training Linear Regression (baseline)...")
    lr = LinearRegression()
    lr.fit(X_train_scaled, y_train)
    y_pred_lr = lr.predict(X_test_scaled)
    results.append(evaluate_model(y_test, y_pred_lr, "Linear Regression"))
    models["linear_regression"] = lr

    # --- Model 2: Random Forest ---
    log.info("\n🌲 Training Random Forest...")
    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=42
    )
    rf.fit(X_train_scaled, y_train)
    y_pred_rf = rf.predict(X_test_scaled)
    results.append(evaluate_model(y_test, y_pred_rf, "Random Forest"))
    models["random_forest"] = rf

    # --- Model 3: XGBoost ---
    log.info("\n🚀 Training XGBoost...")
    try:
        from xgboost import XGBRegressor
        xgb = XGBRegressor(
            n_estimators=300,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            n_jobs=-1,
            random_state=42,
            verbosity=0
        )
        xgb.fit(
            X_train_scaled, y_train,
            eval_set=[(X_val_scaled, y_val)],
            verbose=False
        )
        y_pred_xgb = xgb.predict(X_test_scaled)
        results.append(evaluate_model(y_test, y_pred_xgb, "XGBoost"))
        models["xgboost"] = xgb
    except ImportError:
        log.warning("⚠️  xgboost not installed. Skipping XGBoost model.")
        log.warning("   Install with: pip install xgboost")

    # --- Model 4: LSTM ---
    log.info("\n🧠 Training LSTM (Deep Learning)...")
    try:
        from ml_model.lstm_model import train_lstm, predict_lstm, save_lstm_model

        lstm_model, lstm_history = train_lstm(
            X_train_scaled, y_train_scaled,
            X_val_scaled, y_val_scaled,
            sequence_length=LSTM_SEQ_LEN,
            epochs=100,
            batch_size=32,
            verbose=0
        )

        # Predict on test set
        y_pred_lstm_scaled = predict_lstm(lstm_model, X_test_scaled, LSTM_SEQ_LEN)

        if len(y_pred_lstm_scaled) > 0:
            # Inverse transform predictions
            y_pred_lstm = target_scaler.inverse_transform(
                y_pred_lstm_scaled.reshape(-1, 1)
            ).flatten()
            # Align test targets (LSTM predictions start at index seq_len)
            y_test_lstm = y_test[LSTM_SEQ_LEN:]
            results.append(evaluate_model(y_test_lstm, y_pred_lstm, "LSTM"))
            models["lstm"] = lstm_model

            # Save LSTM model separately (Keras format)
            lstm_path = os.path.join(MODEL_DIR, "lstm_model.keras")
            save_lstm_model(lstm_model, lstm_path)
        else:
            log.warning("  LSTM produced no predictions (not enough test data for sequences)")
    except ImportError:
        log.warning("⚠️  TensorFlow not installed. Skipping LSTM model.")
        log.warning("   Install with: pip install tensorflow")
    except Exception as e:
        log.warning(f"⚠️  LSTM training failed: {e}")

    # ── 5. Compare and select best model ─────────────────────────────
    if not results:
        log.error("No models were trained successfully!")
        return

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values("R²", ascending=False)

    print("\n" + "=" * 80)
    print("📊 MODEL COMPARISON RESULTS")
    print("=" * 80)
    print(results_df.to_string(index=False))
    print("=" * 80)

    best_name = results_df.iloc[0]["Model"]
    best_r2 = results_df.iloc[0]["R²"]
    log.info(f"\n🏆 Best Model: {best_name} (R² = {best_r2:.4f})")

    # Map display name back to dict key
    name_to_key = {
        "Linear Regression": "linear_regression",
        "Random Forest": "random_forest",
        "XGBoost": "xgboost",
        "LSTM": "lstm",
    }
    best_key = name_to_key.get(best_name, "linear_regression")
    best_model = models.get(best_key)

    # ── 6. Save artifacts ────────────────────────────────────────────

    # Save comparison CSV
    csv_path = os.path.join(RESULTS_DIR, "model_comparison.csv")
    results_df.to_csv(csv_path, index=False)
    log.info(f"📄 Comparison CSV saved to {csv_path}")

    # Save scaler
    scaler_path = os.path.join(MODEL_DIR, "scaler.joblib")
    joblib.dump(scaler, scaler_path)
    log.info(f"📦 Scaler saved to {scaler_path}")

    # Save target scaler (for LSTM inverse transform)
    target_scaler_path = os.path.join(MODEL_DIR, "target_scaler.joblib")
    joblib.dump(target_scaler, target_scaler_path)

    # Save feature columns list
    meta = {
        "feature_columns": feature_cols,
        "best_model": best_key,
        "best_r2": float(best_r2),
        "sequence_length": LSTM_SEQ_LEN,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "results": results,
    }
    meta_path = os.path.join(MODEL_DIR, "model_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    log.info(f"📋 Model metadata saved to {meta_path}")

    # Save best sklearn model (if not LSTM)
    if best_key != "lstm" and best_model is not None:
        model_path = os.path.join(MODEL_DIR, "stock_predictor.joblib")
        joblib.dump(best_model, model_path)
        log.info(f"💾 Best model ({best_name}) saved to {model_path}")

        # Copy to backend
        backend_path = os.path.join(BACKEND_MODEL_DIR, "stock_predictor.joblib")
        joblib.dump(best_model, backend_path)
        log.info(f"📦 Model copied to {backend_path}")

        # Also copy scaler and meta to backend
        joblib.dump(scaler, os.path.join(BACKEND_MODEL_DIR, "scaler.joblib"))
        with open(os.path.join(BACKEND_MODEL_DIR, "model_meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
    elif best_key == "lstm":
        # For LSTM, the keras model is already saved
        # Copy scaler + meta to backend
        joblib.dump(scaler, os.path.join(BACKEND_MODEL_DIR, "scaler.joblib"))
        joblib.dump(target_scaler, os.path.join(BACKEND_MODEL_DIR, "target_scaler.joblib"))
        with open(os.path.join(BACKEND_MODEL_DIR, "model_meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
        log.info(f"💾 Best model (LSTM) artifacts copied to backend")

    # Also save ALL sklearn models for comparison page
    for key, m in models.items():
        if key != "lstm":
            path = os.path.join(RESULTS_DIR, f"{key}.joblib")
            joblib.dump(m, path)

    # Save feature importances for tree-based models
    for key in ["random_forest", "xgboost"]:
        if key in models:
            imp = models[key].feature_importances_
            imp_df = pd.DataFrame({
                "feature": feature_cols,
                "importance": imp
            }).sort_values("importance", ascending=False)
            imp_path = os.path.join(RESULTS_DIR, f"{key}_feature_importance.csv")
            imp_df.to_csv(imp_path, index=False)
            log.info(f"📊 Feature importance saved: {imp_path}")
            print(f"\n  Top 10 features ({key}):")
            print(imp_df.head(10).to_string(index=False))

    print("\n✅ Training pipeline complete!")
    print(f"   Results saved to: {RESULTS_DIR}/")
    print(f"   Best model ({best_name}) ready for predictions.\n")

    return results_df


if __name__ == "__main__":
    train_and_save_model()