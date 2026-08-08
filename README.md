# Northstar

Northstar is an explainable daily stock decision-support app. It refreshes daily
market data, applies a transparent trend-pullback strategy, persists a complete
snapshot, and serves the latest results through a web dashboard.

It does not place orders and its output is not financial advice.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/northstar daily-run --watchlist AAPL,MSFT,NVDA
.venv/bin/northstar serve --reload
```

Open <http://127.0.0.1:8000>.

For offline development, generate a deterministic demonstration snapshot:

```bash
.venv/bin/northstar demo
```

If `uv` is installed, `uv sync --extra dev` and `uv run northstar ...` are
equivalent alternatives.

See [`docs/MVP.md`](docs/MVP.md) and [`docs/OPERATIONS.md`](docs/OPERATIONS.md).

## GitHub Pages

Northstar includes a scheduled Pages deployment. It refreshes real Yahoo data
at 4:37 PM Eastern on weekdays and can also be launched manually from GitHub
Actions. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
