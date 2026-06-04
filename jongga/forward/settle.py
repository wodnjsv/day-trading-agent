"""익일 정산: 미정산 행 + d+1 일봉(+d+2 종가) → exit·net밴드·settled."""
from __future__ import annotations
import pandas as pd
from jongga.forward.cost import overnight_net, SLIP_BANDS
from jongga.forward.paperbook import PaperBook


def settle_day(pb: PaperBook, run_date: str, d1: pd.DataFrame, d2: pd.DataFrame) -> int:
    """run_date의 미정산 포지션을 d1(익일 OHLC)·d2(d+2 종가)로 정산. 정산 건수 반환.

    주의: d1은 run_date+1 거래일의 일봉(종가 확정 후 EOD), d2는 run_date+2 거래일 종가.
    따라서 morn 커맨드는 exit 당일(d+1) 장 마감 후 저녁 이후에 실행해야 d1 종가가 확정된다.
    """
    d1 = d1[~d1.index.duplicated()]
    if d2 is not None:
        d2 = d2[~d2.index.duplicated()]
    settled = 0
    for row in pb.open_positions(run_date):
        t = row["ticker"]
        if t not in d1.index or pd.isna(d1.loc[t, "open"]):
            continue
        exit_open = float(d1.loc[t, "open"])
        nets = {s: overnight_net(row["entry_close"], exit_open, s) for s in SLIP_BANDS}
        c2 = float(d2.loc[t, "close"]) if (d2 is not None and t in d2.index) else None
        pb.settle(row["id"], exit_open, float(d1.loc[t, "high"]), float(d1.loc[t, "low"]),
                  float(d1.loc[t, "close"]), c2, nets)
        settled += 1
    return settled
