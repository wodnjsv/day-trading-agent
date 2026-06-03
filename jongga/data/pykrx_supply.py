"""pykrx 투자자별 순매수(수급) 프로바이더.
컬럼명(순매수거래대금)은 Step 6 실호출 시도로 확인 예정 — KRX 로그인 필요."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from jongga.data.cache import cache_path, load_or_fetch


class PykrxSupply:
    def __init__(self, data_dir, market: str = "KOSDAQ"):
        self.data_dir = Path(data_dir)
        self.market = market

    def supply(self, date: str) -> pd.DataFrame:
        from pykrx import stock
        key = date.replace("-", "")

        def fetch():
            inst = stock.get_market_net_purchases_of_equities(key, key, self.market, "기관합계")
            foreign = stock.get_market_net_purchases_of_equities(key, key, self.market, "외국인")
            col = "순매수거래대금"  # ← pykrx 실호출 컬럼명 (KRX 로그인 필요)
            out = pd.DataFrame({"inst_net": inst[col], "foreign_net": foreign[col]})
            out.index.name = "ticker"
            return out.fillna(0)

        return load_or_fetch(cache_path(self.data_dir, "supply", date), fetch)
