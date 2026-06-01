# tests/test_parse.py
from datetime import datetime
from manju.kis.parse import parse_frame
from manju.models import Trade, OrderBook
from tests.fixtures import TRADE_FRAME, QUOTE_FRAME

RECV = datetime(2026, 6, 1, 9, 0, 1)


def test_parse_trade_frame():
    events = parse_frame(TRADE_FRAME, RECV)
    assert len(events) == 1
    t = events[0]
    assert isinstance(t, Trade)
    assert t.symbol == "005930"
    assert t.price == 70000
    assert t.change_rate == 12.5
    assert t.strength == 180.5
    assert t.ccld_dvsn == "1"
    assert t.total_bid_qty == 900
    assert t.vi_std_price == 73500
    assert t.market_ts == datetime(2026, 6, 1, 9, 0, 1)


def test_parse_quote_frame():
    events = parse_frame(QUOTE_FRAME, RECV)
    assert len(events) == 1
    ob = events[0]
    assert isinstance(ob, OrderBook)
    assert ob.symbol == "005930"
    assert ob.asks[0] == 70100
    assert ob.bids[9] == 70000 - 900
    assert ob.ask_qtys[0] == 1
    assert ob.total_bid_qty == 155


def test_parse_system_frame_returns_empty():
    # JSON 시스템 메시지(구독확인/PINGPONG)는 이벤트 없음
    assert parse_frame('{"header":{"tr_id":"PINGPONG"}}', RECV) == []


def test_parse_multi_count_trade():
    # count=2 → 두 레코드(46필드*2)
    head, _, payload = TRADE_FRAME.partition("001|")
    frame = "0|H0STCNT0|002|" + payload + "^" + payload
    events = parse_frame(frame, RECV)
    assert len(events) == 2
    assert all(isinstance(e, Trade) for e in events)
