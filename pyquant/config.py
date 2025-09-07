"""Configuration helpers for notebooks.

Loads environment variables from ``.env`` using :mod:`dotenv` and exposes a
simple :class:`types.SimpleNamespace` with runtime settings.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

from dotenv import load_dotenv

load_dotenv()

HAS_X = bool(os.getenv("X_BEARER_TOKEN"))
HAS_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
MYSQL_URI = os.getenv("MYSQL_URI")
DB_URL = MYSQL_URI if MYSQL_URI else "sqlite+pysqlite:///:memory:"
YF_TZ = os.getenv("YF_TZ", "America/New_York")

settings = SimpleNamespace(
    HAS_X=HAS_X,
    HAS_OPENAI=HAS_OPENAI,
    DB_URL=DB_URL,
    YF_TZ=YF_TZ,
)

__all__ = ["settings"]
