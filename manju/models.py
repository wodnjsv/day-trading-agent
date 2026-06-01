# manju/models.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    """실시간 체결(H0STCNT0) 정규화 레코드."""
    symbol: str
    market_ts: datetime      # 장 시간(체결시각)
    recv_ts: datetime        # 수신 벽시계 시각
    price: int               # 현재가 STCK_PRPR
    change_rate: float       # 등락률 PRDY_CTRT
    volume: int              # 체결량 CNTG_VOL
    cum_volume: int          # 누적거래량 ACML_VOL
    cum_value: int           # 누적거래대금 ACML_TR_PBMN
    strength: float          # 체결강도 CTTR
    ccld_dvsn: str           # 체결구분 CCLD_DVSN (1:매수,3:장전,5:매도)
    ask1: int
    bid1: int
    ask1_qty: int
    bid1_qty: int
    total_ask_qty: int       # TOTAL_ASKP_RSQN
    total_bid_qty: int       # TOTAL_BIDP_RSQN
    vi_std_price: int        # VI 기준가 VI_STND_PRC
    raw: str

    def to_row(self) -> dict:
        d = self.__dict__.copy()
        d["market_ts"] = self.market_ts.isoformat()
        d["recv_ts"] = self.recv_ts.isoformat()
        return d

    @classmethod
    def from_row(cls, row: dict) -> "Trade":
        d = dict(row)
        d["market_ts"] = datetime.fromisoformat(d["market_ts"])
        d["recv_ts"] = datetime.fromisoformat(d["recv_ts"])
        return cls(**d)


@dataclass
class OrderBook:
    """실시간 호가(H0STASP0) 정규화 레코드. 10호가."""
    symbol: str
    market_ts: datetime
    recv_ts: datetime
    asks: list[int]          # 매도호가 1..10
    bids: list[int]          # 매수호가 1..10
    ask_qtys: list[int]      # 매도호가 잔량 1..10
    bid_qtys: list[int]      # 매수호가 잔량 1..10
    total_ask_qty: int
    total_bid_qty: int
    raw: str

    def to_row(self) -> dict:
        d = {
            "symbol": self.symbol,
            "market_ts": self.market_ts.isoformat(),
            "recv_ts": self.recv_ts.isoformat(),
            "total_ask_qty": self.total_ask_qty,
            "total_bid_qty": self.total_bid_qty,
            "raw": self.raw,
        }
        for i in range(10):
            d[f"ask{i+1}"] = self.asks[i]
            d[f"bid{i+1}"] = self.bids[i]
            d[f"ask{i+1}_qty"] = self.ask_qtys[i]
            d[f"bid{i+1}_qty"] = self.bid_qtys[i]
        return d

    @classmethod
    def from_row(cls, row: dict) -> "OrderBook":
        return cls(
            symbol=row["symbol"],
            market_ts=datetime.fromisoformat(row["market_ts"]),
            recv_ts=datetime.fromisoformat(row["recv_ts"]),
            asks=[row[f"ask{i+1}"] for i in range(10)],
            bids=[row[f"bid{i+1}"] for i in range(10)],
            ask_qtys=[row[f"ask{i+1}_qty"] for i in range(10)],
            bid_qtys=[row[f"bid{i+1}_qty"] for i in range(10)],
            total_ask_qty=row["total_ask_qty"],
            total_bid_qty=row["total_bid_qty"],
            raw=row["raw"],
        )
