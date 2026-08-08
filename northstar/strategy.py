from __future__ import annotations

import pandas as pd

from northstar.models import Decision

EXIT_RULE = "Sell on stop, next open after a close below MA20, or after 20 sessions."


def add_indicators(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    close = frame["Close"]
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            frame["High"] - frame["Low"],
            (frame["High"] - previous_close).abs(),
            (frame["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    frame["MA20"] = close.rolling(20).mean()
    frame["MA50"] = close.rolling(50).mean()
    frame["MA200"] = close.rolling(200).mean()
    frame["ATR14"] = true_range.rolling(14).mean()
    frame["SwingLow10"] = frame["Low"].rolling(10).min()
    return frame


def evaluate(
    ticker: str,
    bars: pd.DataFrame,
) -> Decision:
    if len(bars) < 201:
        as_of = str(bars.index[-1].date()) if not bars.empty else "unknown"
        return Decision(
            ticker=ticker,
            as_of=as_of,
            signal="NO_DATA",
            close=None,
            reference_price=None,
            stop=None,
            target=None,
            score=0,
            reason=f"Need at least 201 daily bars; found {len(bars)}.",
            exit_rule=EXIT_RULE,
            valid_for="No order",
        )

    frame = add_indicators(bars)
    row = frame.iloc[-1]
    previous = frame.iloc[-2]
    close = float(row["Close"])
    atr = float(row["ATR14"])
    ma20 = float(row["MA20"])
    ma50 = float(row["MA50"])
    ma200 = float(row["MA200"])
    trend = close > ma50 > ma200
    near_ma20 = abs(close - ma20) <= atr
    confirmation = close > float(previous["High"])

    score = 0.0
    score += 45 if trend else 0
    score += 25 if near_ma20 else 0
    score += 20 if confirmation else 0
    score += 10 if close > ma20 else 0

    if trend and near_ma20 and confirmation:
        signal = "BUY"
        reason = "Uptrend intact; pullback is near MA20 and price confirmed above yesterday's high."
    elif trend and near_ma20:
        signal = "WATCH"
        reason = "Uptrend intact and price is near MA20; waiting for confirmation."
    else:
        signal = "AVOID"
        reason = "The trend-pullback entry conditions are not currently aligned."

    swing_stop = float(row["SwingLow10"]) - 0.1 * atr
    atr_stop = close - 2 * atr
    stop = max(swing_stop, atr_stop)
    stop = min(stop, close - 0.01)

    return Decision(
        ticker=ticker,
        as_of=str(frame.index[-1].date()),
        signal=signal,
        close=round(close, 2),
        reference_price=round(close, 2),
        stop=round(stop, 2),
        target=None,
        score=round(score, 1),
        reason=reason,
        exit_rule=EXIT_RULE,
        valid_for="Next session open" if signal == "BUY" else "No order",
    )
