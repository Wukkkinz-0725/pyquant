"""Execution layer modelling latency, taxes, and guardrails."""
from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Iterable, Optional

import pandas as pd

from core.models import Order, Position, Signal, TokenMeta
from engine.amm import TradeResult, cpmm_price_after_trade

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskGuards:
    """Global guardrails applied to every simulated order."""

    max_slip_bps: int
    max_order_notional_usd: float
    max_daily_notional_usd: float
    reject_honeypot: bool
    require_lp_lock_days_min: int
    reject_tax_above_bps: int


@dataclass
class ExecutionContext:
    """Per-strategy execution configuration."""

    delay_seconds_min: int
    delay_seconds_max: int
    trailing_arm_pct: float
    trailing_pct: float
    stop_loss_pct: float
    follow_sell: bool = False
    base_order_usd: float = 100.0


@dataclass
class ExecutionState:
    """Mutable state tracking positions and usage limits."""

    daily_notional: Dict[str, float] = field(default_factory=dict)
    positions: Dict[str, Position] = field(default_factory=dict)
    orders: list[Order] = field(default_factory=list)


class ExecutionEngine:
    """Handles signal-to-order conversion with guardrail enforcement."""

    def __init__(
        self,
        guards: RiskGuards,
        token_meta: Dict[str, TokenMeta],
        context: ExecutionContext,
    ) -> None:
        self.guards = guards
        self.token_meta = token_meta
        self.context = context
        self.state = ExecutionState()

    def _sample_delay(self) -> timedelta:
        return timedelta(
            seconds=random.uniform(self.context.delay_seconds_min, self.context.delay_seconds_max)
        )

    def _tax_bps(self, token: str, side: str) -> int:
        meta = self.token_meta.get(token)
        if not meta:
            return 0
        if side == "buy":
            return meta.buy_tax_bps or 0
        return meta.sell_tax_bps or 0

    def _validate_meta(self, token: str) -> Optional[str]:
        meta = self.token_meta.get(token)
        if not meta:
            return None
        if self.guards.reject_honeypot and meta.honeypot_flag:
            return "honeypot"
        if self.guards.reject_tax_above_bps:
            buy_tax = meta.buy_tax_bps or 0
            sell_tax = meta.sell_tax_bps or 0
            if buy_tax > self.guards.reject_tax_above_bps or sell_tax > self.guards.reject_tax_above_bps:
                return "excessive_tax"
        if self.guards.require_lp_lock_days_min and not meta.lp_locked_flag:
            return "lp_unlocked"
        return None

    def _check_notional(self, ts: datetime, notional: float) -> Optional[str]:
        date_key = ts.date().isoformat()
        used = self.state.daily_notional.get(date_key, 0.0)
        if notional > self.guards.max_order_notional_usd:
            return "order_notional"
        if used + notional > self.guards.max_daily_notional_usd:
            return "daily_notional"
        self.state.daily_notional[date_key] = used + notional
        return None

    def submit_order(
        self,
        signal: Signal,
        pool_row: pd.Series,
        side: str,
    ) -> Order:
        """Simulate order submission, applying delay and execution model."""
        ts_submit = signal.ts
        delay = self._sample_delay()
        ts_fill = ts_submit + delay
        reserve_in = float(pool_row["reserve0"])
        reserve_out = float(pool_row["reserve1"])
        fee_bps = int(pool_row.get("fee_bps", 300))
        trade_size = self.context.base_order_usd / max(float(pool_row.get("price", 1.0)), 1e-6)
        trade_result = cpmm_price_after_trade(
            reserve_in=reserve_in,
            reserve_out=reserve_out,
            amount_in=trade_size,
            fee_bps=fee_bps,
            direction=side,
        )
        if abs(trade_result.slip_bps) > self.guards.max_slip_bps:
            return Order(
                sim_id="sim",
                ts_submit=ts_submit,
                ts_fill=None,
                token_address=signal.token_address,
                side=side,
                quantity=trade_size,
                price_fill=None,
                gas_used=None,
                slip_bps=trade_result.slip_bps,
                status="rejected",
                reason="slippage",
            )
        notional = trade_result.price * trade_size
        rejection_reason = self._validate_meta(signal.token_address)
        if rejection_reason:
            return Order(
                sim_id="sim",
                ts_submit=ts_submit,
                ts_fill=None,
                token_address=signal.token_address,
                side=side,
                quantity=trade_size,
                price_fill=None,
                gas_used=None,
                slip_bps=trade_result.slip_bps,
                status="rejected",
                reason=rejection_reason,
            )
        notional_reason = self._check_notional(ts_submit, notional)
        if notional_reason:
            return Order(
                sim_id="sim",
                ts_submit=ts_submit,
                ts_fill=None,
                token_address=signal.token_address,
                side=side,
                quantity=trade_size,
                price_fill=None,
                gas_used=None,
                slip_bps=trade_result.slip_bps,
                status="rejected",
                reason=notional_reason,
            )

        tax_bps = self._tax_bps(signal.token_address, side)
        tax_multiplier = 1.0 - tax_bps / 10_000
        filled_quantity = trade_size * tax_multiplier if side == "buy" else trade_size
        proceeds = trade_result.price * trade_size * (tax_multiplier if side == "sell" else 1.0)
        gas_cost = 0.001
        order = Order(
            sim_id="sim",
            ts_submit=ts_submit,
            ts_fill=ts_fill,
            token_address=signal.token_address,
            side=side,
            quantity=filled_quantity,
            price_fill=trade_result.price,
            gas_used=gas_cost,
            slip_bps=trade_result.slip_bps,
            status="filled",
            reason=None,
        )
        position = self.state.positions.get(signal.token_address)
        if side == "buy":
            self.state.positions[signal.token_address] = Position(
                sim_id="sim",
                token_address=signal.token_address,
                quantity=filled_quantity,
                cost_basis=trade_result.price,
                pnl=0.0,
                mtm=0.0,
                ts=ts_fill,
            )
        elif position:
            pnl = (trade_result.price - position.cost_basis) * position.quantity
            pnl -= gas_cost
            self.state.positions.pop(signal.token_address, None)
            self.state.orders.append(order)
            return order
        self.state.orders.append(order)
        return order

    def evaluate_positions(
        self,
        price_frame: pd.DataFrame,
    ) -> None:
        """Update mark-to-market for open positions based on pool states."""
        for token, position in list(self.state.positions.items()):
            token_df = price_frame[price_frame["token_address"] == token]
            if token_df.empty:
                continue
            latest = token_df.iloc[-1]
            mark = float(latest.get("price", latest.get("reserve0", 0)))
            pnl = (mark - position.cost_basis) * position.quantity
            self.state.positions[token] = position.copy(update={"mtm": pnl, "pnl": pnl})

    def close_all(self, price_frame: pd.DataFrame) -> list[Order]:
        """Force liquidate remaining positions at latest price."""
        closing_orders: list[Order] = []
        for token, position in list(self.state.positions.items()):
            token_df = price_frame[price_frame["token_address"] == token]
            if token_df.empty:
                continue
            latest = token_df.iloc[-1]
            price = float(latest.get("price", 0.0))
            order = Order(
                sim_id="sim",
                ts_submit=latest["ts"],
                ts_fill=latest["ts"],
                token_address=token,
                side="sell",
                quantity=position.quantity,
                price_fill=price,
                gas_used=0.001,
                slip_bps=0.0,
                status="filled",
                reason="forced_exit",
            )
            closing_orders.append(order)
            self.state.orders.append(order)
            self.state.positions.pop(token, None)
        return closing_orders
