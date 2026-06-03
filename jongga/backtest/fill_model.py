# jongga/backtest/fill_model.py
"""체결모델: 슬리피지 밴드(대칭) + 강제다일 분기(§8.2)."""
from __future__ import annotations

LIMIT = 0.30   # 가격제한폭 ±30%


def buy_fill(close: float, slippage: float) -> float:
    return close * (1.0 + slippage)


def sell_fill(open_px: float, slippage: float) -> float:
    return open_px * (1.0 - slippage)


def is_sellable(open_px: float, prev_close: float, halted: bool) -> bool:
    if halted:
        return False
    lower_limit = round(prev_close * (1.0 - LIMIT))
    return open_px > lower_limit            # 시초가 하한가면 매도 불가
