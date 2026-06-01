import json
from manju.kis.ws import build_sub_message


def test_build_register_message():
    msg = build_sub_message("APPR", "H0STCNT0", "005930", register=True)
    d = json.loads(msg)
    assert d["header"]["approval_key"] == "APPR"
    assert d["header"]["tr_type"] == "1"        # 등록
    assert d["header"]["custtype"] == "P"
    assert d["body"]["input"] == {"tr_id": "H0STCNT0", "tr_key": "005930"}


def test_build_unregister_message():
    msg = build_sub_message("APPR", "H0STASP0", "000660", register=False)
    assert json.loads(msg)["header"]["tr_type"] == "2"   # 해지
