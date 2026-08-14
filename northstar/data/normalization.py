from __future__ import annotations

import numpy as np
import pandas as pd

from northstar.data.schema import ACTION_COLUMNS, BAR_COLUMNS, RAW_COLUMNS, MarketDataBundle


def _date_index(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    index = pd.to_datetime(result.index)
    if index.tz is not None:
        index = index.tz_convert("America/New_York").tz_localize(None)
    result.index = index.normalize()
    result.index.name = "Date"
    return result[~result.index.duplicated(keep="last")].sort_index()


def normalize_yahoo_history(symbol: str, history: pd.DataFrame) -> MarketDataBundle:
    """Preserve Yahoo facts and derive split/dividend-adjusted strategy bars."""
    source = _date_index(history)
    rename = {"Adj Close": "AdjClose", "Dividends": "Dividend", "Stock Splits": "Split"}
    source = source.rename(columns=rename)
    for column in (*RAW_COLUMNS, *ACTION_COLUMNS):
        if column not in source:
            source[column] = 0.0 if column in ACTION_COLUMNS else np.nan

    raw = source.loc[:, RAW_COLUMNS].apply(pd.to_numeric, errors="coerce")
    actions = source.loc[:, ACTION_COLUMNS].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    actions = actions[(actions != 0).any(axis=1)]

    factor = raw["AdjClose"] / raw["Close"].replace(0, np.nan)
    bars = pd.DataFrame(index=raw.index)
    for column in ("Open", "High", "Low", "Close"):
        bars[column] = raw[column] * factor
    bars["Volume"] = raw["Volume"]
    bars = bars.loc[:, BAR_COLUMNS].dropna(subset=["Open", "High", "Low", "Close"])
    return MarketDataBundle.create(
        symbol=symbol,
        provider="yahoo",
        raw=raw,
        bars=bars,
        actions=actions,
    )
