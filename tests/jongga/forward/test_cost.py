from jongga.forward.cost import overnight_net, SELL_TAX, FEE, SLIP_BANDS


def test_overnight_net_subtracts_costs():
    net = overnight_net(entry=1000, exit_px=1100, slippage=0.0)
    assert abs(net - (0.10 - SELL_TAX - 2 * FEE)) < 1e-12


def test_overnight_net_slippage_band():
    net0 = overnight_net(1000, 1100, 0.0)
    net1 = overnight_net(1000, 1100, 0.001)
    assert abs((net0 - net1) - 2 * 0.001) < 1e-12


def test_slip_bands_default():
    assert SLIP_BANDS == (0.0, 0.0005, 0.001)
