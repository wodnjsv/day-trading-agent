import pandas as pd
from jongga.backtest.engine import run_day


def test_run_day_overnight_return_net_of_costs():
    sized = {"A": 100_000}                       # notional
    close_t = {"A": 1000.0}
    open_t1 = {"A": 1100.0}
    res = run_day(sized, close_t, open_t1, prev_close_for_limit={"A": 1000.0},
                  halted=set(), slippage=0.0, sell_tax=0.0, fee=0.0)
    # gross overnight = (1100-1000)/1000 = +10%
    assert abs(res["A"]["ret"] - 0.10) < 1e-9

def test_run_day_unsellable_marks_forced_hold():
    sized = {"A": 100_000}
    res = run_day(sized, {"A": 1000.0}, {"A": 700.0},
                  prev_close_for_limit={"A": 1000.0}, halted=set(),
                  slippage=0.0, sell_tax=0.0, fee=0.0)
    # 시초 700 == 하한가(1000*0.7) → 매도불가 → forced_hold 플래그
    assert res["A"]["forced_hold"] is True
