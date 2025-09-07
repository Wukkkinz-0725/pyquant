"""Compute very small signal scores."""

from __future__ import annotations


def score_signal(confidence: float, stance_dir: int, momentum: float) -> float:
    """Blend confidence, stance and momentum into a single score."""
    return 0.5 * confidence + 0.3 * stance_dir + 0.2 * momentum


__all__ = ["score_signal"]
