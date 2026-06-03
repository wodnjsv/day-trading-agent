# jongga/factors/value.py
"""t-1 거래대금 상대순위(0~1, 순수)."""
from __future__ import annotations
import pandas as pd


def value_rank(values: pd.Series) -> pd.Series:
    return values.rank(pct=True)
