# manju/kis/parse.py
"""KIS 실시간 프레임 파서. 순수함수 (네트워크 없음)."""
from __future__ import annotations
from datetime import datetime
from manju.models import Trade, OrderBook
from manju.kis.constants import TRADE_TR, QUOTE_TR, PRICE_COLUMNS, QUOTE_IDX


def _ts(date_str: str, hms: str, recv: datetime) -> datetime:
    """BSOP_DATE(YYYYMMDD) + 시각(HHMMSS) → datetime. date 없으면 recv 날짜 사용."""
    hms = (hms or "").zfill(6)
    if date_str and len(date_str) == 8:
        d = datetime.strptime(date_str, "%Y%m%d").date()
    else:
        d = recv.date()
    return datetime(d.year, d.month, d.day,
                    int(hms[0:2]), int(hms[2:4]), int(hms[4:6]))


def _to_int(v: str) -> int:
    return int(float(v)) if v not in ("", None) else 0


def _trade(fields: list[str], recv: datetime) -> Trade:
    f = dict(zip(PRICE_COLUMNS, fields))
    return Trade(
        symbol=f["MKSC_SHRN_ISCD"],
        market_ts=_ts(f.get("BSOP_DATE", ""), f["STCK_CNTG_HOUR"], recv),
        recv_ts=recv,
        price=_to_int(f["STCK_PRPR"]),
        change_rate=float(f["PRDY_CTRT"] or 0),
        volume=_to_int(f["CNTG_VOL"]),
        cum_volume=_to_int(f["ACML_VOL"]),
        cum_value=_to_int(f["ACML_TR_PBMN"]),
        strength=float(f["CTTR"] or 0),
        ccld_dvsn=f["CCLD_DVSN"],
        ask1=_to_int(f["ASKP1"]), bid1=_to_int(f["BIDP1"]),
        ask1_qty=_to_int(f["ASKP_RSQN1"]), bid1_qty=_to_int(f["BIDP_RSQN1"]),
        total_ask_qty=_to_int(f["TOTAL_ASKP_RSQN"]),
        total_bid_qty=_to_int(f["TOTAL_BIDP_RSQN"]),
        vi_std_price=_to_int(f["VI_STND_PRC"]),
        raw="^".join(fields),
    )


def _quote(fields: list[str], recv: datetime) -> OrderBook:
    return OrderBook(
        symbol=fields[QUOTE_IDX["symbol"]],
        market_ts=_ts("", fields[QUOTE_IDX["hour"]], recv),
        recv_ts=recv,
        asks=[_to_int(x) for x in fields[QUOTE_IDX["ask"]]],
        bids=[_to_int(x) for x in fields[QUOTE_IDX["bid"]]],
        ask_qtys=[_to_int(x) for x in fields[QUOTE_IDX["ask_qty"]]],
        bid_qtys=[_to_int(x) for x in fields[QUOTE_IDX["bid_qty"]]],
        total_ask_qty=_to_int(fields[QUOTE_IDX["total_ask_qty"]]),
        total_bid_qty=_to_int(fields[QUOTE_IDX["total_bid_qty"]]),
        raw="^".join(fields),
    )


def parse_frame(raw: str, recv: datetime) -> list:
    """실시간 프레임 → [Trade|OrderBook]. 시스템 메시지(JSON)는 []."""
    if not raw or raw[0] not in ("0", "1"):
        return []  # 시스템 메시지(구독확인/PINGPONG)
    parts = raw.split("|")
    if len(parts) < 4:
        return []
    tr_id, count, payload = parts[1], int(parts[2]), parts[3]
    fields = payload.split("^")
    if tr_id == TRADE_TR:
        n = len(PRICE_COLUMNS)
        return [_trade(fields[i * n:(i + 1) * n], recv) for i in range(count)]
    if tr_id == QUOTE_TR:
        n = 45  # 선두 45필드 단위(꼬리 더미 포함 count>1은 균등 분할)
        chunk = len(fields) // count
        return [_quote(fields[i * chunk:(i + 1) * chunk], recv) for i in range(count)]
    return []
