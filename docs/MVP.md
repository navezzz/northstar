# Northstar MVP

## Product goal

Northstar turns completed daily candles into an explainable next-session plan:
signal, reference close, invalidation price, and exit rule. The portfolio
engine—not the strategy—calculates position size from the eventual execution
price. It is decision support, not a prediction engine or broker.

## First strategy: daily trend pullback

A ticker is in an established uptrend when `close > MA50 > MA200`. It becomes a
watch candidate when price is within one ATR of MA20. A buy setup additionally
requires the latest close to exceed the previous day's high.

The stop uses the tighter of a two-ATR stop and a ten-session swing low with a
small ATR buffer. Position size is capped by both the risk budget and portfolio allocation.
The risk-based ceiling is:

`floor(portfolio value × configured risk fraction / risk per share)`

Signals use only completed bars. A buy signal executes at the next available
session open plus modeled transaction costs, avoiding same-close look-ahead.
The initial strategy universe is AAPL, MSFT, NVDA, AMZN, META, GOOGL, and TSLA.

The historical replay starts with $10,000 and compares the strategy equity with
buy-and-hold SPY. A separate paper replay keeps positions open as of the latest
bar. See [STRATEGIES.md](STRATEGIES.md) for fill assumptions and the plug-in
contract.

## Architecture

```text
Yahoo provider → strategy registry → shared replay engine → snapshot
                                                        ↓
Browser dashboard ← static Pages data or FastAPI latest-snapshot endpoint
```

Market data, strategy evaluation, portfolio replay, persistence, API, and UI are
separate modules. The snapshot contains a `strategies[]` collection, so new
registered strategies appear in the strategy selector without a separate page.

## Non-goals

- Real-money or automated order placement
- Intraday signals
- Price targets presented as guaranteed outcomes
- Machine learning before the baseline is validated
- Personalized suitability or portfolio advice

## Next milestones

1. Validate the baseline across multiple market regimes and an out-of-sample
   period.
2. Persist OHLCV locally and validate data freshness.
3. Add exchange-calendar-aware scheduling.
4. Persist paper-account state rather than reconstructing it from historical
   bars on every run.
5. Add a second strategy through the documented plug-in contract.
