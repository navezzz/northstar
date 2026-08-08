# Strategy and backtest design

Northstar separates **what creates a signal** from **how a portfolio executes
it**. This lets each strategy use the same backtest, paper-account, and
dashboard pipeline.

## Responsibilities

```text
Strategy plug-in                         Shared replay engine
----------------                        --------------------
Universe                                Cash and positions
Indicators                              Next-session open fills
Entry intent and score                  Costs and fees
Initial stop / optional target           Risk/allocation limits
End-of-day exit condition               Trade ledger and equity curve
Description and execution metadata      SPY benchmark statistics
```

The shared engine is `northstar/backtest.py`. It must not contain conditions
specific to trend-pullback (such as moving-average exits). Strategy-specific
logic lives under `northstar/strategies/`.

## Strategy contract

A strategy subclasses `BaseStrategy` and provides:

- Stable `id`, display `name`, `version`, `description`, and `universe`.
- `prepare_bars`: calculate indicators from historical OHLCV data.
- `evaluate`: inspect data through the completed current bar and return a
  `Decision`. A `BUY` decision includes an initial stop but does not choose its
  fill price or portfolio size.
- `close_exit`: return an end-of-day exit reason, if any. The engine executes
  this at the following session's open.
- `execution_summary`: plain-language rules displayed by the frontend.

Strategies must avoid future data. The replay engine passes only history up to
the evaluation date to `evaluate`.

## Adding a strategy

1. Add a module under `northstar/strategies/` implementing `BaseStrategy`.
2. Register an instance in `northstar/strategies/registry.py`.
3. Add strategy-rule tests and run the common backtest tests.
4. Export a site snapshot. The dashboard reads the resulting `strategies[]`
   collection and creates its strategy selector without strategy-specific UI.

No changes should be necessary in the portfolio replay engine, API, or page for
a strategy that fits the existing decision contract. If a future strategy
needs a different order type or intraday execution, extend the execution
contract explicitly instead of embedding those assumptions in that strategy.

## Current execution assumptions

- A signal is calculated after the daily close without look-ahead.
- A buy executes at the next available session open.
- Configurable basis-point cost makes buys more expensive and sales cheaper.
- An optional fixed fee is deducted on every fill.
- A gap opening at or below the stop invalidates the entry.
- Position size is capped by risk budget, maximum allocation, available cash,
  and maximum concurrent positions.
- Protective stops may gap through their trigger. Same-day fill/stop ambiguity
  is handled conservatively.
- End-of-day strategy exits execute at the next available open.

These are research assumptions, not a promise that a live order would receive
the simulated fill.

## Relationship to Market Lens

Northstar follows Market Lens's useful high-level separation between strategy
logic and shared portfolio simulation, but it does not copy its fill model.
Market Lens supports several simulation paths and a more mature walk-forward
research process. Its primary daily engines generally execute a scanner's
signal price on the signal bar and then apply costs.

Northstar instead models the V0 workflow directly: calculate after today's
close and execute at tomorrow's available open. Current Northstar defaults use
10 bps of modeled transaction cost and no per-order commission; the comparable
Market Lens walk-forward configuration uses 10 bps and a $1 fee. Market Lens also has parameter-grid walk-forward
evaluation, richer regime and sector controls, fractional shares, partial exits,
and long/short support. Those are possible later phases, not claims of the MVP.
