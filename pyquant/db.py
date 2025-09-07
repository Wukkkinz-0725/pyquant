from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection


def get_engine(db_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for the configured database."""
    from .config import get_settings

    settings = get_settings()
    url = db_url or settings.DB_URL
    return create_engine(url, future=True)


def _dialect_name(conn_or_engine: Engine | Connection) -> str:
    return conn_or_engine.dialect.name  # type: ignore[attr-defined]


def create_tables(engine: Engine) -> None:
    """Create minimal tables if they do not exist.

    Uses dialect-specific DDL for SQLite/MySQL.
    """
    d = engine.dialect.name
    if d == "mysql":
        stmts: list[str] = [
            """
            CREATE TABLE IF NOT EXISTS tweets (
              id INT AUTO_INCREMENT PRIMARY KEY,
              user_handle VARCHAR(64),
              tweet_id VARCHAR(64) UNIQUE,
              text TEXT,
              created_at DATETIME
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS tweet_analysis (
              id INT AUTO_INCREMENT PRIMARY KEY,
              tweet_id VARCHAR(64),
              coin_symbol VARCHAR(16),
              stance VARCHAR(16),
              rationale TEXT,
              confidence DOUBLE,
              model VARCHAR(64),
              created_at DATETIME
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS price_window (
              id INT AUTO_INCREMENT PRIMARY KEY,
              coin_symbol VARCHAR(16),
              t0 DATETIME,
              t1 DATETIME,
              max_price DOUBLE,
              min_price DOUBLE,
              vol DOUBLE
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS signals (
              id INT AUTO_INCREMENT PRIMARY KEY,
              tweet_id VARCHAR(64),
              coin_symbol VARCHAR(16),
              signal_score DOUBLE,
              horizon_days INT,
              comment TEXT,
              created_at DATETIME
            ) ENGINE=InnoDB
            """,
        ]
    else:  # sqlite and others
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
        for s in stmts:
            conn.exec_driver_sql(s)


def _insert_ignore_sql(table: str, cols: Iterable[str], dialect: str) -> str:
    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    if dialect == "mysql":
        return f"INSERT IGNORE INTO {table} ({col_list}) VALUES ({placeholders})"
    # sqlite and others
    return f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})"


def insert_ignore(conn: Connection, table: str, row: dict[str, Any]) -> None:
    d = _dialect_name(conn)
    cols = list(row.keys())
    sql = _insert_ignore_sql(table, cols, d)
    conn.execute(text(sql), row)


def insert_tweet(conn: Connection, *, user_handle: str, tweet_id: str, text_: str, created_at: datetime | str) -> None:
    row = {
        "user_handle": user_handle,
        "tweet_id": str(tweet_id),
        "text": text_,
        "created_at": created_at if isinstance(created_at, str) else created_at.isoformat(),
    }
    insert_ignore(conn, "tweets", row)


def insert_analysis(
    conn: Connection,
    *,
    tweet_id: str,
    coin_symbol: str,
    stance: str,
    rationale: str,
    confidence: float,
    model: str,
    created_at: datetime | str,
) -> None:
    row = {
        "tweet_id": str(tweet_id),
        "coin_symbol": coin_symbol,
        "stance": stance,
        "rationale": rationale,
        "confidence": float(confidence),
        "model": model,
        "created_at": created_at if isinstance(created_at, str) else created_at.isoformat(),
    }
    insert_ignore(conn, "tweet_analysis", row)


def insert_price_window(
    conn: Connection,
    *,
    coin_symbol: str,
    t0: datetime | str,
    t1: datetime | str,
    max_price: float,
    min_price: float,
    vol: float,
) -> None:
    row = {
        "coin_symbol": coin_symbol,
        "t0": t0 if isinstance(t0, str) else t0.isoformat(),
        "t1": t1 if isinstance(t1, str) else t1.isoformat(),
        "max_price": float(max_price),
        "min_price": float(min_price),
        "vol": float(vol),
    }
    insert_ignore(conn, "price_window", row)


def insert_signal(
    conn: Connection,
    *,
    tweet_id: str,
    coin_symbol: str,
    signal_score: float,
    horizon_days: int,
    comment: str,
    created_at: datetime | str,
) -> None:
    row = {
        "tweet_id": str(tweet_id),
        "coin_symbol": coin_symbol,
        "signal_score": float(signal_score),
        "horizon_days": int(horizon_days),
        "comment": comment,
        "created_at": created_at if isinstance(created_at, str) else created_at.isoformat(),
    }
    insert_ignore(conn, "signals", row)

