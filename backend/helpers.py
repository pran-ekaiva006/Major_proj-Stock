"""
Shared Helper Functions
========================
Yahoo Finance fetching, rate limiting, and refresh logic used by multiple routers.
"""

import os
import time
import logging
import threading
from datetime import datetime, timezone, timedelta

import yfinance as yf
import pandas as pd
import psycopg

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Rate Limiting
# ──────────────────────────────────────────────────────────────────────

RATE_LIMIT_SEC = float(os.getenv("YF_RATE_LIMIT_SEC", "1.0"))
_YF_LOCK = threading.Lock()
_last_call_ts = 0.0


def _rate_limit_wait():
    """Ensure at least RATE_LIMIT_SEC spacing between Yahoo calls."""
    global _last_call_ts
    with _YF_LOCK:
        now = time.time()
        delay = _last_call_ts + RATE_LIMIT_SEC - now
        if delay > 0:
            time.sleep(delay)
        _last_call_ts = time.time()


def _with_backoff(fn, retries=4, base=1.0):
    """Run fn with exponential backoff on exception."""
    for i in range(retries):
        try:
            _rate_limit_wait()
            return fn()
        except Exception as e:
            if i == retries - 1:
                log.warning(f"Final retry failed: {e}")
                return None
            wait = base * (2 ** i)
            log.info(f"Retry {i + 1}/{retries} after {wait}s: {e}")
            time.sleep(wait)


# ──────────────────────────────────────────────────────────────────────
# Yahoo Finance Fetching
# ──────────────────────────────────────────────────────────────────────

def _fetch_history(symbol: str, start_date=None):
    """Fetch historical data from Yahoo Finance with fallbacks."""
    t = yf.Ticker(symbol)

    def safe(fn):
        try:
            return _with_backoff(fn)
        except Exception:
            return None

    if start_date:
        df = safe(lambda: t.history(
            start=start_date,
            end=datetime.now(timezone.utc),
            interval="1d",
            auto_adjust=False,
        ))
        if df is not None and not df.empty:
            return df

    for period in ["5d", "1mo"]:
        df = safe(lambda p=period: t.history(period=p, interval="1d", auto_adjust=False))
        if df is not None and not df.empty:
            return df

    df = safe(lambda: yf.download(symbol, period="5d", interval="1d", progress=False))
    if df is not None and not df.empty:
        return df

    log.error(f"All fetch strategies failed for {symbol}")
    return None


# ──────────────────────────────────────────────────────────────────────
# Database Helpers
# ──────────────────────────────────────────────────────────────────────

def _get_stock_id(symbol: str, conn: psycopg.Connection):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM stocks WHERE symbol=%s", (symbol,))
        row = cur.fetchone()
        return row[0] if row else None


def _get_latest_date(symbol: str, conn: psycopg.Connection):
    stock_id = _get_stock_id(symbol, conn)
    if stock_id is None:
        return None
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(date) FROM stock_prices WHERE stock_id=%s", (stock_id,))
        r = cur.fetchone()
        return r[0]


def _store_history(symbol: str, company_name: str, df: pd.DataFrame, conn: psycopg.Connection):
    """Store fetched price data into the database."""
    if df is None or df.empty:
        return
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO stocks (symbol, company_name)
            VALUES (%s, %s)
            ON CONFLICT (symbol) DO UPDATE SET company_name=EXCLUDED.company_name
            RETURNING id
        """, (symbol, company_name))
        stock_id = cur.fetchone()[0]
        rows = []
        for date, row in df.iterrows():
            rows.append((
                stock_id,
                date.date(),
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
            ))
        cur.executemany("""
            INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (stock_id, date) DO NOTHING
        """, rows)
    conn.commit()


def refresh_symbol(symbol: str, conn: psycopg.Connection):
    """Refresh stock data for a single symbol."""
    symbol = symbol.upper()
    latest_before = _get_latest_date(symbol, conn)
    start = None
    today = datetime.now(timezone.utc).date()

    if latest_before:
        start = latest_before + timedelta(days=1)
        if start > today:
            return {"updated": False, "reason": "up_to_date", "latest": str(latest_before)}

    df = _fetch_history(symbol, start_date=start)

    if df is None or df.empty:
        log.info(f"Incremental fetch for {symbol} yielded no data. Trying fallback.")
        df = _fetch_history(symbol, start_date=None)

    if df is None or df.empty:
        log.error(f"All fetch strategies failed for {symbol}")
        return {
            "updated": False,
            "reason": "fetch_failed_after_retries",
            "latest": str(latest_before) if latest_before else None,
        }

    _store_history(symbol, symbol, df, conn)
    latest_after = _get_latest_date(symbol, conn)
    updated = bool(latest_after and (latest_before is None or latest_after > latest_before))

    return {
        "updated": updated,
        "reason": "ok" if updated else "no_new_rows",
        "latest": str(latest_after),
        "rows_added": len(df),
    }
