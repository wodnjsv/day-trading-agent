from jongga.forward.report import paired_by_day, overlap_jaccard


def test_paired_by_day_relative_gate():
    rows = [
        {"run_date": "d1", "source": "llm", "net_s0": 0.02},
        {"run_date": "d1", "source": "baseline", "net_s0": 0.00},
        {"run_date": "d2", "source": "llm", "net_s0": -0.01},
        {"run_date": "d2", "source": "baseline", "net_s0": 0.00},
    ]
    res = paired_by_day(rows, band="net_s0")
    assert abs(res["mean_diff"] - 0.005) < 1e-9
    assert res["n_days"] == 2
    assert abs(res["llm_mean"] - 0.005) < 1e-9


def test_overlap_jaccard():
    assert abs(overlap_jaccard(["A", "B", "C"], ["B", "C", "D"]) - (2 / 4)) < 1e-9


def test_paired_pooled_combines_market_days():
    from jongga.forward.report import paired_pooled
    rows = [
        {"run_date": "d1", "market": "KOSPI", "source": "llm", "net_s05": 0.02},
        {"run_date": "d1", "market": "KOSPI", "source": "baseline", "net_s05": 0.00},
        {"run_date": "d1", "market": "KOSDAQ", "source": "llm", "net_s05": 0.00},
        {"run_date": "d1", "market": "KOSDAQ", "source": "baseline", "net_s05": 0.01},
    ]
    res = paired_pooled(rows, band="net_s05")
    # 두 market-day diff: KOSPI +0.02, KOSDAQ -0.01 → 2 units, 평균 +0.005
    assert res["n_units"] == 2
    assert abs(res["mean_diff"] - 0.005) < 1e-9


def test_filter_pre_close():
    from jongga.forward.report import filter_pre_close
    rows = [
        {"source": "llm", "catalyst_timestamp": "2026-06-05T13:10"},   # 유지
        {"source": "llm", "catalyst_timestamp": "2026-06-05T16:30"},   # 제외(>15:20)
        {"source": "llm", "catalyst_timestamp": ""},                    # 제외(미파싱)
        {"source": "baseline", "catalyst_timestamp": ""},               # 유지(baseline)
    ]
    kept, frac = filter_pre_close(rows)
    assert len(kept) == 2                       # llm 13:10 + baseline
    assert abs(frac - 2 / 3) < 1e-9             # llm 3개 중 2개 제외
