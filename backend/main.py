"""
Stock Predictor API — Main Application
========================================
FastAPI application entry point. All business logic is in routers/.

Endpoints:
    /api/stocks/*       — Stock data (search, live, symbols)
    /api/predict        — ML predictions
    /api/auth/*         — Authentication (register, login, Google OAuth)
    /api/watchlist/*    — User watchlist (requires auth)
    /api/sentiment/*    — News sentiment analysis
    /api/model-info     — Model metadata and comparison results
    /internal/*         — Admin endpoints (refresh, health)
    /health/db          — Database health check
    /docs               — Auto-generated API documentation
"""

import os
import logging

import psycopg
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.database import get_db_connection

# ──────────────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# App Initialization
# ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AlphaPredict — Stock Price Predictor",
    description="ML-powered stock price prediction with technical indicators, sentiment analysis, and model comparison.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "https://stock-predictor-five-opal.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────
# Register Routers
# ──────────────────────────────────────────────────────────────────────

from backend.routers import stocks, predictions, internal, auth, watchlist, sentiment

app.include_router(stocks.router)
app.include_router(predictions.router)
app.include_router(auth.router)
app.include_router(watchlist.router)
app.include_router(sentiment.router)
app.include_router(internal.router)

# ──────────────────────────────────────────────────────────────────────
# Root & Health Endpoints
# ──────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    """Health check / root endpoint."""
    return {"ok": True, "service": "stock-predictor", "version": "2.0.0"}


@app.get("/health/db", tags=["Health"])
def health(conn: psycopg.Connection = Depends(get_db_connection)):
    """Check database connectivity."""
    with conn.cursor() as c:
        c.execute("SELECT 1")
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)