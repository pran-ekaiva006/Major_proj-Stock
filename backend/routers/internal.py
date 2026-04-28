"""
Internal Router
================
Admin/internal endpoints for data refresh, health checks, and monitoring.
Protected by a shared secret.
"""

import os
import time
import logging
import asyncio
from datetime import datetime, timezone, timedelta

import psycopg
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse

from backend.database import get_db_connection, get_pool
from backend.helpers import refresh_symbol

log = logging.getLogger(__name__)
router = APIRouter(prefix="/internal", tags=["Internal"])

REFRESH_SECRET = os.getenv("REFRESH_SECRET", "change_me")


# ──────────────────────────────────────────────────────────────────────
# Streaming Refresh
# ──────────────────────────────────────────────────────────────────────

async def _stream_full_refresh():
    """Async generator that yields refresh progress as strings."""
    yield "Starting streamed background task: Refreshing stale stocks.\n"

    db_pool = get_pool()

    def get_stale_symbols():
        yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
        with db_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT s.symbol
                    FROM stocks s
                    LEFT JOIN (
                        SELECT stock_id, MAX(date) as max_date
                        FROM stock_prices GROUP BY stock_id
                    ) p ON s.id = p.stock_id
                    WHERE p.max_date IS NULL OR p.max_date < %s
                    ORDER BY s.symbol
                """, (yesterday,))
                return [r[0] for r in cur.fetchall()]

    symbols_to_refresh = await asyncio.to_thread(get_stale_symbols)

    if not symbols_to_refresh:
        yield "All stocks are up-to-date. Nothing to do.\n"
        return

    yield f"Found {len(symbols_to_refresh)} stale symbols to refresh.\n"

    updated_count = 0
    failed_symbols = []

    for i, symbol in enumerate(symbols_to_refresh):
        try:
            yield f"({i+1}/{len(symbols_to_refresh)}) Refreshing {symbol}...\n"
            with db_pool.connection() as conn_for_symbol:
                result = await asyncio.to_thread(refresh_symbol, symbol, conn_for_symbol)
            if result.get("updated"):
                updated_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            yield f"Error refreshing {symbol}: {e}\n"
            failed_symbols.append(symbol)

    yield f"\nBackground refresh complete. Updated: {updated_count}/{len(symbols_to_refresh)}\n"
    if failed_symbols:
        yield f"Failed symbols: {', '.join(failed_symbols)}\n"


# ──────────────────────────────────────────────────────────────────────
# Background Refresh
# ──────────────────────────────────────────────────────────────────────

def _run_full_refresh(conn: psycopg.Connection):
    """Synchronous full refresh for background tasks."""
    log.info("Starting background task: Full database refresh.")
    with conn.cursor() as cur:
        cur.execute("SELECT symbol FROM stocks ORDER BY symbol")
        symbols = [r[0] for r in cur.fetchall()]

    log.info(f"Found {len(symbols)} symbols to refresh.")
    updated_count = 0

    for i, symbol in enumerate(symbols):
        try:
            log.info(f"({i+1}/{len(symbols)}) Refreshing {symbol}...")
            result = refresh_symbol(symbol, conn)
            if result.get("updated"):
                updated_count += 1
            time.sleep(0.1)
        except Exception as e:
            log.error(f"Error refreshing {symbol}: {e}")

    log.info(f"Refresh complete. Updated: {updated_count}/{len(symbols)}")


# ──────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────

@router.post("/refresh-all-stream")
async def refresh_all_stocks_stream(secret: str = Query(None)):
    """Triggers a full refresh and streams logs back."""
    if secret != REFRESH_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return StreamingResponse(_stream_full_refresh(), media_type="text/plain")


@router.post("/refresh-all")
def refresh_all_stocks(
    background_tasks: BackgroundTasks,
    secret: str = Query(None),
    conn: psycopg.Connection = Depends(get_db_connection),
):
    """Triggers a full refresh as a background task."""
    if secret != REFRESH_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    background_tasks.add_task(_run_full_refresh, conn)
    return {"message": "Full data refresh started in the background."}


@router.post("/refresh")
def internal_refresh(
    payload: dict,
    secret: str = Query(None),
    conn: psycopg.Connection = Depends(get_db_connection),
):
    """Refresh specific symbols."""
    if secret != REFRESH_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    symbols = payload.get("symbols") or []
    if not isinstance(symbols, list) or not symbols:
        raise HTTPException(status_code=400, detail="symbols list required")

    results = {}
    updated = []
    failed = []

    for s in symbols:
        try:
            log.info(f"Refreshing {s}...")
            res = refresh_symbol(s, conn)
            results[s.upper()] = res
            if res.get("updated"):
                updated.append(s.upper())
            else:
                failed.append(s.upper())
        except Exception as e:
            log.error(f"Error refreshing {s}: {e}")
            results[s.upper()] = {"updated": False, "reason": f"error:{str(e)[:200]}"}
            failed.append(s.upper())

    return {
        "updated": updated,
        "failed": failed,
        "success_count": len(updated),
        "fail_count": len(failed),
        "results": results,
    }


@router.get("/stale")
def stale_symbols(
    secret: str = Query(None),
    conn: psycopg.Connection = Depends(get_db_connection),
):
    """List symbols that need refreshing."""
    if secret != REFRESH_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    today = datetime.now().date()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT s.symbol
            FROM stocks s
            LEFT JOIN LATERAL (
                SELECT MAX(date) AS max_date FROM stock_prices sp WHERE sp.stock_id = s.id
            ) m ON TRUE
            WHERE COALESCE(m.max_date, '1970-01-01') < %s
            ORDER BY s.symbol LIMIT 500
        """, (today,))
        return [r[0] for r in cur.fetchall()]


@router.get("/refresh-status")
def refresh_status(
    secret: str = Query(None),
    conn: psycopg.Connection = Depends(get_db_connection),
):
    """Monitor refresh health."""
    if secret != REFRESH_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(DISTINCT s.symbol) FROM stocks s
            JOIN stock_prices sp ON sp.stock_id = s.id WHERE sp.date = %s
        """, (today,))
        fresh_count = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(DISTINCT s.symbol) FROM stocks s
            JOIN stock_prices sp ON sp.stock_id = s.id WHERE sp.date = %s
        """, (yesterday,))
        yesterday_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM stocks")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT s.symbol, MAX(sp.date) as latest FROM stocks s
            JOIN stock_prices sp ON sp.stock_id = s.id
            GROUP BY s.symbol ORDER BY latest DESC LIMIT 10
        """)
        recent = [{"symbol": r[0], "latest": str(r[1])} for r in cur.fetchall()]

    return {
        "date": str(today),
        "fresh_today": fresh_count,
        "fresh_yesterday": yesterday_count,
        "total_stocks": total,
        "freshness_percent": round((fresh_count / total * 100) if total > 0 else 0, 2),
        "recent_updates": recent,
    }
