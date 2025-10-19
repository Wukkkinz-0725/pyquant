"""Historical backtesting harness."""
from __future__ import annotations

import itertools
import json
import logging
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd
import yaml
from rich.console import Console

from core.models import Order, Signal, TokenMeta
from engine.execution import ExecutionContext, ExecutionEngine, RiskGuards
from engine.report import save_report
from strategies.gmgn_threshold import GMGNConfig, GMGNThresholdStrategy
from strategies.whale_copy import WhaleConfig, WhaleCopyStrategy

logger = logging.getLogger(__name__)


class BacktestRunner:
    """Run backtests and grid searches using configuration files."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console
        self.data_path = Path("data")
        self.strategy_config_path = Path("configs/strategies.yaml")
        self.risk_config_path = Path("configs/risk.yaml")
        self._strategy_cfg = yaml.safe_load(self.strategy_config_path.read_text())
        self._risk_cfg = yaml.safe_load(self.risk_config_path.read_text())

    def run(
        self,
        strategy_name: str,
        start_ts: datetime,
        end_ts: datetime,
        overrides: Optional[Dict[str, object]] = None,
    ) -> Path:
        swaps = self._load_parquet("swaps")
        pools = self._load_parquet("pool_states")
        token_meta = self._load_parquet("token_meta")
        swaps = self._window(swaps, start_ts, end_ts, "ts")
        pools = self._window(pools, start_ts, end_ts, "ts")
        strategy, context = self._build_strategy(strategy_name, overrides or {})
        guards = RiskGuards(**self._risk_cfg["guards"])
        token_meta_map = (
            {
                row["token_address"]: TokenMeta(**{k: row.to_dict().get(k) for k in TokenMeta.model_fields})
                for _, row in token_meta.iterrows()
            }
            if not token_meta.empty
            else {}
        )
        engine = ExecutionEngine(guards=guards, token_meta=token_meta_map, context=context)

        signals = strategy.generate_signals(swaps, pools, token_meta)
        if self.console:
            self.console.log(f"Generated {len(signals)} signals")
        for signal in sorted(signals, key=lambda s: s.ts):
            pool_row = self._select_pool(pools, signal)
            if pool_row is None:
                continue
            action = signal.meta.get("action", "buy")
            engine.submit_order(signal, pool_row, side=action)
        engine.close_all(pools)
        orders = list(engine.state.orders)
        sim_id = uuid.uuid4().hex[:8]
        report_dir = save_report(sim_id, orders, console=self.console)
        return report_dir

    def grid_search(self, strategy_name: str) -> None:
        grid_cfg = self._strategy_cfg.get("grid_search", {})
        if grid_cfg.get("strategy") != strategy_name:
            raise ValueError("Grid search configuration does not match strategy")
        base_params = self._strategy_cfg[strategy_name]
        param_grid = grid_cfg.get("params", [])
        combos = []
        for param_set in param_grid:
            keys = list(param_set.keys())
            values = itertools.product(*param_set.values())
            for combo in values:
                overrides = {k: v for k, v in zip(keys, combo)}
                combos.append(overrides)
        for overrides in combos:
            self.run(
                strategy_name=strategy_name,
                start_ts=datetime.utcnow(),
                end_ts=datetime.utcnow(),
                overrides=overrides,
            )

    def _build_strategy(self, name: str, overrides: Dict[str, object]) -> tuple[object, ExecutionContext]:
        params = dict(self._strategy_cfg[name])
        params.update(overrides)
        if name == "gmgn_threshold":
            config = GMGNConfig(
                liq_usd_min=params["liq_usd_min"],
                net_buy_5m_min=params["net_buy_5m_min"],
                max_buy_tax_bps=params["max_buy_tax_bps"],
                max_sell_tax_bps=params["max_sell_tax_bps"],
                trailing_arm_pct=params["trailing_arm_pct"],
                trailing_pct=params["trailing_pct"],
                stop_loss_pct=params["stop_loss_pct"],
                delay_seconds_min=params["delay_seconds_min"],
                delay_seconds_max=params["delay_seconds_max"],
            )
            context = ExecutionContext(
                delay_seconds_min=config.delay_seconds_min,
                delay_seconds_max=config.delay_seconds_max,
                trailing_arm_pct=config.trailing_arm_pct,
                trailing_pct=config.trailing_pct,
                stop_loss_pct=config.stop_loss_pct,
            )
            return GMGNThresholdStrategy(config), context
        if name == "whale_copy":
            config = WhaleConfig(
                whitelist_wallets=params.get("whitelist_wallets", []),
                delay_seconds_min=params["delay_seconds_min"],
                delay_seconds_max=params["delay_seconds_max"],
                follow_sell=params.get("follow_sell", True),
                trailing_arm_pct=params["trailing_arm_pct"],
                trailing_pct=params["trailing_pct"],
                stop_loss_pct=params["stop_loss_pct"],
            )
            context = ExecutionContext(
                delay_seconds_min=config.delay_seconds_min,
                delay_seconds_max=config.delay_seconds_max,
                trailing_arm_pct=config.trailing_arm_pct,
                trailing_pct=config.trailing_pct,
                stop_loss_pct=config.stop_loss_pct,
                follow_sell=config.follow_sell,
            )
            return WhaleCopyStrategy(config), context
        raise ValueError(f"Unknown strategy {name}")

    def _load_parquet(self, name: str) -> pd.DataFrame:
        path = self.data_path / f"{name}.parquet"
        if not path.exists():
            return pd.DataFrame()
        return pd.read_parquet(path)

    def _window(self, df: pd.DataFrame, start: datetime, end: datetime, column: str) -> pd.DataFrame:
        if df.empty:
            return df
        return df[(df[column] >= start) & (df[column] <= end)]

    def _select_pool(self, pools: pd.DataFrame, signal: Signal) -> Optional[pd.Series]:
        token_pools = pools[pools["token_address"] == signal.token_address]
        if token_pools.empty:
            return None
        token_pools = token_pools.sort_values("ts")
        after = token_pools[token_pools["ts"] >= signal.ts]
        if not after.empty:
            return after.iloc[0]
        return token_pools.iloc[-1]
