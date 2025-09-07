from __future__ import annotations


def momentum(t0_price: float, max_price: float, min_price: float) -> float:
    """Simple momentum proxy.

    Example: (max - t0)/t0 - (t0 - min)/t0
    """
    if t0_price is None or t0_price == 0:
        return 0.0
    up = (max_price - t0_price) / t0_price
    down = (t0_price - min_price) / t0_price
    return float(up - down)

