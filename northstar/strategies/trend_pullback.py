from __future__ import annotations

import pandas as pd

from northstar.models import Decision
from northstar.strategies.base import BaseStrategy
from northstar.strategy import add_indicators, evaluate


class TrendPullbackV1(BaseStrategy):
    id = "trend_pullback_v1"
    name = "Trend Pullback"
    version = "1.0"
    description = (
        "Magnificent Seven uptrends pulling back near MA20, with next-open "
        "entries and predefined invalidation."
    )
    universe = ("AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA")

    def prepare_bars(self, bars: pd.DataFrame) -> pd.DataFrame:
        return add_indicators(bars.sort_index())

    def evaluate(
        self,
        ticker: str,
        prepared_bars: pd.DataFrame,
    ) -> Decision:
        return evaluate(ticker, prepared_bars)

    def close_exit(
        self,
        ticker: str,
        prepared_bars: pd.DataFrame,
        as_of_date: pd.Timestamp,
        held_sessions: int,
    ) -> str | None:
        del ticker
        if as_of_date not in prepared_bars.index:
            return None
        row = prepared_bars.loc[as_of_date]
        if pd.notna(row["MA20"]) and float(row["Close"]) < float(row["MA20"]):
            return "MA20_BREAK"
        if held_sessions >= 20:
            return "TIME_EXIT"
        return None

    @property
    def execution_summary(self) -> dict:
        return {
            "entry": "Next-session open with modeled transaction costs",
            "signal_expiry": "Next available trading session",
            "exits": "Initial stop, next open after MA20 breakdown, or 20-session timeout",
        }
