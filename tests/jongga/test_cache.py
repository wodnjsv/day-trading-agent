import pandas as pd
from jongga.data.cache import cache_path, load_or_fetch


def test_cache_path_layout(tmp_path):
    assert cache_path(tmp_path, "daily", "2026-06-01") == tmp_path / "daily" / "2026-06-01.parquet"


def test_load_or_fetch_uses_cache_when_present(tmp_path):
    calls = {"n": 0}
    df = pd.DataFrame({"close": [100, 200]}, index=["A", "B"])

    def fetch():
        calls["n"] += 1
        return df

    p = cache_path(tmp_path, "daily", "2026-06-01")
    load_or_fetch(p, fetch)
    out = load_or_fetch(p, fetch)
    assert calls["n"] == 1
    assert list(out["close"]) == [100, 200]
