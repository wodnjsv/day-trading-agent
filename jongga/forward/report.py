"""A/B 리포트: paired(day-level)·게이트분해·겹침도. 검정은 day 단위(유효 N=거래일수)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats


def paired_by_day(rows: list[dict], band: str = "net_s0") -> dict:
    """LLM 매매일 한정 day-level paired: day별 (llm 평균 − baseline 평균) net."""
    df = pd.DataFrame(rows)
    days = []
    for d, g in df.groupby("run_date"):
        llm = g[g["source"] == "llm"][band]
        base = g[g["source"] == "baseline"][band]
        if len(llm) == 0:
            continue
        days.append((float(llm.mean()), float(base.mean()) if len(base) else np.nan))
    if not days:
        return {"n_days": 0, "mean_diff": float("nan"), "llm_mean": float("nan"), "p_rel": 1.0}
    llm_d = np.array([x[0] for x in days])
    base_d = np.array([x[1] for x in days])
    diff = llm_d - base_d
    p = stats.ttest_1samp(diff, 0.0).pvalue if len(diff) >= 2 else 1.0
    return {"n_days": len(days), "mean_diff": float(np.nanmean(diff)),
            "llm_mean": float(llm_d.mean()), "p_rel": float(p)}


def overlap_jaccard(llm_tickers: list[str], baseline_tickers: list[str]) -> float:
    a, b = set(llm_tickers), set(baseline_tickers)
    u = a | b
    return len(a & b) / len(u) if u else 0.0
