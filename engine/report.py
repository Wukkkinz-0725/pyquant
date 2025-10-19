"""Reporting utilities for simulations."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
from rich.console import Console
from rich.table import Table

from core.models import Order
from engine.metrics import compute_metrics, equity_curve


def save_report(sim_id: str, orders: Iterable[Order], console: Console | None = None) -> Path:
    """Persist metrics and equity plot to the reports directory."""
    report_dir = Path("reports") / f"run_{sim_id}"
    report_dir.mkdir(parents=True, exist_ok=True)

    metrics = compute_metrics(orders)
    metrics_path = report_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, default=str))

    eq = equity_curve(orders)
    if not eq.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        eq.plot(ax=ax, label="Equity")
        drawdown = (eq.cummax() - eq)
        ax.fill_between(eq.index, eq - drawdown, eq, color="red", alpha=0.2, label="Drawdown")
        ax.set_title("Equity Curve")
        ax.legend()
        fig.tight_layout()
        fig_path = report_dir / "equity.png"
        fig.savefig(fig_path)
        plt.close(fig)
    else:
        fig_path = None

    if console:
        table = Table(title=f"Run {sim_id} summary")
        table.add_column("Metric")
        table.add_column("Value")
        for key, value in metrics.items():
            table.add_row(key, f"{value:.4f}")
        console.print(table)
    return report_dir
