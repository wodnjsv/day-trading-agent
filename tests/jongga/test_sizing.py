from jongga.sizing import size_basket


def test_size_basket_regime_and_caps():
    picks = [("A", 0.9), ("B", 0.1)]          # conviction은 사이징 미사용
    out = size_basket(picks, capital=1000, regime_mult=1.0,
                      per_symbol_cap_frac=0.4, value_cap={"A": 1e9, "B": 1e9})
    assert out["A"] == 400 and out["B"] == 400   # cap에 걸려 각 400

def test_size_basket_value_cap_limits_notional():
    picks = [("A", 0.5)]
    out = size_basket(picks, capital=1_000_000, regime_mult=1.0,
                      per_symbol_cap_frac=1.0, value_cap={"A": 300_000})
    assert out["A"] == 300_000                   # 거래대금 proxy cap
