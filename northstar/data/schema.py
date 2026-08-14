from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd

SCHEMA_VERSION = 1
RAW_COLUMNS = ("Open", "High", "Low", "Close", "AdjClose", "Volume")
BAR_COLUMNS = ("Open", "High", "Low", "Close", "Volume")
ACTION_COLUMNS = ("Dividend", "Split")


@dataclass(frozen=True, slots=True)
class MarketDataBundle:
    symbol: str
    provider: str
    raw: pd.DataFrame
    bars: pd.DataFrame
    actions: pd.DataFrame
    fetched_at: str

    @classmethod
    def create(
        cls,
        *,
        symbol: str,
        provider: str,
        raw: pd.DataFrame,
        bars: pd.DataFrame,
        actions: pd.DataFrame,
    ) -> MarketDataBundle:
        return cls(
            symbol=symbol.upper(),
            provider=provider,
            raw=raw,
            bars=bars,
            actions=actions,
            fetched_at=datetime.now(UTC).isoformat(),
        )
