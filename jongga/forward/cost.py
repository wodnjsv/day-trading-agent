"""오버나잇 net 비용 모델. 매도세는 현행 실세율(2026, [사용자 확정])."""
from __future__ import annotations

SELL_TAX = 0.0020
FEE = 0.00014
SLIP_BANDS = (0.0, 0.0005, 0.001)


def overnight_net(entry: float, exit_px: float, slippage: float) -> float:
    """진입가→청산가 오버나잇 net 수익률. 매도세+수수료(왕복)+슬리피지(왕복) 차감."""
    gross = (exit_px - entry) / entry
    return gross - SELL_TAX - 2 * FEE - 2 * slippage
