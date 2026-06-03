from jongga.regime import regime_multiplier


def test_regime_thresholds_trillion_won():
    # 코스닥 일거래대금(원). 사전등록: BULL≥12조, BEAR<8조, HALT<5조
    assert regime_multiplier(13e12) == ("BULL", 1.0)
    assert regime_multiplier(10e12) == ("NEUTRAL", 0.5)
    assert regime_multiplier(7e12) == ("BEAR", 0.2)
    assert regime_multiplier(4e12) == ("HALT", 0.0)
