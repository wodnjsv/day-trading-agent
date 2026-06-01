# manju/config.py
"""수집기 설정. secrets.yaml(비밀) + 기본값으로 구성."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

REAL_BASE = "https://openapi.koreainvestment.com:9443"
PAPER_BASE = "https://openapivts.koreainvestment.com:29443"
REAL_WS = "ws://ops.koreainvestment.com:21000"
PAPER_WS = "ws://ops.koreainvestment.com:31000"


@dataclass
class Config:
    app_key: str
    app_secret: str
    account_no: str
    is_paper: bool = False
    data_dir: Path = Path("data")
    universe_size: int = 20          # 동시 구독 종목 수(체결+호가 = 종목당 등록 2건)
    max_registrations: int = 40      # 세션당 실시간 등록 한도(~41), 종목당 2건
    poll_interval_sec: int = 30      # universe 재선정 주기

    @property
    def base_url(self) -> str:
        return PAPER_BASE if self.is_paper else REAL_BASE

    @property
    def ws_url(self) -> str:
        return PAPER_WS if self.is_paper else REAL_WS

    @classmethod
    def load(cls, path: str = "secrets.yaml") -> "Config":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(
            app_key=raw["app_key"],
            app_secret=raw["app_secret"],
            account_no=str(raw["account_no"]),
            is_paper=bool(raw.get("is_paper", False)),
            data_dir=Path(raw.get("data_dir", "data")),
            universe_size=int(raw.get("universe_size", 20)),
            max_registrations=int(raw.get("max_registrations", 40)),
            poll_interval_sec=int(raw.get("poll_interval_sec", 30)),
        )
