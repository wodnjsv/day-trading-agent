# tests/test_models.py
from datetime import datetime
from manju.models import Trade, OrderBook


def test_trade_row_roundtrip():
    t = Trade(
        symbol="005930", market_ts=datetime(2026, 6, 1, 9, 0, 1),
        recv_ts=datetime(2026, 6, 1, 9, 0, 1), price=70000, change_rate=12.5,
        volume=10, cum_volume=1000, cum_value=70_000_000, strength=180.5,
        ccld_dvsn="1", ask1=70100, bid1=70000, ask1_qty=50, bid1_qty=80,
        total_ask_qty=500, total_bid_qty=900, vi_std_price=73500, raw="raw^string",
    )
    row = t.to_row()
    assert row["symbol"] == "005930"
    assert row["ccld_dvsn"] == "1"
    assert Trade.from_row(row) == t


def test_orderbook_row_roundtrip():
    ob = OrderBook(
        symbol="005930", market_ts=datetime(2026, 6, 1, 9, 0, 1),
        recv_ts=datetime(2026, 6, 1, 9, 0, 1),
        asks=[70100 + i * 100 for i in range(10)],
        bids=[70000 - i * 100 for i in range(10)],
        ask_qtys=[i + 1 for i in range(10)],
        bid_qtys=[i + 11 for i in range(10)],
        total_ask_qty=55, total_bid_qty=155, raw="raw^string",
    )
    row = ob.to_row()
    assert row["ask1"] == 70100
    assert row["bid10"] == 70000 - 900
    assert OrderBook.from_row(row) == ob
