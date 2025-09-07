"""Database helpers using SQLAlchemy Core."""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_engine(db_url: str) -> Engine:
    """Return a SQLAlchemy engine for *db_url*."""
    return create_engine(db_url, future=True)


def create_tables(engine: Engine) -> None:
    """Create minimal tables if they do not already exist."""
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_handle TEXT,
            tweet_id TEXT UNIQUE,
            text TEXT,
            created_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS tweet_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id TEXT,
            coin_symbol TEXT,
            stance TEXT,
            rationale TEXT,
            confidence REAL,
            model TEXT,
            created_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS price_window (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coin_symbol TEXT,
            t0 TEXT,
            t1 TEXT,
            max_price REAL,
            min_price REAL,
            vol REAL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id TEXT,
            coin_symbol TEXT,
            signal_score REAL,
            horizon_days INTEGER,
            comment TEXT,
            created_at TEXT
        )
        """,
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))


__all__ = ["get_engine", "create_tables"]
