# bsc-meme-backtester

A production-oriented yet extensible research harness for Binance Smart Chain (BSC) memecoin strategies. The project prioritises five-second bar fidelity, modular adapters, and pragmatic risk guardrails suitable for rapid experimentation.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill SHROOMDK_KEY and BSCSCAN_API_KEY at minimum
```

Initialize the SQLite database:

```bash
python app.py setup-db
```

Ingest historical swaps (example for USDT quote pairs over a weekend window):

```bash
python app.py ingest --start 2025-10-10 --end 2025-10-12 --quote USDT --tokens CAKE,WBNB
```

Run a backtest using the default GMGN-style threshold strategy:

```bash
python app.py backtest --strategy gmgn_threshold --start 2025-10-10 --end 2025-10-12
```

Review results inside `reports/run_<sim_id>/` where both JSON metrics and equity/drawdown plots are stored.

### Optional flows

Run a grid search using the configuration defined in `configs/strategies.yaml`:

```bash
python app.py grid --strategy gmgn_threshold
```

Execute a paper-trading (shadow) loop that consumes the most recent five-second parquet bars without broadcasting any transactions:

```bash
python app.py paper --strategy whale_copy
```

## Data assumptions and limitations

* **Five-second bars** are rebuilt from swap-level data. A gap-filling tolerance is applied, but chain congestion can still introduce missing buckets; the engine interpolates using the last known reserves where necessary.
* **AMM modeling** supports constant-product pools natively and approximates concentrated liquidity with a single effective range. This is conservative for out-of-range pools but keeps the math tractable.
* **Taxes and honeypot detection** rely on BscScan heuristics. Fields are nullable and defaults remain defensive (rejecting missing tax data when risk configs demand it).
* **Latency modeling** assumes a uniform random delay between strategy-configured bounds. This approximates pending mempool visibility for lightweight bots without simulating full mempool mechanics.

## Adding a new strategy

1. Create a module inside `strategies/` that implements the `Strategy` protocol from `strategies/base.py`.
2. Use strongly typed dataclasses for signal metadata so downstream components remain stable.
3. Register default parameters in `configs/strategies.yaml` under a unique key.
4. Optionally add grid-search scenarios inside the same config file to allow CLI-driven sweeps.
5. Add focused tests under `tests/` validating signal generation edge cases.

## Future integrations

* **Bitquery** – add another data adapter in `ingest/` that populates the same normalized DataFrame shape as `flipside_client.fetch_swaps`.
* **Tenderly or BSC archive nodes** – implement richer execution simulations inside `engine/execution.py` by swapping in a new dependency-injected gas/latency model.

These integrations simply require wiring new adapters into the ingest builder and updating CLI options thanks to the inversion-friendly architecture.
