# Northstar V0 platform vision

Status: **Canonical product direction**  
Created: 2026-08-08  
Scope: V0 foundation and first end-to-end strategy

This document preserves the product and engineering direction for Northstar.
Detailed component designs may refine implementation choices, but changes to
the goals, trust model, or scope described here should be recorded explicitly
rather than silently drifting in code.

Related documents:

- [Loop-engineering playbook](LOOP_ENGINEERING_PLAYBOOK.md)
- [Market-data foundation](MARKET_DATA_FOUNDATION.md)
- [Research foundation](RESEARCH_FOUNDATION.md)
- [Strategy and backtest design](../STRATEGIES.md)
- [MVP implementation notes](../MVP.md)
- [Operations](../OPERATIONS.md)
- [Deployment](../DEPLOYMENT.md)

## 1. Overview

Northstar is a platform for developing, backtesting, verifying, publishing, and
tracking systematic stock-trading strategies.

V0 starts with one internally developed, long-only daily strategy. Its purpose
is to establish trustworthy infrastructure before adding more strategies or a
marketplace:

1. Backtest a strategy realistically.
2. Evaluate whether historical performance is robust.
3. Run the same strategy on newly arriving market data.
4. Publish actionable next-session signals.
5. Preserve signal history and measure prospective paper performance.
6. Eventually allow users to subscribe to the strategy.

The platform provides research and decision support. V0 does not place
real-money trades for users.

## 2. Product vision

A user should be able to:

- Discover a systematic strategy.
- Understand its rules and expected behavior.
- Inspect platform-generated backtest and risk statistics.
- Distinguish historical backtest, walk-forward OOS, and prospective live-paper
  performance.
- Inspect every published signal, including losing trades.
- Subscribe to future signals when subscriptions are introduced.

Example strategy summary:

```text
Quality Momentum

Style: Momentum
Universe: U.S. large/mid-cap equities
Typical holding period: 5–20 trading days
Benchmark: SPY

Backtest CAGR: 16.4%
Backtest Sharpe: 1.25
Backtest max drawdown: -18.2%
Walk-forward OOS Sharpe: 1.08
Live since: Aug 2026
```

Example V0 signal:

```text
NEW SIGNAL — AMZN

Action: BUY at next session open
Signal close: $206
Stop: $197
Optional target: $226
Valid for: next trading session
Expected holding period: 5–15 trading days
```

The displayed next open is unknown when the signal is published. Position size
is calculated by the portfolio engine after the modeled execution price is
known.

## 3. V0 scope

### In scope

Strategy:

- One first-party strategy.
- Daily signals using completed U.S. market data.
- Long-only equities.
- Deterministic entry and exit rules.
- Standardized portfolio sizing for evaluation.

Backtesting and evaluation:

- Historical daily OHLCV.
- Point-in-time universe where the available data supports it.
- Explicit warnings when universe data is not point-in-time.
- Transaction-cost assumptions.
- Chronological portfolio accounting.
- Walk-forward out-of-sample evaluation.
- Parameter and cost robustness checks.
- SPY comparison and complete trade history.
- Reproducible run and dataset manifests.

Live-paper system:

- Scheduled market-data refresh after the close.
- The same strategy implementation used in historical and daily paths.
- Immutable published signals.
- Stateful signal lifecycle.
- Persistent paper portfolio.
- Prospective live-paper performance.
- Fail-closed publication of complete daily runs.

Product:

- Strategy overview and documented rules.
- Separate backtest, OOS, and live-paper results.
- Current signal feed.
- Complete historical signals and trades.
- Subscribe/unsubscribe and notifications in a later V0 product increment,
  after a persistent backend exists.

### Out of scope

- Real-money brokerage integration.
- Automatic execution or copy trading.
- Options and short selling.
- Intraday strategies.
- Limit-order fill simulation.
- Machine-learning stock prediction.
- Third-party strategy creators or marketplace.
- Personalized investment suitability advice.

An external broker-paper integration such as Alpaca may later serve as an
additional comparison, but it does not replace Northstar's standardized
live-paper record.

## 4. Core principles

### One strategy implementation

The same versioned strategy code must generate historical and prospective
signals. Backtest-only strategy branches are not allowed.

### Strict time boundaries

A strategy evaluating date T may access only information known at or before
the completed T close. A signal generated after that close cannot execute at
the same close.

### Separation of responsibility

```text
Strategy: what the system wants to trade
Execution: when and at what modeled price it fills
Portfolio: whether it fits and how many shares to hold
Evaluation: how results are measured and verified
Publishing: what users were told and when
```

### Reproducibility

Every material result must identify:

- Strategy ID and version.
- Strategy parameters.
- Code revision.
- Dataset snapshot.
- Universe definition/version.
- Evaluation dates.
- Execution costs.
- Portfolio assumptions.

### Prospective truth is immutable

Published historical signals are never rewritten to match later strategy
logic. A changed strategy becomes a new version.

### Honest limitations

A profitable result is not automatically verified. Missing point-in-time data,
possible survivorship bias, limited trade count, or untested execution costs
must remain visible.

## 5. High-level architecture

```text
Market data
    ↓
Point-in-time universe
    ↓
Data validation and feature pipeline
    ↓
Versioned strategy engine
    ↓
Execution and portfolio engine
    ↓
Backtest / walk-forward / robustness evaluation
    ↓
Immutable signal and performance store
    ↓
API / static export / notifications
    ↓
User product
```

V0 is a modular monolith. These are code and ownership boundaries, not separate
microservices.

## 6. Market-data layer

Canonical daily bars contain:

```text
ticker
date
open
high
low
close
adjusted_close or explicit adjustment policy
volume
```

Symbol metadata should eventually contain:

```text
ticker
company
security type
exchange
sector
industry
market cap
listing date
delisting date
```

Required qualities:

- Ascending, unique trading dates.
- Consistent timezone and session definition.
- Explicit corporate-action adjustment policy.
- Provider and retrieval metadata.
- Dataset fingerprints and preserved snapshots.
- Structural, staleness, calendar-coverage, and discontinuity checks.

Yahoo data is acceptable for early prototyping. It is not sufficient evidence
for a survivorship-bias-free ten-year broad-universe claim without additional
historical universe and delisting data.

## 7. Universe construction

The intended interface is point-in-time:

```python
universe = universe_provider.get_universe(as_of=date_t)
```

Illustrative eligibility rules:

```text
U.S.-listed common stock
Price > $5
Market cap > $1B
20-day average dollar volume > $10M
Trading history >= 252 sessions
```

Every rule must use only information available at that historical date.

During bootstrap, a fixed universe may be used if the result is labeled with a
survivorship-bias limitation. It cannot pass the point-in-time verification
gate.

## 8. Feature pipeline

Shared initial features may include:

```text
return_5d
return_20d
return_60d
ma_20
ma_50
ma_200
volatility_20d
average_volume_20d
average_dollar_volume_20d
```

Features are computed as of a requested date using no future values:

```python
features = feature_pipeline.compute(
    as_of=date_t,
    universe=universe,
    market_data=data,
)
```

Feature tests must demonstrate that adding future rows cannot change a feature
or signal for an earlier date.

## 9. Strategy contract

A strategy receives an immutable view of its date, features, universe, and
portfolio. It returns desired actions, not simulated fills.

Conceptually:

```python
class Strategy:
    identity: StrategyIdentity
    parameters: Mapping[str, object]

    def generate_signals(self, context: StrategyContext) -> list[SignalIntent]: ...
```

An intent may contain:

```text
ticker
action: BUY / EXIT / HOLD
score
stop price
optional target price
valid-until date
reason codes
```

It does not contain an assumed fill or mutate portfolio state.

## 10. Initial strategy

The first V0 strategy should remain simple enough to audit. The candidate is a
momentum-plus-trend strategy over liquid U.S. large/mid-cap equities.

Illustrative initial logic:

```text
Eligibility:
  price, liquidity, history, and security-type gates

Trend filter:
  close > MA50

Rank:
  60-day momentum, potentially adjusted by 20-day volatility

Select:
  top-ranked candidates not already held

Exit:
  deterministic trend, stop, target, or time rule
```

The precise hypothesis and rules must be documented and versioned before final
evaluation. The objective is to validate the platform, not maximize historical
Sharpe.

The existing Magnificent Seven trend-pullback strategy is transitional research
and does not automatically become the canonical V0 Strategy #1.

## 11. Execution model

V0 standardizes next-open execution:

```text
Day T close completes
    ↓
Strategy publishes signal
    ↓
Day T+1 open
    ↓
Execution policy produces modeled fill
```

For a long position:

```text
buy fill  = next open × (1 + cost_bps / 10,000)
sell fill = next open × (1 - cost_bps / 10,000)
```

Initial default:

```text
Modeled transaction cost: 10 bps per transaction
Fixed fee: $0, configurable
```

Robustness evaluation should include at least 5, 10, 20, and 30 bps.

Daily OHLCV limit simulation is excluded because it cannot establish queue
position or realistic fill probability. Protective-stop tests must define gap
and same-bar ambiguity conservatively.

## 12. Portfolio engine

Initial standardized assumptions:

```text
Starting capital: $10,000
Risk per trade: 1%
Maximum positions: initially configurable; target V0 baseline 10
Maximum position size: target V0 baseline 15%
Long-only
Integer shares
No leverage
```

Portfolio state contains:

```text
cash
positions
portfolio value
realized P&L
unrealized P&L
fees
```

Daily accounting must reconcile:

```text
equity = cash + Σ(shares × current close)
```

Position size is determined after execution price is known and is capped by
risk, allocation, cash, and position-count constraints.

## 13. Backtest engine

The backtester proceeds chronologically:

```text
For each session T:
  execute intents created after T-1 close at T open
  process modeled risk events
  update cash and positions
  mark the portfolio to T close
  build the point-in-time T universe
  compute features available through T
  ask the strategy for new intents
  persist orders, fills, trades, and portfolio state
```

The engine must not expose future rows to the strategy. Backtest output includes
the complete ledger, not only summary statistics.

## 14. Evaluation metrics

Returns:

- Total return.
- CAGR.
- Monthly and yearly returns.

Risk:

- Annualized volatility.
- Sharpe and, where useful, Sortino ratio.
- Maximum drawdown.

Trading behavior:

- Trade count and win rate.
- Average winner and loser.
- Average holding period.
- Turnover.
- Fees and modeled execution cost.

Benchmark comparison:

```text
Strategy and SPY CAGR
Strategy and SPY volatility
Strategy and SPY Sharpe
Strategy and SPY maximum drawdown
```

Later versions may add factor attribution, alpha, and beta.

## 15. Experiments and hyperparameters

Experiments are first-class, auditable objects:

```text
Written hypothesis
Declared parameter space
Maximum trial count
Selection metric
Dataset and windows
Every attempted result
Decision and rationale
```

The architecture separates:

```text
ExperimentSpec       declares the hypothesis and candidates
TrialRunner          executes every declared candidate
WalkForwardEvaluator selects without seeing OOS
RobustnessEvaluator  tests neighboring values, periods, costs, and universes
```

An unrestricted full-history `best_params()` workflow is intentionally not a
foundation feature.

## 16. Overfitting protection

Financial time series are never randomly shuffled.

Each walk-forward fold contains chronological training, validation, and unseen
OOS windows. Parameters are frozen before the OOS window is evaluated. Only OOS
returns are concatenated into the reported walk-forward track record.

Reports should show parameter surfaces, not merely the best point. A stable
region such as 40/50/60/70-day momentum behaving similarly is more credible
than one isolated winning value.

The research log records:

```text
hypothesis
reason for experiment
parameters tried
data and windows
all results
decision
```

## 17. Verification

A strategy is not verified solely because it is profitable.

Potential gates:

```text
No known look-ahead bias
Point-in-time universe
Data-quality checks passed
Transaction costs included
Walk-forward OOS evaluation complete
Parameter robustness acceptable
Minimum trade count met
Cost stress acceptable
Complete trade history available
Run reproducible from recorded inputs
```

Each gate reports `PASS`, `FAIL`, `LIMITED`, or `NOT_TESTED`. The overall status
remains `RESEARCH` until required gates pass.

## 18. Signal lifecycle

Published signals are stateful and immutable:

```text
CREATED
   ↓
ACTIVE
   ├──→ EXPIRED
   ↓
FILLED
   ↓
HOLD
   ↓
EXIT_CREATED
   ↓
EXITED
```

Every transition is stored as an event. Corrections are additional events, not
in-place historical edits.

Core fields eventually include:

```text
signal ID
strategy ID and version
ticker
created timestamp
action and reason
signal close
stop and optional target
valid-until timestamp
status
modeled fill timestamp and price
exit timestamp and price
return and P&L
```

## 19. Daily live-paper runner

The same versioned strategy runs after finalized daily data is available:

```text
Market closes
    ↓
Data refresh and validation
    ↓
Feature pipeline
    ↓
Strategy intents
    ↓
Atomic signal publication
    ↓
Next-session modeled execution
    ↓
Position and lifecycle updates
```

The runner must be:

- Idempotent for a strategy/version/session.
- Fail-closed when required data or steps fail.
- Restart-safe with persisted state.
- Explicit about data and advisory timestamps.

## 20. Backtest versus OOS versus live

The product always separates:

```text
BACKTEST
Retrospective historical simulation

WALK-FORWARD OOS
Historical periods not viewed during each fold's parameter selection

LIVE PAPER
Prospectively published signals evaluated after publication

BROKER PAPER
Optional external sandbox fills, kept separate

LIVE REAL MONEY
Not supported in V0
```

Live-paper credibility increases with elapsed time and completed signals. It is
never backfilled retrospectively and presented as live.

## 21. Product experience

The strategy page should show:

- Name, version, style, risk description, and typical holding period.
- Frozen, plain-language rules.
- Execution and portfolio assumptions.
- Backtest results.
- Walk-forward OOS results.
- Verification matrix and known limitations.
- Live-since timestamp and prospective live-paper results.
- Current NEW, HOLD, and EXIT signals.
- Complete historical signal and trade list.

The current GitHub Pages site can serve static public research artifacts. It
cannot securely provide accounts, private subscriptions, protected signals, or
writable user state. Those require a hosted API and persistent database.

## 22. Core entities

```text
Strategy
StrategyVersion
DatasetSnapshot
UniverseVersion
Experiment
TrialRun
BacktestRun
EvaluationReport
VerificationReport
Signal
SignalEvent
OrderIntent
ModeledFill
Trade
PortfolioSnapshot
User
Subscription
```

User and subscription entities can wait until the research and live-paper spine
is reliable.

## 23. Phased expansion

Phase 1 — One complete first-party strategy:

- Trustworthy data and universe handling.
- Reproducible backtest.
- Walk-forward and robustness evaluation.
- Verification report.
- Immutable prospective signals.
- Live-paper track record.

Phase 2 — Multiple first-party strategies:

```text
Momentum
Mean reversion
Quality momentum
Low volatility
Breakout
```

All use the same data, execution, evaluation, and verification infrastructure.

Phase 3 — Subscription validation:

- Free delayed/basic signals.
- Premium complete signals and notifications.
- Test whether users repeatedly consume and value the output.

Phase 4 — Strategy portfolios:

- Cross-strategy correlation.
- Combined drawdown and Sharpe.
- Strategy allocation.

Phase 5 — Creator marketplace:

Creators submit strategy implementations, not self-reported performance.
Northstar controls data, execution assumptions, backtesting, walk-forward
evaluation, verification, and live tracking.

## 24. Long-term product advantage

The moat should not simply be a collection of stock-picking algorithms.
Individual signals can be copied and alpha can decay.

The stronger advantage is trusted, comparable infrastructure for:

- Data and point-in-time universes.
- Backtesting and portfolio accounting.
- Standard execution assumptions.
- Transaction-cost stress.
- Walk-forward evaluation.
- Reproducible experiments.
- Verification.
- Immutable signal history.
- Prospective live track records.
- Strategy discovery and subscriptions.

## 25. V0 success criteria

The engineering milestone is:

> One versioned strategy runs without manual intervention from validated
> historical data through backtest, walk-forward evaluation, verified metrics,
> daily prospective signals, lifecycle tracking, and live-paper performance.

```text
Validated historical OHLCV
      ↓
Point-in-time or explicitly limited universe
      ↓
Strategy #1
      ↓
10+ year reproducible backtest
      ↓
Walk-forward OOS
      ↓
Robustness and verification report
      ↓
Scheduled production run
      ↓
Immutable next-session signal
      ↓
FILLED / HOLD / EXIT / EXPIRED
      ↓
Prospective live-paper track record
```

The initial product milestone is:

> Real users can understand the strategy, subscribe to it, and repeatedly
> return to consume its signals.

Only after that behavior is demonstrated should Northstar expand aggressively
into additional strategies or a marketplace.

## 26. Current decisions and open questions

Settled for V0:

- Modular monolith.
- Daily U.S. equities and long-only.
- Same strategy code for research and prospective signals.
- Next-open modeled execution.
- Configurable costs, initially 10 bps per transaction.
- No limit-order simulation.
- $10,000 standardized starting capital.
- Strategy-independent execution and portfolio sizing.
- Immutable, versioned signal history.
- SPY benchmark.
- Walk-forward OOS before verified performance claims.

Still to finalize:

- Data vendor and licensing for point-in-time constituents and delistings.
- Final Strategy #1 rules and universe.
- Exact V0 portfolio baseline: five/20% during transition versus ten/15% target.
- Adjusted-price and corporate-action accounting policy.
- Walk-forward window lengths and parameter-selection metric.
- Risk-free-rate policy for Sharpe.
- Hosted backend and database provider for persistent live state.
- Notification channel and subscription product boundary.

Open questions must be resolved through explicit design decisions and recorded
experiments, not implicit implementation choices.
