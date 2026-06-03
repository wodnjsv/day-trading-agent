# jongga/backtest/engine.py
"""백테스트 엔진: 하루치 종가매수→익일시초매도 청산(§8.2).

run_day는 한 거래일 d의 바스켓을 d 종가 매수, d+1 시초 매도한 종목별 결과를 낸다.
선정/사이징은 호출 측(run_backtest)이 t-1 입력으로 이미 결정해 넘긴다(누수 차단).
"""
from __future__ import annotations
from jongga.backtest.fill_model import buy_fill, sell_fill, is_sellable


def run_day(sized: dict[str, float], close_t: dict[str, float],
            open_t1: dict[str, float], prev_close_for_limit: dict[str, float],
            halted: set[str], slippage: float, sell_tax: float, fee: float) -> dict:
    out = {}
    for sym, _notional in sized.items():
        buy = buy_fill(close_t[sym], slippage)
        op = open_t1.get(sym)
        if op is None or not is_sellable(op, prev_close_for_limit[sym], sym in halted):
            out[sym] = {"ret": 0.0, "forced_hold": True}
            continue
        sell = sell_fill(op, slippage)
        gross = (sell - buy) / buy
        net = gross - sell_tax - 2 * fee
        out[sym] = {"ret": net, "forced_hold": False}
    return out
