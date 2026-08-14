from __future__ import annotations

from datetime import UTC, datetime, timedelta

from northstar.data.normalization import normalize_yahoo_history
from northstar.data.schema import MarketDataBundle


class YahooDataProvider:
    name = "yahoo"

    def fetch_daily(self, symbol: str, *, years: int = 10) -> MarketDataBundle:
        import yfinance as yf

        end = datetime.now(UTC).date() + timedelta(days=1)
        start = end - timedelta(days=365 * years + 20)
        history = yf.Ticker(symbol).history(
            start=start.isoformat(),
            end=end.isoformat(),
            auto_adjust=False,
            actions=True,
            repair=False,
        )
        return normalize_yahoo_history(symbol, history)
