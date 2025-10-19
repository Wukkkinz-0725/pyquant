"""GMGN-inspired threshold strategy."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd

from core.models import Signal


@dataclass
class GMGNConfig:
    liq_usd_min: float
    net_buy_5m_min: float
    max_buy_tax_bps: int
    max_sell_tax_bps: int
    trailing_arm_pct: float
    trailing_pct: float
    stop_loss_pct: float
    delay_seconds_min: int
    delay_seconds_max: int


class GMGNThresholdStrategy:
    """Detects high conviction buying shortly after pool creation."""

    def __init__(self, config: GMGNConfig) -> None:
        self.config = config

    def generate_signals(self, swaps: pd.DataFrame, pools: pd.DataFrame, token_meta: pd.DataFrame) -> List[Signal]:
        if swaps.empty:
            return []
        recent_cutoff = swaps["ts"].max() - timedelta(minutes=5)
        recent = swaps[swaps["ts"] >= recent_cutoff]
        signals: List[Signal] = []

        tax_map = token_meta.set_index("token_address") if not token_meta.empty else pd.DataFrame()
        liquidity = pools.groupby("token_address")["reserve1"].last() * pools.groupby("token_address")["price"].last()

        grouped = recent.groupby("token_address")
        for token, group in grouped:
            net_buys = (group["side"] == "buy").sum() - (group["side"] == "sell").sum()
            if net_buys < self.config.net_buy_5m_min:
                continue
            liq = float(liquidity.get(token, 0.0))
            if liq < self.config.liq_usd_min:
                continue
            if not tax_map.empty and token in tax_map.index:
                meta_row = tax_map.loc[token]
                if meta_row.get("buy_tax_bps", 0) > self.config.max_buy_tax_bps:
                    continue
                if meta_row.get("sell_tax_bps", 0) > self.config.max_sell_tax_bps:
                    continue
            first_seen = swaps[swaps["token_address"] == token]["ts"].min()
            age_minutes = (recent_cutoff - first_seen).total_seconds() / 60 if first_seen else 0
            meta = {
                "action": "buy",
                "net_buys": float(net_buys),
                "liq_usd": liq,
                "age_minutes": age_minutes,
            }
            signals.append(
                Signal(
                    strategy="gmgn_threshold",
                    token_address=token,
                    ts=group["ts"].max(),
                    score=float(net_buys),
                    meta=meta,
                )
            )
        return signals
