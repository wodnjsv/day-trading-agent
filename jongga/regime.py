# jongga/regime.py
"""시황등급/비중배수 — t-1 코스닥 거래대금 기준(사전등록 임계치)."""
from __future__ import annotations

BULL, NEUTRAL, BEAR, HALT = 12e12, 8e12, 5e12, 0.0  # 경계(원)


def regime_multiplier(market_value: float) -> tuple[str, float]:
    if market_value >= BULL:
        return ("BULL", 1.0)
    if market_value >= NEUTRAL:
        return ("NEUTRAL", 0.5)
    if market_value >= BEAR:
        return ("BEAR", 0.2)
    return ("HALT", 0.0)
