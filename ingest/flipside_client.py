"""Flipside Crypto data adapter for swap history."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

import pandas as pd
import requests
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class FlipsideQuery(BaseModel):
    """Encapsulates the payload sent to Flipside's ShroomDK endpoint."""

    sql: str


def _build_query(start_ts: str, end_ts: str, base_or_quote: str) -> str:
    """Return SQL for swaps filtered by quote token."""
    return f"""
    SELECT
        block_timestamp as ts,
        tx_hash,
        event_index,
        token_in AS token_in,
        token_out AS token_out,
        amount_in,
        amount_out,
        amount_usd,
        trader,
        pool_address
    FROM {base_or_quote}
    WHERE block_timestamp BETWEEN '{start_ts}' AND '{end_ts}'
    ORDER BY block_timestamp
    """


@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def _execute_query(payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """Hit ShroomDK with sane retries. Raises on non-200 responses."""
    headers = {"x-api-key": api_key}
    response = requests.post(
        "https://node-api.flipsidecrypto.com/queries",
        json=payload,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_swaps(start_ts: str, end_ts: str, base_or_quote: str) -> pd.DataFrame:
    """Fetch swaps and map the payload into the canonical Swap schema."""
    api_key = os.getenv("SHROOMDK_KEY")
    if not api_key:
        raise RuntimeError("SHROOMDK_KEY must be configured in the environment.")

    sql = _build_query(start_ts=start_ts, end_ts=end_ts, base_or_quote=base_or_quote)
    payload = FlipsideQuery(sql=sql).dict()
    logger.debug("Querying Flipside: %s", sql)
    data = _execute_query(payload, api_key=api_key)
    rows = data.get("records", [])
    if not rows:
        return pd.DataFrame(columns=[
            "token_address",
            "pool_address",
            "ts",
            "block_number",
            "side",
            "price",
            "amount_in",
            "amount_out",
            "tx_hash",
            "wallet",
        ])

    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df.rename(
        columns={
            "token_out": "token_address",
            "pool_address": "pool_address",
            "trader": "wallet",
        },
        inplace=True,
    )
    df["amount_usd"] = df.get("amount_usd", 0).astype(float)
    df["amount_out"] = df["amount_out"].astype(float)
    df["price"] = df.apply(
        lambda row: row["amount_usd"] / row["amount_out"] if row["amount_out"] else 0.0,
        axis=1,
    )
    df["side"] = df.apply(lambda row: "buy" if row["token_in"] == base_or_quote else "sell", axis=1)
    df["block_number"] = df.get("block_number", 0)
    df["price"] = df["price"].astype(float).clip(lower=1e-9)
    # Flipside returns rows in event order; we floor to five-second buckets later to maintain fidelity.
    return df[[
        "token_address",
        "pool_address",
        "ts",
        "block_number",
        "side",
        "price",
        "amount_in",
        "amount_out",
        "tx_hash",
        "wallet",
    ]]
