from __future__ import annotations

from northstar.strategies.base import BaseStrategy
from northstar.strategies.trend_pullback import TrendPullbackV1


def strategy_registry() -> tuple[BaseStrategy, ...]:
    """Return fresh strategy instances registered for dashboard analysis."""
    return (TrendPullbackV1(),)
