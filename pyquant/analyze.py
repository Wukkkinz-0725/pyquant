from __future__ import annotations

import re
from typing import List


_KNOWN = ["BTC", "ETH", "SOL", "DOGE", "ADA", "XRP"]
_COIN_RE = re.compile(r"\b(BTC|ETH|SOL|DOGE|ADA|XRP)\b|\$([A-Z]{2,5})")


def extract_coins(text: str) -> List[str]:
    """Extract coin tickers from text using a simple regex.

    Matches common symbols and $TICKER patterns. Returns uppercase uniques.
    """
    found: list[str] = []
    for m in _COIN_RE.finditer(text or ""):
        g1, g2 = m.groups()
        sym = (g1 or g2 or "").upper().lstrip("$")
        if sym:
            found.append(sym)
    # keep order, dedupe
    seen: set[str] = set()
    out: list[str] = []
    for s in found:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def stance_to_dir(stance: str) -> int:
    """Map stance to numeric direction."""
    s = (stance or "").strip().lower()
    if s == "bull":
        return 1
    if s == "bear":
        return -1
    return 0

