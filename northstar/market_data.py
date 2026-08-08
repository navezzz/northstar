from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

import pandas as pd


class MarketDataProvider(ABC):
    @abstractmethod
    def daily_bars(self, ticker: str, years: int = 6) -> pd.DataFrame:
        """Return ascending OHLCV bars indexed by date."""


class YahooFinanceProvider(MarketDataProvider):
    def daily_bars(self, ticker: str, years: int = 6) -> pd.DataFrame:
        import yfinance as yf

        end = datetime.now(UTC).date() + timedelta(days=1)
        start = end - timedelta(days=365 * years + 10)
        frame = yf.download(
            ticker,
            start=start.isoformat(),
            end=end.isoformat(),
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)
        required = ["Open", "High", "Low", "Close", "Volume"]
        if frame.empty or any(column not in frame for column in required):
            return pd.DataFrame(columns=required)
        result = frame[required].dropna(subset=["Open", "High", "Low", "Close"]).copy()
        result.index = pd.to_datetime(result.index).tz_localize(None)
        return result.sort_index()
