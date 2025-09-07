"""OpenAI sentiment extraction with mock mode."""

from __future__ import annotations

from typing import List
import json
import os

import openai

from .config import settings
from . import analyze


MOCK_RESPONSE = {
    "coins": ["BTC"],
    "stance": "bull",
    "rationale": "BTC mentioned positively in tweet",
    "confidence": 0.7,
    "model": "mock",
}


def analyze_tweets(tweets: List[dict]) -> List[dict]:
    """Return sentiment analysis for *tweets*.

    Each result dict contains ``tweet_id``, ``coins`` (a list of symbols),
    ``stance``, ``rationale``, ``confidence`` and ``model``.
    """

    if not settings.HAS_OPENAI:
        results = []
        for t in tweets:
            coins = analyze.extract_coins(t.get("text", "")) or MOCK_RESPONSE["coins"]
            r = MOCK_RESPONSE.copy()
            r.update({"tweet_id": t["tweet_id"], "coins": coins})
            results.append(r)
        return results

    openai.api_key = os.environ["OPENAI_API_KEY"]
    out = []
    for t in tweets:
        prompt = (
            "Extract mentioned crypto tickers and sentiment (bull/bear/neutral)\n"
            f"Tweet: {t['text']}\n"
            "Respond as JSON with keys coins (list), stance, rationale, confidence"
        )
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = resp.choices[0].message["content"]
        data = json.loads(content)
        data["tweet_id"] = t["tweet_id"]
        data["model"] = resp.model
        out.append(data)
    return out


__all__ = ["analyze_tweets"]
