# jongga/sizing.py
"""정량가중 sizing(#15). conviction 미사용. 등가중 × 시황배수, caps 적용."""
from __future__ import annotations


def size_basket(picks: list[tuple[str, float]], capital: float, regime_mult: float,
                per_symbol_cap_frac: float, value_cap: dict[str, float]) -> dict[str, float]:
    if not picks or regime_mult == 0:
        return {}
    budget = capital * regime_mult
    each = budget / len(picks)                       # 등가중
    cap_abs = capital * per_symbol_cap_frac
    out = {}
    for sym, _conv in picks:
        notional = min(each, cap_abs, value_cap.get(sym, float("inf")))
        out[sym] = notional
    return out
