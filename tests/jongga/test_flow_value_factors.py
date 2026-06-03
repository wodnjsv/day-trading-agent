import pandas as pd
from jongga.factors.flow import supply_factor
from jongga.factors.value import value_rank


def test_supply_factor_5day_cumulative_ratio():
    df = pd.DataFrame({
        "inst_net": [1, 1, 1, 1, 1],
        "foreign_net": [1, 1, 1, 1, 1],
        "value": [10, 10, 10, 10, 10],
    })
    # (5*1 + 5*1) / (5*10) = 10/50 = 0.2
    assert abs(supply_factor(df, lookback=5) - 0.2) < 1e-9


def test_value_rank_is_percentile_0_to_1():
    values = pd.Series({"A": 10, "B": 20, "C": 30, "D": 40})
    r = value_rank(values)
    assert r["D"] == 1.0
    assert 0.0 <= r["A"] < r["B"] < r["C"] < r["D"]
