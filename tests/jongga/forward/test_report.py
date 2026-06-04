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
