# jongga/factors/flow.py
"""t-1 수급 팩터(순수)."""
from __future__ import annotations
import pandas as pd


def supply_factor(recent: pd.DataFrame, lookback: int = 5) -> float:
    """최근 lookback일 (외국인+기관) 순매수 누적 / 거래대금 누적."""
    w = recent.tail(lookback)
    net = (w["inst_net"] + w["foreign_net"]).sum()
    denom = w["value"].sum()
    return float(net / denom) if denom else 0.0
