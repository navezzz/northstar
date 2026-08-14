# Market-data foundation

Status: **M1.1 implemented**

This design implements the first trustworthy-data slice from the
[loop-engineering playbook](LOOP_ENGINEERING_PLAYBOOK.md).

## Goals

- Preserve provider facts separately from strategy-ready data.
- Apply one documented adjustment transformation.
- Validate structural integrity, exchange sessions, and freshness before
  creating a dataset snapshot.
- Make historical analysis runnable without network access.
- Give exact input tables deterministic identities.

## Storage model

```text
data/market/
  raw/yahoo/1d/<SYMBOL>.parquet
  normalized/1d/<SYMBOL>.parquet
  actions/<SYMBOL>.parquet
  metadata/<SYMBOL>.json
  snapshots/<SNAPSHOT_ID>/
    manifest.json
    raw/<SYMBOL>.parquet
    bars/<SYMBOL>.parquet
    actions/<SYMBOL>.parquet
```

Writes use a temporary file in the destination directory followed by atomic
replacement. An interrupted write cannot replace a valid table with a partial
Parquet file.

## Canonical tables

Raw Yahoo table:

```text
Open High Low Close AdjClose Volume
```

Corporate actions:

```text
Dividend Split
```

Strategy bars:

```text
adjustment_factor = AdjClose / Close
adjusted OHLC = raw OHLC × adjustment_factor
Volume = provider Volume
```

The raw table and actions are retained so the transformation can be audited.
Strategies receive only the normalized adjusted bars.

This adjustment model is appropriate for return features and split-consistent
technical indicators. It does not yet implement explicit cash-dividend
portfolio accounting. That limitation must be resolved before making precise
total-return claims for strategies that hold through distributions.

## Snapshot identity and immutability

The snapshot ID hashes:

- Schema version and provider.
- Sorted symbol membership.
- Date coverage and row counts.
- Raw-table hash.
- Normalized-bar hash.
- Corporate-action-table hash.

Retrieval timestamps are recorded but excluded from identity. Fetching
identical provider values twice therefore produces the same snapshot ID.
Provider corrections or any changed input value produce a different ID.

A snapshot copies the exact raw, normalized, and action Parquet files into its
own directory. `SnapshotProvider` verifies each normalized table against the
manifest before returning it.

## Validation

Snapshot creation fails on:

- Missing stored tables.
- Empty or insufficient histories.
- Missing required columns.
- Duplicate or unsorted dates.
- Non-finite or nonpositive prices.
- Invalid OHLC ranges or negative volume.
- Invalid adjusted/raw close factors.
- Invalid split ratios.
- Bars older or newer than the latest expected completed XNYS session.

Missing expected sessions are warnings rather than fatal errors because a
specific security may be halted while XNYS remains open. Warnings are retained
for inspection and future security-master reconciliation.

The latest expected session uses the XNYS calendar. On a trading day, the
current session becomes eligible at 4:30 PM America/New_York, providing a
buffer after the close for daily data finalization.

## Commands

```bash
# Fetch Yahoo facts, normalize, save, and validate the default universe + SPY
uv run northstar data sync --years 10

# Validate existing stored data; useful for deterministic incident replay
uv run northstar data validate --as-of 2026-08-14T17:00:00-04:00

# Create or reuse a content-addressed immutable snapshot
uv run northstar data snapshot

# Inspect recent stored bars, actions, and metadata
uv run northstar data inspect AAPL

# Run the dashboard/backtest offline from exact preserved inputs
uv run northstar export-site \
  --provider snapshot \
  --snapshot-id <SNAPSHOT_ID> \
  --output site
```

SPY is always included because it defines the benchmark calendar and
comparison. `NORTHSTAR_DATA_ROOT` controls the repository location.

## GitHub Pages flow

The scheduled job now performs:

```text
sync → validate → immutable snapshot → offline export → deploy
```

An invalid or stale dataset stops the job before site publication. The static
snapshot records the content fingerprint and source snapshot ID. GitHub-hosted
runners are ephemeral, so durable long-term archival of scheduled Parquet
snapshots remains a Phase 2 infrastructure requirement.

## Known limitations and next loop

- Yahoo is a prototyping source, not a verified institutional dataset.
- Scheduled-run Parquet snapshots are not durably archived after the ephemeral
  GitHub runner exits.
- Universe membership is still a current fixed list and remains
  survivorship-limited.
- Delistings and symbol changes are not modeled.
- Dividends are reflected through adjusted prices, not explicit portfolio cash.
- Missing-session warnings are not reconciled against security-specific halt or
  listing history.
- Cross-provider comparison is not implemented.

M1.2 should add a security master and point-in-time universe interface, durable
snapshot archival, cross-provider spot checks, and explicit corporate-action
portfolio policy.
