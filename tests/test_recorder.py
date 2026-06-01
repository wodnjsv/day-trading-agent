# tests/test_recorder.py
from datetime import datetime
import pyarrow.parquet as pq
from manju.collector.recorder import Recorder
from manju.models import Trade, OrderBook


def _trade(sym, sec):
    ts = datetime(2026, 6, 1, 9, 0, sec)
    return Trade(symbol=sym, market_ts=ts, recv_ts=ts, price=70000, change_rate=1.0,
                 volume=1, cum_volume=1, cum_value=1, strength=100.0, ccld_dvsn="1",
                 ask1=70100, bid1=70000, ask1_qty=1, bid1_qty=1,
                 total_ask_qty=1, total_bid_qty=1, vi_std_price=0, raw="r")


def _quote(sym, sec):
    ts = datetime(2026, 6, 1, 9, 0, sec)
    return OrderBook(symbol=sym, market_ts=ts, recv_ts=ts,
                     asks=[1]*10, bids=[1]*10, ask_qtys=[1]*10, bid_qtys=[1]*10,
                     total_ask_qty=10, total_bid_qty=10, raw="r")


def test_recorder_writes_partitioned_parquet(tmp_path):
    rec = Recorder(tmp_path)
    rec.record(_trade("005930", 1))
    rec.record(_trade("005930", 2))
    rec.record(_quote("005930", 1))
    rec.flush()

    tick_files = list((tmp_path / "ticks" / "2026-06-01").glob("005930-*.parquet"))
    quote_files = list((tmp_path / "quotes" / "2026-06-01").glob("005930-*.parquet"))
    assert len(tick_files) == 1 and len(quote_files) == 1

    t = pq.read_table(tick_files[0]).to_pylist()
    assert len(t) == 2
    assert t[0]["symbol"] == "005930" and t[0]["ccld_dvsn"] == "1"


def test_flush_clears_buffer(tmp_path):
    rec = Recorder(tmp_path)
    rec.record(_trade("000660", 1))
    rec.flush()
    rec.flush()   # 두 번째 flush는 빈 버퍼 → 추가 파일 없음
    files = list((tmp_path / "ticks" / "2026-06-01").glob("000660-*.parquet"))
    assert len(files) == 1
