from __future__ import annotations

from northstar.config import Settings
from northstar.market_data import MarketDataProvider
from northstar.models import Decision
from northstar.store import Store
from northstar.strategy import evaluate


def run_daily(
    provider: MarketDataProvider,
    store: Store,
    settings: Settings,
    watchlist: tuple[str, ...] | None = None,
) -> tuple[str, list[Decision]]:
    decisions = []
    for ticker in watchlist or settings.watchlist:
        bars = provider.daily_bars(ticker)
        decisions.append(evaluate(ticker, bars, settings.portfolio_value, settings.risk_pct))
    run_id = store.save_completed_run(decisions)
    return run_id, decisions
