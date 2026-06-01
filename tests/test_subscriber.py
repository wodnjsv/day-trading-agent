from manju.collector.subscriber import plan_changes


def test_initial_registration_respects_limit():
    # 한도 4건 = 종목 2개 (종목당 체결+호가 2건)
    to_reg, to_unreg, active = plan_changes(
        current=set(), desired=["A", "B", "C"], max_reg=4)
    assert active == ["A", "B"]                       # 한도 내 상위 2종목만
    assert set(to_reg) == {("H0STCNT0", "A"), ("H0STASP0", "A"),
                           ("H0STCNT0", "B"), ("H0STASP0", "B")}
    assert to_unreg == []


def test_rotation_unregisters_dropped_and_registers_new():
    to_reg, to_unreg, active = plan_changes(
        current={"A", "B"}, desired=["B", "C"], max_reg=4)
    assert set(active) == {"B", "C"}
    assert set(to_unreg) == {("H0STCNT0", "A"), ("H0STASP0", "A")}
    assert set(to_reg) == {("H0STCNT0", "C"), ("H0STASP0", "C")}


def test_no_change_when_universe_stable():
    to_reg, to_unreg, active = plan_changes(
        current={"A", "B"}, desired=["A", "B"], max_reg=10)
    assert to_reg == [] and to_unreg == []
    assert set(active) == {"A", "B"}
