# Northstar MVP

## Product goal

Northstar turns completed daily candles into an explainable decision card:
signal, entry range, invalidation price, risk per share, position-size ceiling,
and exit rule. It is decision support, not a prediction engine or broker.

## First strategy: daily trend pullback

A ticker is in an established uptrend when `close > MA50 > MA200`. It becomes a
watch candidate when price is within one ATR of MA20. A buy setup additionally
requires the latest close to exceed the previous day's high.

The displayed entry range spans MA20/current-price context plus or minus a
quarter ATR. The stop uses the tighter of a two-ATR stop and a ten-session swing
low with a small ATR buffer. Position size is:

`floor(portfolio value × configured risk fraction / risk per share)`

Signals use only completed bars. A daily signal is intended for evaluation at
the next session, avoiding same-close look-ahead assumptions.

## Architecture

```text
Yahoo provider → daily pipeline → strategy → atomic SQLite run
                                             ↓
Browser dashboard ← FastAPI latest-run endpoint
```

Market data, strategy evaluation, persistence, API, and UI are separate modules.
This permits replacing Yahoo, adding strategies, or moving from SQLite later.

## Non-goals

- Real-money or automated order placement
- Intraday signals
- Price targets presented as guaranteed outcomes
- Machine learning before the baseline is validated
- Personalized suitability or portfolio advice

## Next milestones

1. Persist OHLCV locally and validate data freshness.
2. Add a realistic next-open backtester with slippage.
3. Add paper positions and daily sell checks.
4. Add exchange-calendar-aware scheduling.
5. Compare the strategy against buy-and-hold SPY out of sample.
