"""Simple price utilities."""

from __future__ import annotations


def momentum(t0_price: float, max_price: float, min_price: float) -> float:
    """Very rough momentum proxy based on extremes around *t0_price*."""
    up = (max_price - t0_price) / t0_price
    down = (t0_price - min_price) / t0_price
    return up - down


__all__ = ["momentum"]
