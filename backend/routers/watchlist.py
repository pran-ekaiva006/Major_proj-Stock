"""
Watchlist Router
=================
User watchlist management (requires authentication).
"""

import logging
import psycopg
from fastapi import APIRouter, HTTPException, Depends

from backend.database import get_db_connection
from backend.auth import get_current_user
from backend.models import WatchlistAdd

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])


def _get_user_id(username: str, conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return row[0]


@router.get("")
def get_watchlist(
    current_user: str = Depends(get_current_user),
    conn: psycopg.Connection = Depends(get_db_connection),
):
    """Get the current user's watchlist."""
    uid = _get_user_id(current_user, conn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT symbol, added_at FROM watchlists WHERE user_id = %s ORDER BY added_at DESC",
            (uid,),
        )
        rows = cur.fetchall()
    return [{"symbol": r[0], "added_at": r[1].isoformat() if r[1] else None} for r in rows]


@router.post("")
def add_to_watchlist(
    item: WatchlistAdd,
    current_user: str = Depends(get_current_user),
    conn: psycopg.Connection = Depends(get_db_connection),
):
    """Add a symbol to the user's watchlist."""
    uid = _get_user_id(current_user, conn)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO watchlists (user_id, symbol) VALUES (%s, %s) ON CONFLICT (user_id, symbol) DO NOTHING",
            (uid, item.symbol.upper()),
        )
    conn.commit()
    return {"message": f"{item.symbol.upper()} added to watchlist"}


@router.delete("/{symbol}")
def remove_from_watchlist(
    symbol: str,
    current_user: str = Depends(get_current_user),
    conn: psycopg.Connection = Depends(get_db_connection),
):
    """Remove a symbol from the user's watchlist."""
    uid = _get_user_id(current_user, conn)
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM watchlists WHERE user_id = %s AND symbol = %s",
            (uid, symbol.upper()),
        )
    conn.commit()
    return {"message": f"{symbol.upper()} removed from watchlist"}
