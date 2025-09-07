from __future__ import annotations

import os
from types import SimpleNamespace

from dotenv import load_dotenv


def _truthy(value: str | None) -> bool:
    return bool(value and value.strip())


def get_settings() -> SimpleNamespace:
    """Load environment and expose simple settings.

    Picks DB URL: `MYSQL_URI` if set, else in-memory SQLite.
    Detects availability of X and OpenAI keys for mock/live behavior.
    """
    # Don't override already-set environment variables
    load_dotenv(override=False)

    openai_key = os.getenv("OPENAI_API_KEY", "")
    x_token = os.getenv("X_BEARER_TOKEN", "")
    mysql_uri = (os.getenv("MYSQL_URI", "") or "").strip()
    yf_tz = os.getenv("YF_TZ", "America/New_York")

    has_x = _truthy(x_token)
    has_openai = _truthy(openai_key)
    db_url = mysql_uri if _truthy(mysql_uri) else "sqlite+pysqlite:///:memory:"

    return SimpleNamespace(
        OPENAI_API_KEY=openai_key,
        X_BEARER_TOKEN=x_token,
        MYSQL_URI=mysql_uri,
        DB_URL=db_url,
        YF_TZ=yf_tz,
        HAS_X=has_x,
        HAS_OPENAI=has_openai,
    )

