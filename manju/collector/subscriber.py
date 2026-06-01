"""universe 변경 → WS 등록/해지 액션 산출. 종목당 체결+호가 2건."""
from __future__ import annotations
from manju.kis.constants import TRADE_TR, QUOTE_TR

_PER_SYMBOL = (TRADE_TR, QUOTE_TR)   # 종목당 등록 TR 2개


def plan_changes(current: set[str], desired: list[str], max_reg: int):
    """
    Args:
        current: 현재 구독 중인 종목 집합
        desired: 원하는 종목(순위순)
        max_reg: 세션 실시간 등록 한도(건수). 종목당 2건.
    Returns:
        (to_register, to_unregister, active_symbols)
        to_*: [(tr_id, symbol), ...]
    """
    max_symbols = max_reg // len(_PER_SYMBOL)
    active = desired[:max_symbols]
    active_set = set(active)

    to_unreg = [(tr, s) for s in current - active_set for tr in _PER_SYMBOL]
    to_reg = [(tr, s) for s in active if s not in current for tr in _PER_SYMBOL]
    return to_reg, to_unreg, active
