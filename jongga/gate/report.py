# jongga/gate/report.py
"""§8.4 사전등록 합격선 판정(C3: 1순위 실패=baseline 붕괴, 전략 전체 중단 아님)."""
from __future__ import annotations


def verdict(n_sig_factors: int, sign_stable: bool,
            net_mean_conservative: float, mdd: float, n: int,
            theta1: float, theta2: float, thresholds: dict) -> dict:
    g1 = (n_sig_factors >= thresholds["m"]) and sign_stable
    g2 = (net_mean_conservative > 0) and (mdd >= thresholds["mdd_limit"]) \
        and (n >= thresholds["min_n"])
    g3_warn = (theta1 > thresholds["theta1_max"]) or (theta2 > thresholds["theta2_max"])
    if not g1:
        overall = "BASELINE_COLLAPSE"        # §8.5/C3: LLM A/B는 별도(이 계획 밖)
    elif g1 and g2:
        overall = "PASS"
    else:
        overall = "FAIL"
    return {"gate1_pass": g1, "gate2_pass": g2, "gate3_warn": g3_warn, "overall": overall}
