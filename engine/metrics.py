"""Performance metrics utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

import numpy as np
import pandas as pd

from core.models import Order


@dataclass
class MetricResult:
    """Container storing common metrics for reporting."""

    total_return: float
    max_drawdown: float
    sharpe: float
    sortino: float
    win_rate: float
    cost_ratio: float


def equity_curve(orders: Iterable[Order]) -> pd.Series:
    """Compute equity curve from filled orders."""
    cash = []
    times = []
    for order in orders:
        if order.status != "filled":
            continue
        flow = (order.price_fill or 0) * order.quantity
        if order.side == "buy":
            flow *= -1
        cash.append(flow)
        times.append(order.ts_fill or order.ts_submit)
    if not cash:
        return pd.Series(dtype=float)
    return pd.Series(cash, index=pd.to_datetime(times, utc=True)).cumsum()


def compute_metrics(orders: Iterable[Order]) -> Dict[str, float]:
    """Derive key performance metrics from order list."""
    filled = [order for order in orders if order.status == "filled"]
    if not filled:
        return {"total_return": 0.0, "max_dd": 0.0, "sharpe": 0.0, "win_rate": 0.0, "cost_ratio": 0.0}

    df = pd.DataFrame([
        {
            "side": order.side,
            "price": order.price_fill,
            "quantity": order.quantity,
            "ts": order.ts_fill,
            "gas": order.gas_used or 0,
        }
        for order in filled
    ])
    buys = df[df["side"] == "buy"]
    sells = df[df["side"] == "sell"]
    pnl = (sells["price"] * sells["quantity"]).sum() - (buys["price"] * buys["quantity"]).sum()
    costs = df["gas"].sum()
    if sells.empty or buys.empty:
        win_rate = 0.0
    else:
        avg_entry = (buys["price"] * buys["quantity"]).sum() / max(buys["quantity"].sum(), 1e-9)
        win_rate = float((sells["price"] > avg_entry).mean())
    equity = equity_curve(filled)
    max_dd = float((equity.cummax() - equity).max() or 0)
    returns = equity.diff().fillna(0)
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() else 0.0
    downside = returns[returns < 0]
    sortino = returns.mean() / (downside.std() * np.sqrt(len(returns))) if not downside.empty else 0.0
    cost_ratio = costs / max(pnl, 1e-9)
    return {
        "total_return": float(pnl),
        "max_dd": float(max_dd),
        "sharpe": float(sharpe),
        "win_rate": float(win_rate),
        "cost_ratio": float(cost_ratio),
        "sortino": float(sortino),
    }
