# Research foundation

## Goal

Northstar should make it difficult to publish a result whose data, strategy
version, execution assumptions, or portfolio constraints are unknown. A
profitable backtest is not useful evidence when those inputs cannot be audited
and reproduced.

The foundation is a modular monolith. Module boundaries describe ownership of
logic, not independently deployed services.

```text
Validated dataset snapshot
          ↓
Versioned strategy + parameters
          ↓
Execution and portfolio configuration
          ↓
Chronological portfolio replay
          ↓
Metrics + run manifest + complete ledger
          ↓
Walk-forward / robustness / verification
```

## Current increment

The first foundation increment adds:

- `research/contracts.py`: immutable execution, portfolio, time-window,
  walk-forward, and experiment definitions.
- `research/validation.py`: fail-closed OHLCV structural validation.
- `research/manifest.py`: deterministic dataset fingerprints and research-run
  configuration identities.
- A research manifest and data-quality report in each dashboard snapshot.

The first follow-on increment migrated the existing trend-pullback strategy,
backtest, paper replay, signal language, and tests together to the V0
`NEXT_OPEN` policy. Strategies now publish intents and invalidation rules;
execution and portfolio modules determine fills and shares.

## Data-quality contract

Every research and production run validates data before invoking a strategy.
Fatal checks currently include:

- Missing or empty data.
- Missing Open, High, Low, Close, or Volume.
- Non-datetime, duplicate, or unsorted indexes.
- Insufficient indicator warm-up history.
- Null, infinite, or non-numeric OHLCV values.
- Nonpositive prices.
- High/low values inconsistent with open and close.
- Negative volume.

Zero volume is a warning rather than a fatal error because valid exchange data
can occasionally contain it. Future checks should cover exchange-calendar
gaps, stale symbols, split discontinuities, cross-provider comparisons, and
point-in-time universe metadata.

Validation answers whether a dataset is structurally usable. It does not prove
that the provider is correct or that the universe is free of survivorship bias.

## Dataset identity

Each symbol is fingerprinted from its ordered date index and canonical OHLCV
values. The dataset ID hashes all symbol fingerprints and date coverage.

```text
dataset ID changes if:
  a price or volume changes
  a date is added or removed
  the universe changes
  benchmark data changes
```

The fingerprint is evidence of exact inputs, not a replacement for preserving
the underlying dataset. A later data repository will keep immutable or
versioned Parquet snapshots referenced by this ID.

## Run identity

A research manifest records:

- Strategy ID and version.
- Dataset ID.
- Execution policy and costs.
- Portfolio constraints.
- Research start and end.
- Data-quality report.
- Git commit.

`run_config_id` hashes the assumptions that should affect a result. It excludes
the generation timestamp and Git commit so equivalent configurations can be
recognized. A future final `run_id` should also bind the result artifacts and
the exact code revision.

## Execution and portfolio boundaries

The strategy determines desired actions and strategy-specific invalidation
rules. It must not mutate cash or positions.

The execution policy owns:

- When an order is eligible to execute.
- The reference price.
- Transaction-cost and fee application.
- Gap and missing-bar behavior.

The portfolio engine owns:

- Cash and positions.
- Risk, allocation, and position-count limits.
- Shares and leverage rules.
- Realized and unrealized P&L.
- Daily mark-to-market state.

These configurations are immutable inputs to a run. Strategy code must not
silently override them.

## Experiment and hyperparameter design

Parameter experimentation is useful, but an unrestricted optimizer encourages
data snooping. Northstar separates four concerns:

```text
ExperimentSpec
    Written hypothesis + bounded candidate parameters

TrialRunner
    Runs every declared candidate and preserves every result

WalkForwardEvaluator
    Selects parameters using train/validation data only

RobustnessEvaluator
    Examines neighboring parameters, periods, universes, and costs
```

The current `ExperimentSpec` only declares and expands a deterministic, bounded
grid. It requires a written hypothesis and rejects grids above `max_trials`.
It intentionally does not offer `best_params()`.

Parameter selection will be implemented only with walk-forward evaluation:

```text
For each fold:
  fit/derive on training window, if needed
  select on validation window
  freeze parameters
  evaluate once on unseen OOS window

Concatenate only OOS daily portfolio returns.
```

Every attempted trial must remain in the experiment log. Reports will show the
parameter surface rather than only the winner.

## Near-term sequence

1. Finish extracting portfolio accounting from the legacy backtest into its
   owned module; next-open execution is already separate.
2. Add a versioned local Parquet market-data repository and dataset snapshots.
3. Add calendar coverage, staleness, and corporate-action checks.
4. Implement the simple `momentum_trend_v1` strategy.
5. Add full metrics and ledger persistence.
6. Add chronological walk-forward evaluation.
7. Add cost and parameter robustness reports.
8. Create machine-readable verification gates.

No performance result should receive a “verified” label until the relevant
data-bias, look-ahead, cost, walk-forward, robustness, and reproducibility gates
have passed or are clearly labeled as limited.
