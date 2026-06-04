import pandas as pd
from jongga.forward.screen import entry_covariates


def test_entry_covariates():
    closes = pd.Series([100.0, 110.0, 99.0, 105.0, 120.0])
    cov = entry_covariates(closes, open_d=100.0, high_d=125.0, low_d=98.0,
                           value_d=5_000_000_000, vol_window=4)
    assert abs(cov["ret_d"] - (120 - 105) / 105) < 1e-9
    assert abs(cov["close_pos"] - (120 - 98) / (125 - 98)) < 1e-9
    assert abs(cov["close_strength"] - (120 - 100) / 100) < 1e-9
    assert cov["trade_value"] == 5_000_000_000
    assert cov["vol20"] > 0
