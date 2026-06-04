"""후보 진입 공변량(정량 컨텍스트). 후보 shortlist는 CLI에서 Phase1 universe로 결선."""
from __future__ import annotations
import numpy as np
import pandas as pd


def entry_covariates(closes: pd.Series, open_d: float, high_d: float, low_d: float,
                     value_d: float, vol_window: int = 20) -> dict:
    """당일 d까지 종가시리즈 + 당일 OHLC·거래대금 → 진입 공변량."""
    c = closes.dropna()
    close_d = float(c.iloc[-1])
    prev = float(c.iloc[-2]) if len(c) >= 2 else close_d
    rng = (high_d - low_d)
    logret = np.log(c / c.shift(1)).dropna().tail(vol_window)
    return {
        "ret_d": (close_d - prev) / prev if prev else 0.0,
        "close_pos": (close_d - low_d) / rng if rng else 0.5,
        "close_strength": (close_d - open_d) / open_d if open_d else 0.0,
        "trade_value": float(value_d),
        "vol20": float(logret.std()) if len(logret) >= 2 else 0.0,
    }
