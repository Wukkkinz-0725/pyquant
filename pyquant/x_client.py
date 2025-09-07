from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from .config import get_settings


def _iso8601(dt: str | datetime | None) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, str):
        s = dt.strip()
        return s
    return dt.replace(microsecond=0).isoformat() + "Z"


def get_tweets(handles: list[str], since: str | None = None, until: str | None = None, max_results: int = 10) -> list[dict[str, Any]]:
    """Return recent tweets for given handles.

    - If no X token is present, returns a small deterministic mock list.
    - If a token exists, performs a minimal call to Twitter v2 recent search.
      This is intentionally simple: no pagination, minimal fields.
    """
    settings = get_settings()
    if not settings.HAS_X:
        # Deterministic mock data: 3 tweets, two coins mentioned
        now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        return [
            {
                "user_handle": handles[0] if handles else "alice",
                "tweet_id": "t_mock_1",
                "text": "I think BTC looks strong this week. #crypto",
                "created_at": now,
            },
            {
                "user_handle": handles[1] if len(handles) > 1 else "bob",
                "tweet_id": "t_mock_2",
                "text": "ETH may pull back, but long term bullish.",
                "created_at": now,
            },
            {
                "user_handle": handles[0] if handles else "alice",
                "tweet_id": "t_mock_3",
                "text": "Watching SOL volatility; staying neutral for now.",
                "created_at": now,
            },
        ]

    # Live (best-effort minimal) implementation
    token = settings.X_BEARER_TOKEN
    headers = {"Authorization": f"Bearer {token}"}
    since_iso = _iso8601(since)
    until_iso = _iso8601(until)
    tweets: list[dict[str, Any]] = []

    with httpx.Client(timeout=10.0, headers=headers) as client:
        for h in handles:
            params = {
                "query": f"from:{h}",
                "max_results": str(min(max_results, 100)),
                "tweet.fields": "created_at",
            }
            if since_iso:
                params["start_time"] = since_iso
            if until_iso:
                params["end_time"] = until_iso

            # Twitter v2 recent search endpoint
            url = "https://api.twitter.com/2/tweets/search/recent"
            try:
                r = client.get(url, params=params)
                r.raise_for_status()
                data = r.json().get("data", [])
                for item in data:
                    tweets.append(
                        {
                            "user_handle": h,
                            "tweet_id": str(item.get("id")),
                            "text": item.get("text", ""),
                            "created_at": item.get("created_at"),
                        }
                    )
            except Exception:
                # Best-effort: if a call fails for a handle, continue
                continue

    return tweets

