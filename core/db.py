"""Database helpers for SQLite-backed simulations."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.models import Base

load_dotenv()

_DB_PATH = Path(os.getenv("BSC_MEME_DB", "data/bsc_meme.db"))


def get_engine(echo: bool = False) -> Engine:
    """Return the SQLAlchemy engine, creating directories as needed."""
    if not _DB_PATH.parent.exists():
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite+pysqlite:///{_DB_PATH}"
    return create_engine(url, echo=echo, future=True)


def create_all_tables(engine: Engine) -> None:
    """Create all tables defined in :mod:`core.models`."""
    Base.metadata.create_all(engine)


_SESSION_FACTORY = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope for DB operations."""
    session = _SESSION_FACTORY()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
