"""Command line interface for the BSC memecoin backtester."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from typer import Option

from core.db import create_all_tables, get_engine
from ingest.builder import IngestBuilder
from sim.backtest import BacktestRunner
from sim.paper import PaperTrader

APP = typer.Typer(help="Backtesting and paper trading utilities for BSC memecoins.")
console = Console()


def configure_logging() -> None:
    """Configure standard logging with Rich handler for CLI readability."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@APP.command("setup-db")
def setup_db() -> None:
    """Create database tables defined in the SQLAlchemy metadata."""
    configure_logging()
    engine = get_engine()
    create_all_tables(engine)
    console.log("Database initialized", style="bold green")


@APP.command("ingest")
def ingest(
    start: str = Option(..., "--start", help="Inclusive UTC start date YYYY-MM-DD"),
    end: str = Option(..., "--end", help="Inclusive UTC end date YYYY-MM-DD"),
    quote: str = Option("USDT", "--quote", help="Quote token symbol to filter"),
    tokens: Optional[str] = Option(None, "--tokens", help="Comma-separated token symbols"),
) -> None:
    """Ingest swaps and persist normalized datasets."""
    configure_logging()
    builder = IngestBuilder(console=console)
    token_list = tokens.split(",") if tokens else None
    builder.run(
        start_ts=datetime.fromisoformat(start),
        end_ts=datetime.fromisoformat(end),
        quote_symbol=quote,
        tokens=token_list,
    )


@APP.command("backtest")
def backtest(
    strategy: str = Option(..., "--strategy", help="Strategy key in configs/strategies.yaml"),
    start: str = Option(..., "--start", help="Inclusive start date"),
    end: str = Option(..., "--end", help="Inclusive end date"),
    override: Optional[str] = Option(None, "--override", help="Comma-separated key=value overrides"),
) -> None:
    """Run a single backtest for the provided strategy and config override."""
    configure_logging()
    runner = BacktestRunner(console=console)
    overrides = {}
    if override:
        for part in override.split(","):
            key, value = part.split("=")
            try:
                overrides[key] = json.loads(value)
            except json.JSONDecodeError:
                overrides[key] = value
    result_dir = runner.run(
        strategy_name=strategy,
        start_ts=datetime.fromisoformat(start),
        end_ts=datetime.fromisoformat(end),
        overrides=overrides,
    )
    console.log(f"Backtest complete: {result_dir}", style="bold green")


@APP.command("grid")
def grid(strategy: str = Option(..., "--strategy", help="Strategy key for grid search")) -> None:
    """Run a grid search based on configs/strategies.yaml definitions."""
    configure_logging()
    runner = BacktestRunner(console=console)
    runner.grid_search(strategy_name=strategy)


@APP.command("paper")
def paper(strategy: str = Option(..., "--strategy", help="Strategy key for paper trading")) -> None:
    """Start a paper-trading loop using the latest five-second bars."""
    configure_logging()
    trader = PaperTrader(console=console)
    trader.run(strategy_name=strategy)


if __name__ == "__main__":
    APP()
