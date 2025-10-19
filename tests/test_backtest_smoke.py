import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from sim.backtest import BacktestRunner


def test_backtest_smoke(tmp_path):
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    for filename in ["swaps.parquet", "pool_states.parquet", "token_meta.parquet"]:
        path = data_dir / filename
        if path.exists():
            path.unlink()
    ts_start = datetime(2025, 10, 10, 0, 0, tzinfo=timezone.utc)
    swaps = pd.DataFrame(
        {
            "token_address": ["token"] * 3,
            "pool_address": ["pool"] * 3,
            "ts": [ts_start, ts_start + timedelta(seconds=5), ts_start + timedelta(seconds=10)],
            "block_number": [1, 2, 3],
            "side": ["buy", "buy", "sell"],
            "price": [1.0, 1.05, 1.1],
            "amount_in": [100.0, 120.0, 80.0],
            "amount_out": [90.0, 100.0, 85.0],
            "tx_hash": ["0x1", "0x2", "0x3"],
            "wallet": ["0xa", "0xb", "0xc"],
        }
    )
    pools = pd.DataFrame(
        {
            "pool_address": ["pool"] * 3,
            "token_address": ["token"] * 3,
            "token0": ["token"] * 3,
            "token1": ["USDT"] * 3,
            "fee_bps": [30] * 3,
            "reserve0": [5000.0, 5050.0, 5100.0],
            "reserve1": [5000.0, 4950.0, 4900.0],
            "ts": [ts_start, ts_start + timedelta(seconds=5), ts_start + timedelta(seconds=10)],
            "price": [1.0, 1.05, 1.1],
        }
    )
    swaps.to_parquet(data_dir / "swaps.parquet", index=False)
    pools.to_parquet(data_dir / "pool_states.parquet", index=False)

    runner = BacktestRunner(console=None)
    report_dir = runner.run(
        strategy_name="gmgn_threshold",
        start_ts=ts_start,
        end_ts=ts_start + pd.Timedelta(minutes=10),
        overrides={"net_buy_5m_min": 1, "liq_usd_min": 0},
    )
    metrics_path = report_dir / "metrics.json"
    assert metrics_path.exists()
    metrics = json.loads(metrics_path.read_text())
    for key in ["total_return", "max_dd", "sharpe", "win_rate", "cost_ratio"]:
        assert key in metrics
