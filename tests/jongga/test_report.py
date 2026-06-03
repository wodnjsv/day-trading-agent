from jongga.gate.report import verdict


def test_verdict_pass_when_criteria_met():
    v = verdict(
        n_sig_factors=2, sign_stable=True,            # 1순위
        net_mean_conservative=0.004, mdd=-0.15, n=300,  # 2순위
        theta1=0.2, theta2=0.1,                        # 3순위
        thresholds={"m": 2, "mdd_limit": -0.25, "min_n": 250,
                    "theta1_max": 0.30, "theta2_max": 0.20},
    )
    assert v["gate1_pass"] is True
    assert v["gate2_pass"] is True
    assert v["gate3_warn"] is False
    assert v["overall"] == "PASS"


def test_verdict_gate1_fail_is_baseline_collapse():
    v = verdict(n_sig_factors=0, sign_stable=False,
               net_mean_conservative=0.01, mdd=-0.1, n=300,
               theta1=0.1, theta2=0.1,
               thresholds={"m": 2, "mdd_limit": -0.25, "min_n": 250,
                           "theta1_max": 0.30, "theta2_max": 0.20})
    assert v["gate1_pass"] is False
    assert v["overall"] == "BASELINE_COLLAPSE"   # 전략 전체 중단 아님(§8.5/C3)
