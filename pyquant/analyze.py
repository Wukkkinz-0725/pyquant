"""Text helpers for coin extraction and stance mapping."""

from __future__ import annotations

import re
from typing import List

COIN_RE = re.compile(r"\b(?:BTC|ETH|SOL)\b|\$[A-Z]{2,5}", re.IGNORECASE)


def extract_coins(text: str) -> List[str]:
    """Extract coin symbols from *text* using a small regex."""
    coins = [m.group(0).lstrip("$").upper() for m in COIN_RE.finditer(text)]
    return list(dict.fromkeys(coins))  # unique preserving order


STANCE_DIR = {"bull": 1, "neutral": 0, "bear": -1}


def stance_to_dir(stance: str) -> int:
    """Map ``bull``/``bear``/``neutral`` to directional integers."""
    return STANCE_DIR.get(stance, 0)


__all__ = ["extract_coins", "stance_to_dir"]
