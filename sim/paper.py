"""Paper trading loop for five-second bars."""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from rich.console import Console

from core.models import Signal
from strategies.gmgn_threshold import GMGNConfig, GMGNThresholdStrategy
from strategies.whale_copy import WhaleConfig, WhaleCopyStrategy


class PaperTrader:
    """Consumes parquet bars to simulate live decision making."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console
        self.data_path = Path("data")

    def run(self, strategy_name: str) -> None:
        strategy = self._build_strategy(strategy_name)
        while True:
            swaps = self._load("swaps")
            pools = self._load("pool_states")
            if swaps.empty or pools.empty:
                if self.console:
                    self.console.log("No fresh data available; sleeping...")
                time.sleep(5)
                continue
            signals = strategy.generate_signals(swaps, pools, pd.DataFrame())
            if self.console:
                for signal in signals:
                    self.console.log(f"[{strategy_name}] {signal.token_address} score={signal.score}")
            time.sleep(5)

    def _build_strategy(self, name: str):
        if name == "gmgn_threshold":
            config = GMGNConfig(
                liq_usd_min=20000,
                net_buy_5m_min=10,
                max_buy_tax_bps=1200,
                max_sell_tax_bps=1200,
                trailing_arm_pct=0.8,
                trailing_pct=0.2,
                stop_loss_pct=0.25,
                delay_seconds_min=5,
                delay_seconds_max=15,
            )
            return GMGNThresholdStrategy(config)
        if name == "whale_copy":
            config = WhaleConfig(
                whitelist_wallets=[],
                delay_seconds_min=5,
                delay_seconds_max=15,
                follow_sell=True,
                trailing_arm_pct=0.8,
                trailing_pct=0.2,
                stop_loss_pct=0.25,
            )
            return WhaleCopyStrategy(config)
        raise ValueError(f"Unsupported strategy {name}")

    def _load(self, name: str) -> pd.DataFrame:
        path = self.data_path / f"{name}.parquet"
        if not path.exists():
            return pd.DataFrame()
        return pd.read_parquet(path)
