"""Ingestion orchestration module."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
import yaml
from rich.console import Console

from core.db import session_scope
from core.models import PoolStateORM, SwapORM, TokenMetaORM
from core.timeutils import floor_to_bucket
from ingest.bscscan_meta import enrich_token_meta
from ingest.dexscreener_client import fetch_pairs_snapshot
from ingest.flipside_client import fetch_swaps

logger = logging.getLogger(__name__)


@dataclass
class IngestConfig:
    """Minimal config representation for datasource toggles."""

    flipside_enabled: bool
    dexscreener_enabled: bool
    bscscan_enabled: bool

    @classmethod
    def from_file(cls, path: Path) -> "IngestConfig":
        data = yaml.safe_load(path.read_text())
        return cls(
            flipside_enabled=data.get("flipside", {}).get("enabled", False),
            dexscreener_enabled=data.get("dexscreener", {}).get("enabled", False),
            bscscan_enabled=data.get("bscscan", {}).get("enabled", False),
        )


class IngestBuilder:
    """Coordinates data ingestion and normalization."""

    def __init__(self, console: Optional[Console] = None, config_path: Path | None = None) -> None:
        self.console = console
        self.config_path = config_path or Path("configs/datasources.yaml")
        self.config = IngestConfig.from_file(self.config_path)

    def run(
        self,
        start_ts: datetime,
        end_ts: datetime,
        quote_symbol: str,
        tokens: Optional[Iterable[str]] = None,
    ) -> None:
        """Kick off ingestion for the provided window."""
        if self.console:
            self.console.log("Fetching swaps...")
        swaps_df = self._fetch_swaps(start_ts, end_ts, quote_symbol)
        if tokens:
            swaps_df = swaps_df[swaps_df["token_address"].isin(tokens)]
        if swaps_df.empty:
            if self.console:
                self.console.log("No swaps found for window", style="yellow")
            return

        pool_states_df = self._reconstruct_pools(swaps_df)
        token_meta_df = (
            enrich_token_meta(swaps_df["token_address"].unique()) if self.config.bscscan_enabled else pd.DataFrame()
        )
        if self.config.dexscreener_enabled and self.console:
            snapshot = fetch_pairs_snapshot(swaps_df["token_address"].unique())
            self.console.log(f"Dexscreener snapshot rows: {len(snapshot)}")
        self._write_outputs(swaps_df, pool_states_df, token_meta_df)
        if self.console:
            self.console.log("Ingestion complete", style="bold green")

    def _fetch_swaps(self, start_ts: datetime, end_ts: datetime, quote_symbol: str) -> pd.DataFrame:
        if not self.config.flipside_enabled:
            raise RuntimeError("Flipside datasource disabled in config")
        df = fetch_swaps(start_ts.isoformat(), end_ts.isoformat(), base_or_quote=quote_symbol)
        return df

    def _reconstruct_pools(self, swaps_df: pd.DataFrame) -> pd.DataFrame:
        """Rebuild reserve snapshots by aggregating swaps in five-second buckets."""
        swaps_df = swaps_df.copy()
        swaps_df["bucket"] = swaps_df["ts"].apply(floor_to_bucket)
        agg = swaps_df.groupby(["pool_address", "bucket"]).agg(
            amount_in=("amount_in", "sum"),
            amount_out=("amount_out", "sum"),
            price=("price", "mean"),
        ).reset_index()
        agg.rename(columns={"bucket": "ts"}, inplace=True)
        agg["reserve0"] = agg.groupby("pool_address")["amount_in"].cumsum()
        agg["reserve1"] = agg.groupby("pool_address")["amount_out"].cumsum()
        pool_tokens = swaps_df.groupby("pool_address")["token_address"].first()
        agg["token0"] = agg["pool_address"].map(pool_tokens)
        agg["token1"] = "USDT"
        agg["fee_bps"] = 300
        agg["token_address"] = agg["token0"]
        return agg[["pool_address", "token_address", "token0", "token1", "fee_bps", "reserve0", "reserve1", "ts", "price"]]

    def _write_outputs(
        self,
        swaps_df: pd.DataFrame,
        pool_states_df: pd.DataFrame,
        token_meta_df: pd.DataFrame,
    ) -> None:
        Path("data").mkdir(exist_ok=True)
        swaps_path = Path("data/swaps.parquet")
        pools_path = Path("data/pool_states.parquet")
        swaps_df.to_parquet(swaps_path, index=False)
        pool_states_df.to_parquet(pools_path, index=False)
        if not token_meta_df.empty:
            token_meta_df.to_parquet(Path("data/token_meta.parquet"), index=False)
        if self.console:
            self.console.log(f"Swaps saved to {swaps_path}")
            self.console.log(f"Pool states saved to {pools_path}")

        with session_scope() as session:
            session.query(SwapORM).delete()
            session.query(PoolStateORM).delete()
            session.query(TokenMetaORM).delete()
            session.bulk_insert_mappings(SwapORM, swaps_df.to_dict(orient="records"))
            session.bulk_insert_mappings(PoolStateORM, pool_states_df.to_dict(orient="records"))
            if not token_meta_df.empty:
                session.bulk_insert_mappings(TokenMetaORM, token_meta_df.to_dict(orient="records"))
