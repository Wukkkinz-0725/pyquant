from datetime import datetime, timezone

import pandas as pd

from ingest.builder import IngestBuilder


def test_pool_reconstruction_columns():
    builder = IngestBuilder(console=None)
    swaps = pd.DataFrame(
        {
            "token_address": ["token", "token"],
            "pool_address": ["pool", "pool"],
            "ts": [datetime(2025, 10, 10, 0, 0, tzinfo=timezone.utc), datetime(2025, 10, 10, 0, 0, 5, tzinfo=timezone.utc)],
            "block_number": [1, 2],
            "side": ["buy", "buy"],
            "price": [1.0, 1.1],
            "amount_in": [10.0, 15.0],
            "amount_out": [9.0, 13.0],
            "tx_hash": ["0x1", "0x2"],
            "wallet": ["0xa", "0xb"],
        }
    )
    pools = builder._reconstruct_pools(swaps)
    expected_columns = {
        "pool_address",
        "token_address",
        "token0",
        "token1",
        "fee_bps",
        "reserve0",
        "reserve1",
        "ts",
        "price",
    }
    assert set(pools.columns) == expected_columns
    assert pools["ts"].is_monotonic_increasing
