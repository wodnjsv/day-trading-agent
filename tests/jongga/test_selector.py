import pandas as pd
from jongga.selector import score_and_select


def test_score_select_topk_with_normalized_conviction():
    feats = pd.DataFrame({
        "spread": [0.9, 0.1, 0.5],
        "supply": [0.8, 0.2, 0.5],
        "days_since_high": [0, 30, 5],   # 작을수록 좋음(패널티)
    }, index=["A", "B", "C"])
    weights = {"spread": 1.0, "supply": 1.0}
    picks = score_and_select(feats, weights, dsh_penalty=0.01, k=2)
    assert [p[0] for p in picks] == ["A", "C"]        # A 최고
    assert 0.0 <= picks[1][1] <= picks[0][1] <= 1.0   # conviction 0~1, 정렬
