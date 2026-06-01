# tests/test_rest.py
import manju.kis.rest as rest
from manju.config import Config

CFG = Config(app_key="AK", app_secret="AS", account_no="12345678", is_paper=False)


class _Resp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p


def test_top_symbols_extracts_codes_in_rank_order(monkeypatch):
    payload = {"output": [
        {"mksc_shrn_iscd": "111111", "data_rank": "1"},
        {"mksc_shrn_iscd": "222222", "data_rank": "2"},
        {"mksc_shrn_iscd": "333333", "data_rank": "3"},
    ]}
    def fake_get(url, headers=None, params=None, timeout=None):
        assert headers["tr_id"] == "FHPST01710000"
        assert params["FID_BLNG_CLS_CODE"] == "3"   # 거래대금순
        return _Resp(payload)
    monkeypatch.setattr(rest.requests, "get", fake_get)

    codes = rest.top_symbols_by_value("TOK", CFG, n=2)
    assert codes == ["111111", "222222"]
