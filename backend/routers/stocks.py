"""
Stock Data Router
==================
Handles all stock-related API endpoints.
"""

import logging
from datetime import datetime, timezone, timedelta

import psycopg
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends, Query

from backend.database import get_db_connection
from backend.helpers import refresh_symbol

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Stocks"])


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def query_stock_data(search_term: str, conn: psycopg.Connection):
    """Search for a stock by symbol or name and return its price history."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, symbol, company_name
            FROM stocks WHERE symbol ILIKE %s OR company_name ILIKE %s
        """, (f"%{search_term}%", f"%{search_term}%"))
        stock = cur.fetchone()
        if not stock:
            return None
        stock_id, symbol, name = stock

        today = datetime.now(timezone.utc).date()
        cur.execute("""
            SELECT date, open, high, low, close, volume
            FROM stock_prices
            WHERE stock_id=%s AND date <= %s
            ORDER BY date DESC
            LIMIT 365
        """, (stock_id, today))
        rows = cur.fetchall()

        if not rows:
            return {"symbol": symbol, "company_name": name, "prices": []}

        return {
            "symbol": symbol,
            "company_name": name,
            "prices": [
                {
                    "date": r[0].isoformat(),
                    "open": float(r[1]),
                    "high": float(r[2]),
                    "low": float(r[3]),
                    "close": float(r[4]),
                    "volume": int(r[5]),
                }
                for r in rows
            ],
        }


def get_live_info(symbol: str, conn: psycopg.Connection):
    """Get the most recent price data from the database."""
    sym = symbol.upper()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT sp.close, sp.high, sp.low, s.company_name
            FROM stock_prices sp
            JOIN stocks s ON s.id = sp.stock_id
            WHERE s.symbol = %s
            ORDER BY sp.date DESC
            LIMIT 1
        """, (sym,))
        latest_record = cur.fetchone()

    if not latest_record:
        return None

    close, high, low, name = latest_record
    return {
        "currentPrice": float(close) if close else None,
        "dayHigh": float(high) if high else None,
        "dayLow": float(low) if low else None,
        "marketCap": None,
        "previousClose": None,
        "source": "database",
    }


# ──────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────

@router.get("/stocks/{term}")
def get_stock(
    term: str,
    refresh: int = Query(0),
    conn: psycopg.Connection = Depends(get_db_connection),
):
    """Get stock data by symbol or company name."""
    data = query_stock_data(term, conn)
    if not data:
        raise HTTPException(status_code=404, detail="Stock not found")

    if refresh:
        refresh_symbol(data["symbol"], conn)
        data = query_stock_data(term, conn)

    live = get_live_info(data["symbol"], conn)
    if live:
        data["live_info"] = live
    return data


@router.get("/live/{symbol}")
def live(
    symbol: str,
    conn: psycopg.Connection = Depends(get_db_connection),
):
    """Get the latest price data for a symbol."""
    info = get_live_info(symbol.upper(), conn)
    if info:
        return {"symbol": symbol.upper(), "live_info": info}
    raise HTTPException(status_code=404, detail="No data for this symbol in the database.")


@router.get("/symbols")
def list_symbols(conn: psycopg.Connection = Depends(get_db_connection)):
    """List all available stock symbols."""
    with conn.cursor() as cur:
        cur.execute("SELECT symbol FROM stocks ORDER BY symbol")
        return [r[0] for r in cur.fetchall()]
