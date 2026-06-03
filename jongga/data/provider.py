"""MarketDataProvider 추상 인터페이스. 백테스트 1차=KRX OpenAPI / 수급=pykrx."""
from __future__ import annotations
from typing import Protocol
import pandas as pd


class MarketDataProvider(Protocol):
    def daily(self, date: str) -> pd.DataFrame:
        """그 날짜 전종목 일별매매. index=ticker(ISU_CD), 컬럼:
        open/high/low/close/volume/value/marketcap/shares/sect.
        index 자체가 그 시점 PIT 멤버십(상폐 포함 → 생존편향 차단)."""
        ...

    def supply(self, date: str) -> pd.DataFrame:
        """투자자별 순매수. index=ticker, 컬럼: inst_net/foreign_net."""
        ...
