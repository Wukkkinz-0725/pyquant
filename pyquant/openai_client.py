from __future__ import annotations

from typing import Any, List, Dict

from .config import get_settings
from . import analyze as local_analyze


def _mock_analysis(tweets: List[dict]) -> List[dict]:
    out: list[dict] = []
    for t in tweets:
        text = t.get("text", "")
        coins = local_analyze.extract_coins(text) or ["BTC"]
        lowered = text.lower()
        stance = "neutral"
        if any(w in lowered for w in ["bull", "buy", "moon", "pump"]):
            stance = "bull"
        elif any(w in lowered for w in ["bear", "sell", "dump"]):
            stance = "bear"
        rationale = "Mock analysis based on keywords and coins in text."
        out.append(
            {
                "tweet_id": str(t.get("tweet_id")),
                "coins": coins,
                "stance": stance,
                "rationale": rationale,
                "confidence": 0.7,
                "model": "mock-v1",
            }
        )
    return out


def analyze_tweets(tweets: List[dict]) -> List[dict]:
    """Analyze tweets' sentiment and extract coins.

    Returns a list of dicts with keys: tweet_id, coins (list[str]), stance,
    rationale, confidence [0,1], model.
    """
    settings = get_settings()
    if not settings.HAS_OPENAI:
        return _mock_analysis(tweets)

    # Minimal OpenAI call per tweet to keep it robust and simple
    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        # If the client import fails, fall back to mock
        return _mock_analysis(tweets)

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    results: list[dict] = []
    system = (
        "You analyze crypto tweets. Extract coins (tickers) and sentiment as"
        " 'bull'|'bear'|'neutral'. Respond strictly as compact JSON with keys:"
        " coins (array of strings), stance, rationale (short), confidence (0..1)."
    )

    for t in tweets:
        text = t.get("text", "")
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": text},
                ],
                temperature=0.2,
                max_tokens=150,
            )
            content = (resp.choices[0].message.content or "{}").strip()
        except Exception:
            # On errors, degrade gracefully to mock for this tweet
            results.extend(_mock_analysis([t]))
            continue

        # Best-effort parse; if not valid JSON, revert to mock for this item
        import json

        try:
            obj = json.loads(content)
            coins = obj.get("coins") or local_analyze.extract_coins(text) or ["BTC"]
            stance = obj.get("stance", "neutral")
            rationale = obj.get("rationale", "OpenAI analysis")
            confidence = float(obj.get("confidence", 0.6))
            results.append(
                {
                    "tweet_id": str(t.get("tweet_id")),
                    "coins": [str(c).upper() for c in coins],
                    "stance": str(stance).lower(),
                    "rationale": str(rationale),
                    "confidence": confidence,
                    "model": getattr(resp, "model", "openai"),
                }
            )
        except Exception:
            results.extend(_mock_analysis([t]))

    return results

