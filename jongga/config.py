# jongga/config.py
"""백테스트 설정 + 사전등록 파라미터. 값은 §12.1 사전등록 문서와 일치시킨다."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FactorParams:
    ma_windows: tuple[int, ...] = (5, 20, 60, 120)
    high_window: int = 120          # 신고가 룩백 N
    vol_window: int = 20            # VolRatio 윈도우
    near_ma_pct: float = 0.03       # NearMA ±x%


@dataclass(frozen=True)
class UniverseParams:
    top_k_value: int = 100          # 거래대금 상위 K
    min_marketcap: int = 50_000_000_000  # 안전 시총 하한(동전주·상폐 배제 수준; 랭킹은 별도)


@dataclass(frozen=True)
class Config:
    data_dir: Path = Path("data/krx")
    start_date: str = "2018-01-01"
    holdout_start: str = "2025-01-01"   # 홀드아웃 시작(이전=walk-forward, 이후=최종 1회)
    market: str = "KOSDAQ"              # 시황·universe 기준 시장
    factors: FactorParams = field(default_factory=FactorParams)
    universe: UniverseParams = field(default_factory=UniverseParams)
    basket_k: int = 5                  # 최종 바스켓 종목 수
    capital: int = 100_000_000
