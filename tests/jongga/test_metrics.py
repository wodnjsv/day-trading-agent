from jongga.backtest.metrics import summarize


def test_summarize_net_and_winrate_and_mdd():
    rets = [0.02, -0.01, 0.03, -0.04]
    m = summarize(rets)
    assert abs(m["mean"] - 0.0) < 0.011
    assert m["win_rate"] == 0.5
    assert m["n"] == 4
    assert m["mdd"] <= 0.0          # MDD는 음수(낙폭)
