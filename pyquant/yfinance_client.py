"""Yahoo Finance helper."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf


def get_price_window(symbol: str, t0: datetime, horizon_days: int) -> Optional[dict]:
    """Return price stats for *symbol* between *t0* and *t0 + horizon_days*."""
    t1 = t0 + timedelta(days=horizon_days)
    df = yf.download(symbol, start=t0, end=t1, progress=False)
    if df.empty:
        return None
    max_price = float(df["Close"].max())
    min_price = float(df["Close"].min())
    vol = float(df["Close"].pct_change().std())
    t0_price = float(df["Close"].iloc[0])
    return {
        "t0": t0,
        "t1": t1,
        "t0_price": t0_price,
        "max_price": max_price,
        "min_price": min_price,
        "vol": vol,
    }


__all__ = ["get_price_window"]
