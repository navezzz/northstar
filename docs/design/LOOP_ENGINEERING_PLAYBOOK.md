# Northstar loop-engineering playbook

Status: **Execution companion to the V0 platform vision**
Created: 2026-08-14

This document turns the [canonical V0 vision](V0_PLATFORM_VISION.md) into a set
of bounded engineering loops. It is meant to survive changes in contributors,
tools, and implementation details.

## 1. The model

For Northstar, loop engineering means designing the environment in which good
decisions can be made repeatedly—not merely specifying a list of features.

Each milestone defines:

- **Context** — the trusted inputs, prior decisions, constraints, and evidence
  available to the work.
- **Tools** — code, commands, fixtures, reports, and observability used to make
  and evaluate changes.
- **Intent** — the outcome and invariants the milestone must protect.
- **Loop** — the repeatable sequence for observing, changing, testing, and
  recording results.
- **Taste** — the human quality bar used when several technically valid choices
  exist.

Context prevents uninformed work. Tools make feedback cheap. Intent prevents
local optimization. The loop creates learning. Taste prevents the system from
becoming technically correct but misleading, brittle, or unpleasant to use.

## 2. The common Northstar loop

Every milestone uses the same outer loop:

```text
1. Observe
   Inspect current artifacts, failures, limitations, and user behavior.

2. Frame
   Write the hypothesis, decision boundary, and success/failure criteria.

3. Change narrowly
   Make the smallest coherent change that can test the hypothesis.

4. Verify mechanically
   Run deterministic tests, data checks, and invariant checks.

5. Evaluate honestly
   Compare against baselines and inspect failure cases, not only aggregates.

6. Record
   Preserve inputs, configuration, results, limitations, and decision.

7. Promote or reject
   Advance only when the milestone exit gate is satisfied.
```

Failures are useful loop outputs. They should be preserved when they teach us
about a hypothesis or expose a weakness in the platform.

## 3. Dependency map

```text
M0 Governance and contracts
        ↓
M1 Trustworthy data and universe
        ↓
M2 Execution and portfolio accounting
        ↓
M3 Strategy research and experiments
        ↓
M4 Backtest evaluation and verification
        ↓
M5 Prospective live-paper system
        ↓
M6 User product and distribution
        ↓
M7 Multiple strategies and subscriptions
```

Later milestones may prototype against limited earlier infrastructure, but
they cannot claim completion while a required upstream exit gate is unmet.

---

## M0. Governance, contracts, and reproducibility

### Context

- [V0 platform vision](V0_PLATFORM_VISION.md).
- [Research foundation](RESEARCH_FOUNDATION.md).
- Current modular-monolith source tree.
- Existing strategy, execution, portfolio, and experiment contracts.
- Git history, tests, dataset fingerprints, and run manifests.
- V0 constraints: daily U.S. equities, long-only, next-open execution, no
  real-money trading.

### Tools

- Typed immutable configuration models.
- Strategy and execution interfaces.
- `pytest`, Ruff, and deterministic fixtures.
- Git commits and architecture/design records.
- Dataset and run fingerprints.
- A change checklist for schema/version compatibility.

### Intent

Create stable boundaries that make incorrect coupling visible:

- Strategies do not execute orders or mutate portfolios.
- Execution does not decide what is attractive.
- Portfolio accounting does not contain strategy rules.
- Evaluation does not silently alter strategy parameters.
- Published artifacts identify their versions and assumptions.

### Loop

1. Identify a boundary under pressure from the next milestone.
2. Write the desired responsibility and prohibited dependencies.
3. Add or change the smallest contract.
4. Prove substitutability with a deliberately unrelated implementation.
5. Run all existing consumers.
6. Version any externally stored or rendered schema.
7. Record the decision and migration path.

### Taste

- Prefer a few explicit concepts over generic framework machinery.
- A contract is good when a second implementation fits without conditionals in
  the shared engine.
- Avoid abstractions whose only implementation is hypothetical.
- Make invalid states difficult to construct.
- Names should express market timing precisely: `signal_close`, `next_open`,
  and `as_of`, not ambiguous `price` or `today`.

### Exit gate

- Core ownership boundaries are documented and tested.
- Stored schemas are versioned.
- Every research result identifies code, data, strategy, execution, portfolio,
  and evaluation assumptions.
- The repository has one obvious path for adding a strategy or evaluation.

---

## M1. Trustworthy market data and point-in-time universe

### Context

- Provider contracts and credentials.
- Canonical OHLCV schema and adjustment policy.
- Exchange calendar and U.S. session conventions.
- Security master, listings, delistings, and corporate actions where available.
- Universe eligibility rules and their historical availability.
- Known provider limitations and licensing constraints.
- Existing structural validator and dataset fingerprinting.

### Tools

- Versioned Parquet repository with atomic writes.
- Provider adapters and normalized fixtures.
- Trading-calendar library.
- Structural, coverage, staleness, and discontinuity validators.
- Cross-provider spot-check command.
- Dataset manifest and snapshot command.
- Data-quality report with `ERROR`, `WARNING`, and limitation statuses.
- Small golden datasets containing splits, missing sessions, delistings, and
  malformed bars.

### Intent

Make every downstream result traceable to data that is structurally valid,
temporally appropriate, and honestly characterized.

Protected invariants:

- No duplicate or future bars.
- One explicit adjustment policy.
- Dates conform to the expected exchange calendar or carry an explanation.
- The historical universe uses only information available at that date.
- A fixed current universe is labeled as survivorship-limited.
- Provider corrections produce a new dataset identity.

### Loop

```text
Fetch → Normalize → Validate → Compare → Snapshot → Fingerprint → Publish report
```

For each anomaly:

1. Preserve the raw provider response or a minimal fixture.
2. Classify provider issue, normalization bug, expected market event, or
   unsupported case.
3. Add a failing validator test.
4. Correct normalization or policy.
5. Rebuild the snapshot and inspect changed symbols/date ranges.
6. Record the limitation if it cannot be resolved.

### Taste

- Prefer failing closed over filling unexplained gaps silently.
- Preserve raw facts; derive adjusted views reproducibly.
- A clean-looking dataset is not evidence of correctness.
- Data-quality reports should help diagnose, not merely return red/green.
- Do not purchase complexity before knowing which verification claim requires
  it, but do not make broad unbiased claims from current-universe Yahoo data.

### Exit gate

- A single command creates a validated, immutable dataset snapshot.
- Calendar, staleness, OHLC, volume, and adjustment checks pass.
- Provider, retrieval time, coverage, and fingerprint are recorded.
- Universe membership can be reproduced for each historical date, or the run
  is explicitly marked `LIMITED` for survivorship bias.
- Representative symbols are reconciled against a second source.

---

## M2. Execution and portfolio-accounting engine

### Context

- Validated bars and exchange sessions from M1.
- Execution configuration: next-open, basis-point cost, fixed fee.
- Portfolio configuration: capital, risk, allocation, position count, integer
  shares, long-only, no leverage.
- Strategy intents containing action, score, stop, target, and validity.
- Explicit rules for gaps, missing opens, same-bar stop ambiguity, and final
  liquidation.

### Tools

- Pure next-open execution policy.
- Order, fill, position, trade, cash-ledger, and portfolio-snapshot models.
- Chronological event/replay engine.
- Hand-calculated accounting fixtures.
- Property/invariant tests for cash, equity, and position limits.
- Execution-cost stress fixtures.
- Ledger reconciliation command.

### Intent

Produce a deterministic account history without knowing or caring which
strategy generated the intents.

Protected invariants:

```text
equity = cash + market value
cash never falls below allowed bounds
no signal fills before it exists
no fill occurs on a missing session
position limits are never exceeded
fees and costs are charged exactly once
trade P&L reconciles to account change
```

### Loop

1. Express one market scenario as a tiny hand-calculated fixture.
2. Write the expected event order, fills, cash, positions, and equity.
3. Replay through the shared engine.
4. Compare every ledger event, not only final return.
5. Add the case to the permanent scenario suite.
6. Run all scenarios under zero and nonzero costs.
7. Only then test against a large historical dataset.

Required scenario loop includes:

- Ordinary entry and exit.
- Gap through an entry stop.
- Gap through an active stop.
- Entry and stop touched on the same daily bar.
- Multiple simultaneous candidates and limited cash.
- Missing ticker bar while the market trades.
- Corporate-action boundary.
- End-of-test liquidation.

### Taste

- Conservative ambiguity is preferable to optimistic invented precision.
- The ledger is the source of truth; summary metrics are derived views.
- Execution assumptions belong in output next to performance.
- Avoid clever vectorization until the chronological reference engine is
  demonstrably correct.
- Performance speed matters only after correctness can be continuously proven.

### Exit gate

- All scenario and invariant tests pass.
- A second no-op or synthetic strategy runs without engine changes.
- Every dollar of final equity reconciles to ledger events.
- Costs and gap behavior are documented and visible in results.
- Backtest and paper replay use the same execution/accounting components.

---

## M3. Strategy research and parameter experiments

### Context

- Frozen hypothesis for Strategy #1.
- Validated dataset and universe version.
- Shared feature definitions and availability times.
- Portfolio and execution assumptions from M2.
- Experiment log containing previous successful and failed ideas.
- Declared train, validation, and untouched OOS boundaries.
- Baselines: cash, SPY, and a deliberately simple momentum rule.

### Tools

- Versioned strategy interface and registry.
- Feature pipeline with point-in-time tests.
- `ExperimentSpec` requiring a hypothesis and bounded parameter space.
- Future `TrialRunner` that persists every trial.
- Parameter-surface tables and plots.
- Signal-diff tool: which dates/tickers changed between versions.
- Trade drill-down and regime/subperiod reports.
- Experiment manifest tied to code and dataset identities.

### Intent

Turn an economic hypothesis into the simplest auditable rule that exhibits
stable evidence—not find the highest historical score.

Strategy #1 should primarily validate the platform. Complexity must earn its
place through out-of-sample evidence and understandable behavior.

### Loop

```text
Hypothesis
  ↓
Simple implementation
  ↓
Feature/time-boundary tests
  ↓
Train analysis
  ↓
Validation comparison
  ↓
Failure-case inspection
  ↓
Record keep/reject decision
```

For parameter work:

1. State why the parameter should matter economically.
2. Declare neighboring values before running the experiment.
3. Run every declared value with identical inputs.
4. Inspect the surface, trade count, turnover, and regime behavior.
5. Prefer broad stable regions over an isolated optimum.
6. Freeze a choice before OOS evaluation.
7. Preserve every result and the decision rationale.

### Taste

- Simple enough to explain from memory is a feature.
- Economic coherence precedes statistical optimization.
- A parameter that only repairs one famous year is suspicious.
- Improvements should be visible in the trades they claim to improve.
- Fewer knobs and stable neighboring values beat a fragile higher Sharpe.
- Do not add a feature merely because it is available.

### Exit gate

- Strategy rules, parameters, universe, and expected behavior are frozen and
  versioned.
- Future-data invariance tests pass.
- Every experiment has a hypothesis and complete trial record.
- The chosen parameter region is stable on validation data.
- The untouched OOS window has not influenced implementation decisions.
- Strategy #1 is understandable without reading the source code.

---

## M4. Backtest evaluation, walk-forward, and verification

### Context

- Frozen strategy version from M3.
- Validated dataset/universe and correct replay engine.
- Predeclared fold schedule and selection metric.
- SPY benchmark and risk-free-rate policy.
- Required metric definitions.
- Verification criteria and minimum evidence thresholds.

### Tools

- Metrics module with independently tested formulas.
- Walk-forward fold planner.
- Trial runner and validation-only selector.
- OOS equity concatenator that respects portfolio continuity rules.
- Cost stress runner at 5/10/20/30 bps.
- Parameter, subperiod, regime, and universe robustness reports.
- Verification report with `PASS`, `FAIL`, `LIMITED`, `NOT_TESTED`.
- Reproduction command from a run manifest.

### Intent

Estimate how much confidence the evidence deserves and expose uncertainty. The
goal is not to manufacture a `Verified` badge.

Backtest, walk-forward OOS, and prospective live results must remain distinct.

### Loop

For each fold:

```text
Train or derive
    ↓
Select on validation only
    ↓
Freeze parameters
    ↓
Run once on unseen OOS
    ↓
Append OOS events and returns
```

After all folds:

1. Concatenate OOS history.
2. Reconcile all trades and equity.
3. Compute strategy and SPY metrics identically.
4. Run parameter and cost stress.
5. Inspect worst drawdowns and representative losses.
6. Evaluate every verification gate.
7. Publish limitations beside performance.

### Taste

- A credible mediocre result is more valuable than a beautiful contaminated
  result.
- Report distributions and failure regimes, not only averages.
- Comparison with SPY should use the same calendar and transparent assumptions.
- Avoid thresholds chosen after seeing the final OOS result.
- Verification language should be harder to earn than marketing language wants.
- Full trade history is part of the evidence, not debugging debris.

### Exit gate

- Core metrics reproduce from the stored ledger.
- Fold boundaries are chronological and auditable.
- Parameter selection never accesses OOS outcomes.
- OOS, benchmark, cost-stress, and robustness artifacts are complete.
- Verification gates are machine-readable and limitations are visible.
- A clean checkout can reproduce the published result from its manifest.

---

## M5. Prospective signal lifecycle and live-paper tracking

### Context

- Verified or explicitly `RESEARCH` strategy version.
- Finalized daily data and session calendar.
- Same feature, strategy, execution, and portfolio modules used in research.
- Previous immutable signals, events, fills, positions, and portfolio state.
- Publication cutoff, retry, correction, and stale-data policies.

### Tools

- Idempotent daily runner.
- Persistent signal/event repository.
- Atomic transaction boundary around a daily batch.
- Job/run log and data-freshness checks.
- Lifecycle state machine.
- Replay/rebuild command from immutable events.
- Scheduler with exchange-calendar awareness.
- Alerting for missing data, failed runs, and reconciliation errors.

### Intent

Build a prospective record that cannot be improved retrospectively. A user
should be able to reconstruct exactly what Northstar knew, published, and later
modeled as executed.

### Loop

Daily production loop:

```text
Check expected session
  ↓
Fetch and validate finalized data
  ↓
Load previous event-derived state
  ↓
Execute prior intents at today's open
  ↓
Update exits, positions, and portfolio
  ↓
Generate today's close-based intents
  ↓
Persist one atomic batch
  ↓
Publish only the complete batch
  ↓
Reconcile and alert
```

Operational improvement loop:

1. Reproduce any incident from stored inputs and events.
2. Add an idempotency or recovery test.
3. Fix the smallest responsible module.
4. Replay without changing already published facts.
5. Add a correction event when public information needs correction.

### Taste

- Boring reliability is the product.
- “No signal because data failed” is better than a stale or partial signal.
- Never rewrite live history to make it agree with new code.
- Every timestamp should identify market timezone and semantic meaning.
- Operational status must be understandable by someone who did not write the
  scheduler.

### Exit gate

- Repeated execution for the same date is idempotent.
- An interrupted run cannot publish partial state.
- State rebuild from events matches stored positions and equity.
- Signal lifecycle and corrections are immutable and queryable.
- Backtest and live-paper paths produce identical decisions for the same frozen
  historical context.
- The scheduled runner operates without manual intervention and alerts clearly
  when it cannot.

---

## M6. Strategy page, signal feed, and user trust

### Context

- Stored backtest, OOS, verification, and live-paper artifacts.
- Current immutable signal lifecycle.
- Product vocabulary and legal/disclosure constraints.
- User questions: What is this? Why this stock? What do I do next? How risky is
  it? Is this backtest or genuinely live?
- GitHub Pages limitations and future hosted-backend boundary.

### Tools

- Versioned API/static snapshot schema.
- Strategy-page and signal-feed components.
- Accessibility and responsive checks.
- Screenshot/visual regression fixtures where useful.
- Analytics for return visits, signal views, and subscription intent.
- Content checklist for assumptions, freshness, limitations, and complete
  history.
- User interviews and comprehension tests.

### Intent

Help a user understand and evaluate a strategy without overstating certainty.
The interface should make the next action and the source of every performance
number obvious.

### Loop

1. Choose one user question or observed confusion.
2. Find the minimum data and language needed to answer it.
3. Prototype against real stored artifacts, including bad and empty states.
4. Test comprehension, not merely visual preference.
5. Check mobile, accessibility, freshness, and failure behavior.
6. Measure whether users return and inspect complete history.
7. Record wording/schema decisions and iterate.

### Taste

- Separate `BACKTEST`, `WALK-FORWARD OOS`, and `LIVE PAPER` visually and
  semantically.
- Show assumptions near metrics, not behind a legal footer.
- Plain language first; methodology available one level deeper.
- Losing trades and inactive periods deserve the same visibility as winners.
- Avoid casino aesthetics, urgency, and false precision.
- Empty and failed states should feel deliberate, not broken.

### Exit gate

- Users can correctly explain what a signal means and when it executes.
- Performance provenance is clear without documentation.
- Verification limitations and full history are accessible.
- The page handles no-signal, stale-data, failed-run, and no-live-history states.
- Analytics can answer whether users repeatedly consume the strategy.

---

## M7. Multiple strategies, subscriptions, and platform expansion

### Context

- One stable end-to-end strategy and meaningful live-paper history.
- Evidence of recurring user demand.
- Standard strategy, data, execution, evaluation, and publishing contracts.
- Cross-strategy capital, overlap, and correlation concerns.
- Authentication, entitlement, notification, privacy, and billing requirements.
- Explicit non-goal until warranted: third-party marketplace.

### Tools

- Strategy registry and compatibility suite.
- Per-strategy versioned artifacts and event streams.
- Cross-strategy exposure/correlation analysis.
- Hosted API and PostgreSQL migrations.
- Authentication and entitlement service.
- Notification delivery with idempotency and audit logs.
- Subscription analytics and controlled product experiments.
- Eventually, sandboxed creator submissions evaluated on platform-owned data.

### Intent

Prove that the common infrastructure makes a second strategy cheaper and more
comparable without weakening verification or mixing track records.

Monetization follows demonstrated recurring value; the marketplace follows
demonstrated first-party platform reliability.

### Loop

Second-strategy loop:

1. Add through existing contracts only.
2. Run the full compatibility and verification suite.
3. Compare behavior, correlation, and overlapping positions.
4. Publish with a distinct immutable version and track record.
5. Identify shared gaps; generalize only after two real implementations need
   the same capability.

Subscription loop:

1. Measure repeated strategy consumption.
2. Test a narrow subscription value proposition.
3. Instrument activation, retention, delivery, and cancellation.
4. Improve reliability and comprehension before adding tiers.
5. Expand only when behavior, not stated interest, supports it.

### Taste

- The second strategy is the test of the platform abstraction.
- Comparability is more important than strategy count.
- Never combine track records across strategy versions.
- Do not hide better information merely to manufacture a weak paywall.
- Entitlements must not compromise immutable public evidence.
- Marketplace scale is earned after platform-controlled verification works for
  our own strategies.

### Exit gate

- A second strategy requires no strategy-specific execution, accounting,
  evaluation, or frontend branches.
- Cross-strategy positions and performance remain attributable.
- Subscription delivery is reliable, auditable, and privacy-conscious.
- Retention demonstrates recurring value before marketplace investment.
- Third-party performance can only be generated by platform-controlled data and
  evaluation.

---

## 4. Milestone working packet

Before starting a milestone increment, create a small working packet:

```markdown
# Increment name

## Context snapshot
- Relevant design decisions
- Current code/artifacts
- Known limitations
- Baseline result

## Intent
- User/system outcome
- Invariants
- Explicit non-goals

## Tools and tests
- Commands
- Fixtures
- Reports
- Observability

## Loop
- Hypothesis
- Smallest experiment/change
- Success and rejection criteria

## Taste checks
- What would be misleading?
- What would be needlessly complex?
- What failure cases must feel intentional?

## Result
- Inputs and versions
- Evidence
- Decision: promote / revise / reject
- New limitations or follow-ups
```

The packet may be a design plan, experiment manifest, or issue, but it must be
durable and linked to the resulting code/run.

## 5. Global taste checklist

Before promoting any increment, ask:

- Is it temporally honest?
- Is it reproducible from preserved inputs?
- Does the UI say exactly what the engine does?
- Are failures and limitations visible?
- Can we inspect every underlying event or trade?
- Did complexity buy measurable robustness or clarity?
- Would an unrelated second strategy fit the same boundary?
- Are we optimizing user trust or merely an attractive number?

If those answers are unclear, the loop is not complete.
