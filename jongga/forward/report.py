"""A/B 리포트: paired(day-level)·게이트분해·겹침도. 검정은 day 단위(유효 N=거래일수)."""
from __future__ import annotations
import re
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
    diff = diff[~np.isnan(diff)]
    p = stats.ttest_1samp(diff, 0.0).pvalue if len(diff) >= 2 else 1.0
    return {"n_days": len(days), "mean_diff": float(np.nanmean(diff)),
            "llm_mean": float(llm_d.mean()), "p_rel": float(p)}


def paired_pooled(rows: list[dict], band: str = "net_s05") -> dict:
    """1차(사전등록) 추정량: (거래일×시장) 단위 diff(llm평균 − baseline평균)를 한 표본으로 결합한 paired t.
    시장별이 아니라 market-day 단위를 풀링(시장 구성 고정). 반환 n_units/mean_diff/p."""
    df = pd.DataFrame(rows)
    if df.empty:
        return {"n_units": 0, "mean_diff": float("nan"), "p": 1.0}
    diffs = []
    for (_d, _mkt), g in df.groupby(["run_date", "market"]):
        llm = g[g["source"] == "llm"][band]
        base = g[g["source"] == "baseline"][band]
        if len(llm) == 0 or len(base) == 0:
            continue
        diffs.append(float(llm.mean()) - float(base.mean()))
    diffs = [x for x in diffs if pd.notna(x)]
    if len(diffs) < 2:
        return {"n_units": len(diffs),
                "mean_diff": float(diffs[0]) if diffs else float("nan"), "p": 1.0}
    arr = np.array(diffs)
    return {"n_units": len(arr), "mean_diff": float(arr.mean()),
            "p": float(stats.ttest_1samp(arr, 0.0).pvalue)}


def filter_pre_close(rows: list[dict], cutoff_hhmm: str = "15:20") -> tuple[list[dict], float]:
    """LLM 픽 중 catalyst_timestamp 시각이 cutoff 초과(또는 미파싱)면 제외(누수 방지·보수).
    baseline 행은 통과. 반환: (남은 rows, 제외된 llm 비율)."""
    ch, cm = (int(x) for x in cutoff_hhmm.split(":"))
    kept, n_llm, n_excl = [], 0, 0
    for r in rows:
        if r.get("source") != "llm":
            kept.append(r)
            continue
        n_llm += 1
        m = re.search(r"(\d{1,2}):(\d{2})", str(r.get("catalyst_timestamp") or ""))
        if m and (int(m.group(1)), int(m.group(2))) <= (ch, cm):
            kept.append(r)
        else:
            n_excl += 1   # >15:20 또는 시각 미파싱 → 보수적 제외
    return kept, (n_excl / n_llm if n_llm else 0.0)


def overlap_jaccard(llm_tickers: list[str], baseline_tickers: list[str]) -> float:
    a, b = set(llm_tickers), set(baseline_tickers)
    u = a | b
    return len(a & b) / len(u) if u else 0.0
