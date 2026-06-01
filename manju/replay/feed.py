# manju/replay/feed.py
"""ReplayFeed: 녹음 parquet을 시간순으로 재생. LiveFeed와 동일한 Trade/OrderBook 산출."""
from __future__ import annotations
from pathlib import Path
from collections.abc import Iterator
import pyarrow.parquet as pq
from manju.models import Trade, OrderBook


class ReplayFeed:
    def __init__(self, data_dir: Path, date: str):
        self.data_dir = Path(data_dir)
        self.date = date

    def _load(self, kind: str, cls) -> list:
        d = self.data_dir / kind / self.date
        if not d.exists():
            return []
        out = []
        for f in d.glob("*.parquet"):
            for row in pq.read_table(f).to_pylist():
                out.append(cls.from_row(row))
        return out

    def events(self) -> Iterator:
        merged = self._load("ticks", Trade) + self._load("quotes", OrderBook)
        merged.sort(key=lambda e: (e.market_ts, e.recv_ts))
        yield from merged
