"""Dexscreener adapter for price/liq validation snapshots."""
from __future__ import annotations

import logging
import os
from typing import Iterable

import pandas as pd
import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)
load_dotenv()


@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def _get(url: str) -> requests.Response:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response


def fetch_pairs_snapshot(tokens: Iterable[str]) -> pd.DataFrame:
    """Fetch a lightweight snapshot for provided tokens."""
    base_url = os.getenv("DEXSCREENER_BASE", "https://api.dexscreener.com/latest/dex")
    joined = ",".join(tokens)
    url = f"{base_url}/tokens/{joined}"
    try:
        response = _get(url)
    except Exception as exc:  # pragma: no cover - network failure path
        logger.warning("Dexscreener unavailable: %s", exc)
        return pd.DataFrame(columns=["token_address", "price", "liquidity_usd", "updated_at"])

    data = response.json()
    pairs = data.get("pairs", [])
    if not pairs:
        return pd.DataFrame(columns=["token_address", "price", "liquidity_usd", "updated_at"])

    df = pd.DataFrame(pairs)
    df.rename(columns={"fdv": "liquidity_usd", "pairAddress": "pool_address"}, inplace=True)
    df["updatedAt"] = pd.to_datetime(df["updatedAt"], unit="ms", utc=True)
    df["price"] = df.get("priceUsd", 0).astype(float)
    df["liquidity_usd"] = df["liquidity"].apply(
        lambda liq: liq.get("usd", 0.0) if isinstance(liq, dict) else float(liq or 0.0)
    )
    df["token_address"] = df["baseToken"].apply(lambda token: token.get("address"))
    return df[["token_address", "pool_address", "price", "liquidity_usd", "updatedAt"]].rename(
        columns={"updatedAt": "updated_at"}
    )
