from __future__ import annotations

import math

import pandas as pd

from northstar.market_data import MarketDataProvider


class DemoProvider(MarketDataProvider):
    """Deterministic bars for UI development without network access."""

    def daily_bars(self, ticker: str, years: int = 6) -> pd.DataFrame:
        dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=1500)
        phase = sum(ord(char) for char in ticker) % 17
        closes = [80 + i * 0.035 + math.sin((i + phase) / 8) * 2.4 for i in range(1500)]
        frame = pd.DataFrame(index=dates)
        frame["Close"] = closes
        frame["Open"] = frame["Close"].shift(1).fillna(frame["Close"]) * 0.998
        frame["High"] = frame[["Open", "Close"]].max(axis=1) + 1.1
        frame["Low"] = frame[["Open", "Close"]].min(axis=1) - 1.1
        frame["Volume"] = 1_000_000 + phase * 10_000
        return frame[["Open", "High", "Low", "Close", "Volume"]]
