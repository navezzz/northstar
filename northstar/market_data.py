from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class MarketDataProvider(ABC):
    @abstractmethod
    def daily_bars(self, ticker: str, years: int = 6) -> pd.DataFrame:
        """Return ascending OHLCV bars indexed by date."""


class YahooFinanceProvider(MarketDataProvider):
    def daily_bars(self, ticker: str, years: int = 6) -> pd.DataFrame:
        from northstar.data.provider import YahooDataProvider

        return YahooDataProvider().fetch_daily(ticker, years=years).bars
