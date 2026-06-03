"""pykrx 투자자별 순매수(수급) 프로바이더. KRX 회원 로그인(secrets krx_id/krx_pw) 필요."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from jongga.data.cache import cache_path, load_or_fetch
from jongga.secrets import set_krx_login

NET_VALUE_COL = "순매수거래대금"   # pykrx get_market_net_purchases_of_equities 순매수 금액 컬럼


class PykrxSupply:
    def __init__(self, data_dir, market: str = "KOSDAQ"):
        self.data_dir = Path(data_dir)
        self.market = market

    def supply(self, date: str) -> pd.DataFrame:
        """투자자별 순매수(원). index=ticker, 컬럼: inst_net(기관합계)/foreign_net(외국인)."""
        from pykrx import stock
        set_krx_login()                    # secrets의 krx_id/krx_pw → KRX_ID/KRX_PW (자동 로그인)
        key = date.replace("-", "")

        def fetch():
            inst = stock.get_market_net_purchases_of_equities(key, key, self.market, "기관합계")
            foreign = stock.get_market_net_purchases_of_equities(key, key, self.market, "외국인")
            out = pd.DataFrame({"inst_net": inst[NET_VALUE_COL], "foreign_net": foreign[NET_VALUE_COL]})
            out.index.name = "ticker"
            return out.fillna(0)

        return load_or_fetch(cache_path(self.data_dir, "supply", date), fetch)
