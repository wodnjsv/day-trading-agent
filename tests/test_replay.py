# tests/test_replay.py
from datetime import datetime
from manju.collector.recorder import Recorder
from manju.replay.feed import ReplayFeed
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


def test_replay_yields_time_ordered_events(tmp_path):
    rec = Recorder(tmp_path)
    rec.record(_trade("005930", 3))
    rec.record(_quote("005930", 1))
    rec.record(_trade("005930", 2))
    rec.flush()

    events = list(ReplayFeed(tmp_path, "2026-06-01").events())
    secs = [e.market_ts.second for e in events]
    assert secs == [1, 2, 3]                      # 시간순
    assert isinstance(events[0], OrderBook)        # 1초=호가
    assert isinstance(events[1], Trade)            # 2초=체결
    assert events[1].price == 70000               # 스키마 복원 확인


def test_replay_empty_date_yields_nothing(tmp_path):
    assert list(ReplayFeed(tmp_path, "2099-01-01").events()) == []
