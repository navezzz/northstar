from __future__ import annotations

import uuid
from datetime import UTC, datetime

from northstar.backtest import run_portfolio_backtest
from northstar.config import Settings
from northstar.market_data import MarketDataProvider
from northstar.research.contracts import ExecutionConfig, PortfolioConfig
from northstar.research.manifest import build_run_manifest, dataset_manifest
from northstar.research.validation import DataQualityError, validate_market_data
from northstar.strategies.registry import strategy_registry


def build_dashboard_snapshot(
    provider: MarketDataProvider,
    settings: Settings,
    watchlist: tuple[str, ...] | None = None,
) -> dict:
    strategies = strategy_registry()
    symbols = watchlist or tuple(
        dict.fromkeys(symbol for strategy in strategies for symbol in strategy.universe)
    )
    bars_by_ticker = {ticker: provider.daily_bars(ticker) for ticker in symbols}
    spy_bars = provider.daily_bars("SPY")
    data_quality = validate_market_data(bars_by_ticker, "SPY", spy_bars)
    if not data_quality.passed:
        raise DataQualityError(data_quality)
    execution_config = ExecutionConfig(
        policy="NEXT_OPEN",
        slippage_bps=settings.slippage_bps,
        fee_per_order=settings.fee_per_order,
    )
    portfolio_config = PortfolioConfig(
        initial_capital=settings.portfolio_value,
        risk_per_trade_pct=settings.risk_pct,
        max_positions=settings.max_positions,
        max_position_pct=settings.max_position_pct,
    )
    common = {
        "initial_capital": settings.portfolio_value,
        "risk_pct": settings.risk_pct,
        "max_positions": settings.max_positions,
        "max_position_pct": settings.max_position_pct,
        "slippage_bps": settings.slippage_bps,
        "fee_per_order": settings.fee_per_order,
    }

    strategy_payloads = []
    for strategy in strategies:
        strategy_bars = {
            ticker: bars_by_ticker[ticker]
            for ticker in strategy.universe
            if ticker in bars_by_ticker
        }
        decisions = [
            strategy.evaluate(
                ticker,
                strategy.prepare_bars(bars),
            )
            for ticker, bars in strategy_bars.items()
        ]
        decisions.sort(
            key=lambda decision: (decision.signal == "BUY", decision.score), reverse=True
        )
        backtest = run_portfolio_backtest(
            strategy,
            strategy_bars,
            spy_bars,
            start=settings.backtest_start,
            liquidate_end=True,
            **common,
        )
        paper = run_portfolio_backtest(
            strategy,
            strategy_bars,
            spy_bars,
            start=settings.paper_start,
            liquidate_end=False,
            **common,
        )
        strategy_dataset = dataset_manifest(strategy_bars, "SPY", spy_bars)
        source_snapshot_id = getattr(provider, "dataset_snapshot_id", None)
        if source_snapshot_id:
            strategy_dataset["source_snapshot_id"] = source_snapshot_id
        manifest = build_run_manifest(
            strategy_id=strategy.id,
            strategy_version=strategy.version,
            dataset=strategy_dataset,
            data_quality=data_quality,
            execution=execution_config,
            portfolio=portfolio_config,
            start=str(settings.backtest_start),
            end=backtest["as_of"],
        )
        strategy_payloads.append(
            {
                "id": strategy.id,
                "name": strategy.name,
                "version": strategy.version,
                "status": strategy.status,
                "description": strategy.description,
                "universe": list(strategy.universe),
                "recommendations": [decision.to_dict() for decision in decisions],
                "paper": paper,
                "backtest": backtest,
                "research_manifest": manifest,
                "execution": {
                    **strategy.execution_summary,
                    "risk_per_trade_pct": settings.risk_pct * 100,
                    "max_position_pct": settings.max_position_pct * 100,
                    "slippage_bps": settings.slippage_bps,
                    "fee_per_order": settings.fee_per_order,
                },
            }
        )

    return {
        "schema_version": 3,
        "run_id": uuid.uuid4().hex,
        "completed_at": datetime.now(UTC).isoformat(),
        "data_quality": data_quality.to_dict(),
        "strategies": strategy_payloads,
    }
