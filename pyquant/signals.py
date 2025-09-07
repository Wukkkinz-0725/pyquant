from __future__ import annotations


def score_signal(confidence: float, stance_dir: int, momentum: float) -> float:
    """Compute a simple signal score from components.

    Weights: 0.5*confidence + 0.3*stance_dir + 0.2*momentum
    """
    c = float(confidence or 0.0)
    s = int(stance_dir or 0)
    m = float(momentum or 0.0)
    return 0.5 * c + 0.3 * s + 0.2 * m

