"""Automated market maker math utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

Direction = Literal["buy", "sell"]


@dataclass(frozen=True)
class TradeResult:
    """Container describing the outcome of a simulated trade."""

    price: float
    new_reserve_in: float
    new_reserve_out: float
    slip_bps: float


def cpmm_price_after_trade(
    reserve_in: float,
    reserve_out: float,
    amount_in: float,
    fee_bps: int,
    direction: Direction = "buy",
) -> TradeResult:
    """Return the execution price and updated reserves for a constant-product pool."""
    if reserve_in <= 0 or reserve_out <= 0:
        raise ValueError("Reserves must be positive for CPMM pricing")
    fee = amount_in * fee_bps / 10_000
    effective_in = amount_in - fee
    if effective_in <= 0:
        raise ValueError("Effective amount in must be positive after fees")

    k = reserve_in * reserve_out
    if direction == "buy":
        new_reserve_in = reserve_in + effective_in
        new_reserve_out = k / new_reserve_in
        amount_out = reserve_out - new_reserve_out
    else:
        new_reserve_out = reserve_out + effective_in
        new_reserve_in = k / new_reserve_out
        amount_out = reserve_in - new_reserve_in

    price = amount_in / max(amount_out, 1e-12)
    pre_price = reserve_in / reserve_out
    slip = (price / pre_price - 1.0) * 10_000
    return TradeResult(price=price, new_reserve_in=new_reserve_in, new_reserve_out=new_reserve_out, slip_bps=slip)


def v3_single_band_price(
    reserve_in: float,
    reserve_out: float,
    amount_in: float,
    fee_bps: int,
    lower_price: float,
    upper_price: float,
) -> TradeResult:
    """Approximate concentrated liquidity with a single active band."""
    if lower_price <= 0 or upper_price <= lower_price:
        raise ValueError("Invalid band bounds")
    mid_price = np.clip(reserve_in / reserve_out, lower_price, upper_price)
    adjusted_reserve_in = reserve_in * (mid_price / (reserve_in / reserve_out))
    return cpmm_price_after_trade(adjusted_reserve_in, reserve_out, amount_in, fee_bps)
