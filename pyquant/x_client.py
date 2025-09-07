"""Minimal Twitter/X client with mock fallback."""

from __future__ import annotations

from typing import List, Optional
import os

import httpx

from .config import settings


MOCK_TWEETS = [
    {
        "user_handle": "alice",
        "tweet_id": "1",
        "text": "BTC to the moon!",
        "created_at": "2024-01-01T00:00:00Z",
    },
    {
        "user_handle": "bob",
        "tweet_id": "2",
        "text": "ETH is lagging today",
        "created_at": "2024-01-02T00:00:00Z",
    },
]


def get_tweets(handles: List[str], since: Optional[str] = None, until: Optional[str] = None) -> List[dict]:
    """Fetch recent tweets for *handles*.

    If :data:`settings.HAS_X` is ``False`` a deterministic mock list is
    returned.  The real implementation uses the Twitter v2 recent search API and
    purposely keeps error handling minimal.
    """

    if not settings.HAS_X:
        return MOCK_TWEETS

    token = os.environ["X_BEARER_TOKEN"]
    headers = {"Authorization": f"Bearer {token}"}
    query = " OR ".join(f"from:{h}" for h in handles)
    params = {
        "query": query,
        "max_results": 10,
        "tweet.fields": "created_at",
    }
    if since:
        params["start_time"] = since
    if until:
        params["end_time"] = until
    url = "https://api.twitter.com/2/tweets/search/recent"
    resp = httpx.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    tweets = []
    for t in data:
        tweets.append(
            {
                "user_handle": t.get("author_id", ""),  # TODO: resolve handle
                "tweet_id": t.get("id"),
                "text": t.get("text"),
                "created_at": t.get("created_at"),
            }
        )
    return tweets


__all__ = ["get_tweets"]
