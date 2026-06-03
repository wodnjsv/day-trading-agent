from jongga.backtest.fill_model import buy_fill, sell_fill, is_sellable


def test_buy_fill_adds_slippage():
    assert abs(buy_fill(1000, slippage=0.003) - 1003.0) < 1e-9

def test_sell_fill_subtracts_slippage():
    assert abs(sell_fill(1000, slippage=0.003) - 997.0) < 1e-9

def test_is_sellable_false_when_limit_down_or_halt():
    # 시초가 == 하한가(전일 종가 -30%)면 매도 불가
    assert is_sellable(open_px=700, prev_close=1000, halted=False) is False
    assert is_sellable(open_px=950, prev_close=1000, halted=False) is True
    assert is_sellable(open_px=950, prev_close=1000, halted=True) is False
