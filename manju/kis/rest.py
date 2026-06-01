# manju/kis/rest.py
"""KIS REST: 거래대금 상위 종목 조회."""
from __future__ import annotations
import requests
from manju.config import Config
from manju.kis.constants import VOLUME_RANK_TR, VOLUME_RANK_PATH


def top_symbols_by_value(token: str, cfg: Config, n: int) -> list[str]:
    """거래대금 상위 n개 종목코드(순위순)."""
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": cfg.app_key,
        "appsecret": cfg.app_secret,
        "tr_id": VOLUME_RANK_TR,
        "custtype": "P",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_COND_SCR_DIV_CODE": "20171",
        "FID_INPUT_ISCD": "0000",        # 0000:전체
        "FID_DIV_CLS_CODE": "0",
        "FID_BLNG_CLS_CODE": "3",        # 3:거래대금순
        "FID_TRGT_CLS_CODE": "111111111",
        "FID_TRGT_EXLS_CLS_CODE": "000000",
        "FID_INPUT_PRICE_1": "",
        "FID_INPUT_PRICE_2": "",
        "FID_VOL_CNT": "",
        "FID_INPUT_DATE_1": "",
    }
    r = requests.get(cfg.base_url + VOLUME_RANK_PATH, headers=headers,
                     params=params, timeout=10)
    r.raise_for_status()
    rows = r.json().get("output", [])
    return [row["mksc_shrn_iscd"] for row in rows[:n]]
