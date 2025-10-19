"""Whale wallet mirroring strategy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from core.models import Signal


@dataclass
class WhaleConfig:
    whitelist_wallets: list[str]
    delay_seconds_min: int
    delay_seconds_max: int
    follow_sell: bool
    trailing_arm_pct: float
    trailing_pct: float
    stop_loss_pct: float


class WhaleCopyStrategy:
    """Mirrors trades from a curated wallet list with latency bounds."""

    def __init__(self, config: WhaleConfig) -> None:
        self.config = config

    def generate_signals(self, swaps: pd.DataFrame, pools: pd.DataFrame, token_meta: pd.DataFrame) -> List[Signal]:
        if swaps.empty:
            return []
        wallets = set(self.config.whitelist_wallets)
        filtered = swaps[swaps["wallet"].isin(wallets)] if wallets else swaps
        signals: List[Signal] = []
        for _, row in filtered.iterrows():
            meta = {
                "action": row["side"],
                "wallet": row["wallet"],
                "tx_hash": row["tx_hash"],
            }
            signals.append(
                Signal(
                    strategy="whale_copy",
                    token_address=row["token_address"],
                    ts=row["ts"],
                    score=float(row.get("amount_in", 0)),
                    meta=meta,
                )
            )
        return signals
