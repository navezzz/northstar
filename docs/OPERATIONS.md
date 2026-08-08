# Operations

## Commands

```bash
# Standard Python setup
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'

# Create an offline demonstration snapshot
.venv/bin/northstar demo

# Fetch current Yahoo daily bars and calculate a snapshot
.venv/bin/northstar daily-run --watchlist AAPL,MSFT,NVDA

# Serve the API and dashboard
.venv/bin/northstar serve --reload

# Build the same static artifact used by GitHub Pages
.venv/bin/northstar export-site --provider yahoo --output site

# Verify
.venv/bin/pytest
.venv/bin/ruff check .
```

When `uv` is available, use `uv sync --extra dev` and prefix commands with
`uv run` instead.

## Configuration

Copy `.env.example` values into your shell or scheduler environment. Northstar
does not load `.env` automatically in the MVP.

- `NORTHSTAR_DB_PATH`: SQLite database location
- `NORTHSTAR_WATCHLIST`: optional comma-separated universe override
- `NORTHSTAR_PORTFOLIO_VALUE`: starting cash for backtest and paper replay
- `NORTHSTAR_RISK_PCT`: maximum portfolio risk budget per entry
- `NORTHSTAR_MAX_POSITIONS`: concurrent-position ceiling
- `NORTHSTAR_MAX_POSITION_PCT`: maximum portfolio allocation per position
- `NORTHSTAR_SLIPPAGE_BPS`: simulated slippage applied on each fill
- `NORTHSTAR_FEE_PER_ORDER`: fixed simulated fee applied on each fill
- `NORTHSTAR_BACKTEST_START`: historical comparison start date
- `NORTHSTAR_PAPER_START`: paper-account replay start date

## Scheduling

Run `northstar daily-run` once per US trading day after finalized bars are
available, initially around 4:30 PM Eastern. A production scheduler should use a
US exchange calendar rather than weekday-only logic.

The pipeline writes decisions in one SQLite transaction. The API only selects
completed runs, so an interrupted refresh cannot partially replace the visible
dashboard snapshot.

The GitHub Pages job publishes an immutable build artifact instead of committing
generated market data to the repository. See `DEPLOYMENT.md`.

## Safety

The suggested share count is a mathematical risk ceiling, not a recommendation.
Stops can execute away from their trigger price during gaps or fast markets.
Keep the dashboard's data timestamp visible and do not act on stale runs.
