# jongga/backtest/metrics.py
"""백테스트 net 메트릭."""
from __future__ import annotations
import numpy as np


def summarize(daily_returns: list[float]) -> dict:
    r = np.array(daily_returns, dtype=float)
    if len(r) == 0:
        return {"n": 0, "mean": 0.0, "win_rate": 0.0, "mdd": 0.0}
    equity = np.cumprod(1 + r)
    peak = np.maximum.accumulate(equity)
    mdd = float((equity / peak - 1).min())
    return {
        "n": int(len(r)),
        "mean": float(r.mean()),
        "win_rate": float((r > 0).mean()),
        "mdd": mdd,
    }
