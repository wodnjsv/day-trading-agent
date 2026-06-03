"""parquet 캐시 유틸(종류별·날짜별 1파일)."""
from __future__ import annotations
from pathlib import Path
from typing import Callable
import pandas as pd


def cache_path(data_dir, kind: str, key: str) -> Path:
    return Path(data_dir) / kind / f"{key}.parquet"


def load_or_fetch(path: Path, fetch: Callable[[], pd.DataFrame]) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)
    df = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df
