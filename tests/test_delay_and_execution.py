from datetime import datetime, timedelta, timezone
from unittest import mock

import pandas as pd

from core.models import Signal, TokenMeta
from engine.execution import ExecutionContext, ExecutionEngine, RiskGuards


def make_engine(token_meta: TokenMeta | None = None) -> ExecutionEngine:
    guards = RiskGuards(
        max_slip_bps=500,
        max_order_notional_usd=500,
        max_daily_notional_usd=1000,
        reject_honeypot=False,
        require_lp_lock_days_min=0,
        reject_tax_above_bps=2000,
    )
    context = ExecutionContext(
        delay_seconds_min=5,
        delay_seconds_max=10,
        trailing_arm_pct=0.8,
        trailing_pct=0.2,
        stop_loss_pct=0.25,
    )
    token_meta_map = {token_meta.token_address: token_meta} if token_meta else {}
    return ExecutionEngine(guards=guards, token_meta=token_meta_map, context=context)


def test_delay_bounds():
    engine = make_engine()
    signal = Signal("gmgn", "token", datetime.now(timezone.utc), 1.0, {"action": "buy"})
    pool_row = pd.Series({
        "reserve0": 100000.0,
        "reserve1": 100000.0,
        "fee_bps": 30,
        "price": 1.0,
    })
    with mock.patch("random.uniform", return_value=7):
        order = engine.submit_order(signal, pool_row, side="buy")
    assert order.ts_fill - order.ts_submit == timedelta(seconds=7)
    assert order.status == "filled"


def test_slippage_rejection():
    engine = make_engine()
    signal = Signal("gmgn", "token", datetime.now(timezone.utc), 1.0, {"action": "buy"})
    pool_row = pd.Series({
        "reserve0": 10.0,
        "reserve1": 10.0,
        "fee_bps": 30,
        "price": 1.0,
    })
    order = engine.submit_order(signal, pool_row, side="buy")
    assert order.status == "rejected"
    assert order.reason == "slippage"


def test_tax_applied():
    meta = TokenMeta(
        token_address="token",
        deployer=None,
        created_at=None,
        buy_tax_bps=200,
        sell_tax_bps=0,
        honeypot_flag=False,
        lp_locked_flag=True,
    )
    engine = make_engine(meta)
    signal = Signal("gmgn", "token", datetime.now(timezone.utc), 1.0, {"action": "buy"})
    pool_row = pd.Series({
        "reserve0": 100000.0,
        "reserve1": 100000.0,
        "fee_bps": 30,
        "price": 1.0,
    })
    with mock.patch("random.uniform", return_value=6):
        order = engine.submit_order(signal, pool_row, side="buy")
    assert order.quantity < engine.context.base_order_usd
