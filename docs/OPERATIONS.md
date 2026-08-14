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

# Build a validated, content-addressed offline dataset
.venv/bin/northstar data sync --years 10
.venv/bin/northstar data snapshot

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
- `NORTHSTAR_DATA_ROOT`: raw, normalized, action, and snapshot data location
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

Run the data refresh after finalized bars are available. Validation uses the
XNYS exchange calendar and considers the current session complete after 4:30 PM
Eastern. The GitHub scheduler remains weekday-based, but holiday runs resolve
the latest expected exchange session correctly.

The pipeline writes decisions in one SQLite transaction. The API only selects
completed runs, so an interrupted refresh cannot partially replace the visible
dashboard snapshot.

The GitHub Pages job publishes an immutable build artifact instead of committing
generated market data to the repository. See `DEPLOYMENT.md`.

## Safety

Stops can execute away from their trigger price during gaps or fast markets.
Keep the dashboard's data timestamp visible and do not act on stale runs.
