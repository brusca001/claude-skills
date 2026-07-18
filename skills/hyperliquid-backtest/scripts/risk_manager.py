"""
Kelly Criterion position sizing, adapted from ai-contrarian-bot's risk_manager.py
(the full circuit-breaker/exposure-tracking machinery isn't needed here since this
skill is backtest-only — no live orders are ever placed).
"""

from typing import Optional


def kelly_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    bankroll: float,
    fraction: float = 0.5,
    max_size: Optional[float] = None,
) -> float:
    """
    Kelly formula: f* = (p * b - q) / b
        p = win probability, q = 1-p, b = avg_win / avg_loss

    fraction=0.5 (half-Kelly) is the standard safety discount.
    Returns 0.0 if the edge is negative or inputs are invalid.
    """
    if win_rate <= 0 or win_rate >= 1:
        return 0.0
    if avg_win <= 0 or avg_loss <= 0:
        return 0.0
    if bankroll <= 0:
        return 0.0

    p = win_rate
    q = 1.0 - p
    b = avg_win / avg_loss

    kelly_f = (p * b - q) / b
    if kelly_f <= 0:
        return 0.0

    size = bankroll * (kelly_f * fraction)
    if max_size:
        size = min(size, max_size)

    return round(size, 2)
