# jongga/calendar.py
"""거래일 유틸. 거래일 리스트는 pykrx ohlcv 인덱스에서 도출(실데이터=실제 영업일)."""
from __future__ import annotations


def prev_trading_day(date: str, trading_days: list[str]) -> str | None:
    i = trading_days.index(date)
    return trading_days[i - 1] if i > 0 else None


def next_trading_day(date: str, trading_days: list[str]) -> str | None:
    i = trading_days.index(date)
    return trading_days[i + 1] if i + 1 < len(trading_days) else None
