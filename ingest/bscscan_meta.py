"""Token metadata enrichment via BscScan."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Iterable

import pandas as pd
import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)
load_dotenv()


@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def _call(endpoint: str, params: dict[str, str]) -> dict:
    response = requests.get(endpoint, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def _parse_tax(tax_str: str | None) -> int | None:
    if not tax_str:
        return None
    try:
        return int(float(tax_str) * 100)
    except ValueError:
        return None


def enrich_token_meta(tokens: Iterable[str]) -> pd.DataFrame:
    """Return token metadata for downstream risk checks."""
    api_key = os.getenv("BSCSCAN_API_KEY")
    if not api_key:
        raise RuntimeError("BSCSCAN_API_KEY must be set in the environment")

    endpoint = "https://api.bscscan.com/api"
    records: list[dict[str, object]] = []

    for token in tokens:
        params = {"module": "token", "action": "tokeninfo", "contractaddress": token, "apikey": api_key}
        try:
            payload = _call(endpoint, params)
        except Exception as exc:  # pragma: no cover
            logger.warning("BscScan metadata failure for %s: %s", token, exc)
            continue
        result = payload.get("result", [])
        if not result:
            continue
        info = result[0]
        created_at_raw = info.get("createdAt")
        created_at = None
        if created_at_raw and str(created_at_raw).isdigit():
            created_at = datetime.fromtimestamp(int(created_at_raw), tz=timezone.utc)
        records.append(
            {
                "token_address": token,
                "deployer": info.get("owner"),
                "created_at": created_at,
                "buy_tax_bps": _parse_tax(info.get("buyTax")),
                "sell_tax_bps": _parse_tax(info.get("sellTax")),
                "honeypot_flag": info.get("isHoneypot", "0") == "1",
                "lp_locked_flag": info.get("lpIsLocked", "0") == "1",
            }
        )

    if not records:
        return pd.DataFrame(columns=[
            "token_address",
            "deployer",
            "created_at",
            "buy_tax_bps",
            "sell_tax_bps",
            "honeypot_flag",
            "lp_locked_flag",
        ])

    df = pd.DataFrame(records)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    return df
