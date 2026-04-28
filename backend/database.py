"""
Database Connection Pool
=========================
Shared PostgreSQL connection pool used by all routers.
"""

import os
import logging
from psycopg_pool import ConnectionPool

log = logging.getLogger(__name__)

pool = None


def _normalize_dsn(dsn: str) -> str:
    """Add sslmode=require for Supabase connections."""
    if ("supabase.co" in dsn or "supabase.com" in dsn) and "sslmode=" not in dsn:
        return f"{dsn}{'?' if '?' not in dsn else '&'}sslmode=require"
    return dsn


def get_pool():
    """Get or create the database connection pool."""
    global pool
    if pool is None:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise RuntimeError("DATABASE_URL missing.")
        dsn = _normalize_dsn(dsn)
        pool = ConnectionPool(
            conninfo=dsn,
            min_size=1,
            max_size=10,
            kwargs={"prepare_threshold": None},
        )
        log.info("Database connection pool created")
    return pool


def get_db_connection():
    """FastAPI dependency: yield a database connection from the pool."""
    db_pool = get_pool()
    with db_pool.connection() as conn:
        yield conn
