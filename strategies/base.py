"""Strategy interfaces and shared utilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol

import pandas as pd

from core.models import Signal


class Strategy(Protocol):
    """Protocol each strategy must satisfy."""

    def generate_signals(
        self,
        swaps: pd.DataFrame,
        pools: pd.DataFrame,
        token_meta: pd.DataFrame,
    ) -> list[Signal]:
        """Produce strategy signals from normalized data."""


@dataclass(slots=True)
class SignalEnvelope:
    """Helper to bundle signals with provenance for debugging."""

    strategy: str
    signals: list[Signal]
    generated_at: datetime
