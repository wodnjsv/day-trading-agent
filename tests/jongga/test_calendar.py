from jongga.calendar import prev_trading_day, next_trading_day


def test_prev_and_next_trading_day():
    days = ["2026-06-01", "2026-06-02", "2026-06-03"]
    assert prev_trading_day("2026-06-03", days) == "2026-06-02"
    assert next_trading_day("2026-06-02", days) == "2026-06-03"
    assert prev_trading_day("2026-06-01", days) is None
    assert next_trading_day("2026-06-03", days) is None
