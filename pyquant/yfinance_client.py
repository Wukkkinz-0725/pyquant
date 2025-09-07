from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf


def get_price_window(symbol: str, t0: datetime, horizon_days: int = 7) -> Optional[dict]:
    """Fetch a simple price window and compute basic stats.

    Returns dict with: max_price, min_price, vol (stdev of daily returns).
    If data is empty, returns None.
    """
    t1 = t0 + timedelta(days=int(horizon_days))
    try:
        df = yf.download(symbol, start=t0, end=t1, progress=False, auto_adjust=True)
    except Exception:
        return None

    if df is None or df.empty:
        return None

    # Use Close; compute simple stats
    prices = df["Close"].dropna()
    if prices.empty:
        return None

    max_p = float(prices.max())
    min_p = float(prices.min())
    # daily returns stdev as vol proxy
    returns = prices.pct_change().dropna()
    vol = float(returns.std()) if not returns.empty else 0.0

    return {
        "max_price": max_p,
        "min_price": min_p,
        "vol": vol,
        "t1": t1,
    }

