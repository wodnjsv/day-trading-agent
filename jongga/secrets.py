"""secrets.yaml 로더 + KRX 회원 로그인 환경변수 설정.

pykrx는 data.krx.co.kr 투자자별 수급 조회 시 KRX_ID/KRX_PW 환경변수로 자동 로그인한다
(pykrx/website/comm/auth.py). 여기서 secrets.yaml의 krx_id/krx_pw를 그 환경변수로 옮겨준다.
"""
from __future__ import annotations
import os
from pathlib import Path

import yaml


def load_secrets(path: str = "secrets.yaml") -> dict:
    p = Path(path)
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def set_krx_login(secrets: dict | None = None) -> bool:
    """secrets의 krx_id/krx_pw를 KRX_ID/KRX_PW 환경변수로 설정. 둘 다 있으면 True."""
    s = secrets if secrets is not None else load_secrets()
    kid, kpw = (s.get("krx_id") or "").strip(), (s.get("krx_pw") or "").strip()
    if kid and kpw:
        os.environ["KRX_ID"] = kid
        os.environ["KRX_PW"] = kpw
        return True
    return False
