from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from northstar.analysis import build_dashboard_snapshot
from northstar.config import Settings
from northstar.data.provider import YahooDataProvider
from northstar.data.repository import MarketDataRepository, SnapshotProvider
from northstar.data.validation import validate_repository
from northstar.demo import DemoProvider
from northstar.market_data import YahooFinanceProvider
from northstar.site_export import export_site
from northstar.store import Store


def _symbols(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def _data_symbols(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*_symbols(value, default), "SPY")))


def _snapshot_provider(settings: Settings, snapshot_id: str | None) -> SnapshotProvider:
    if not snapshot_id:
        raise SystemExit("--snapshot-id is required when --provider snapshot")
    return SnapshotProvider(MarketDataRepository(settings.data_root), snapshot_id)


def _run_data_command(args, settings: Settings) -> None:
    repository = MarketDataRepository(settings.data_root)
    symbols = _data_symbols(getattr(args, "symbols", None), settings.watchlist)
    if args.data_command == "sync":
        provider = YahooDataProvider()
        for symbol in symbols:
            bundle = provider.fetch_daily(symbol, years=args.years)
            repository.save(bundle)
            print(f"Saved {symbol}: {len(bundle.bars)} bars, {len(bundle.actions)} actions")
        report = validate_repository(repository, symbols)
        print(json.dumps(report.to_dict(), indent=2))
        if not report.passed:
            raise SystemExit(1)
        return
    if args.data_command == "validate":
        now = datetime.fromisoformat(args.as_of) if args.as_of else None
        report = validate_repository(repository, symbols, now=now)
        print(json.dumps(report.to_dict(), indent=2))
        if not report.passed:
            raise SystemExit(1)
        return
    if args.data_command == "snapshot":
        report = validate_repository(repository, symbols)
        if not report.passed:
            print(json.dumps(report.to_dict(), indent=2))
            raise SystemExit("Refusing to snapshot invalid or stale market data")
        manifest = repository.create_snapshot(symbols, provider="yahoo")
        print(json.dumps(manifest, indent=2))
        return
    if args.data_command == "inspect":
        symbol = args.symbol.upper()
        payload = {
            "metadata": repository.load_metadata(symbol),
            "latest_bars": repository.load_bars(symbol)
            .tail(args.rows)
            .reset_index()
            .to_dict("records"),
            "actions": repository.load_actions(symbol)
            .tail(args.rows)
            .reset_index()
            .to_dict("records"),
        }
        print(json.dumps(payload, indent=2, default=str))
        return
    raise SystemExit("A data subcommand is required")


def main() -> None:
    parser = argparse.ArgumentParser(prog="northstar")
    subparsers = parser.add_subparsers(dest="command", required=True)
    daily = subparsers.add_parser("daily-run", help="Refresh data and save daily decisions")
    daily.add_argument("--watchlist", help="Comma-separated ticker symbols")
    daily.add_argument("--provider", choices=("yahoo", "snapshot"), default="yahoo")
    daily.add_argument("--snapshot-id")
    demo = subparsers.add_parser("demo", help="Create deterministic demo decisions")
    demo.add_argument("--watchlist", help="Comma-separated ticker symbols")
    export = subparsers.add_parser("export-site", help="Build a deployable static dashboard")
    export.add_argument("--watchlist", help="Comma-separated ticker symbols")
    export.add_argument("--provider", choices=("yahoo", "demo", "snapshot"), default="yahoo")
    export.add_argument("--snapshot-id")
    export.add_argument("--output", default="site", help="Static output directory")
    serve = subparsers.add_parser("serve", help="Run the API and dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    data = subparsers.add_parser("data", help="Manage versioned market data")
    data_subparsers = data.add_subparsers(dest="data_command", required=True)
    data_sync = data_subparsers.add_parser("sync", help="Fetch, normalize, save, and validate")
    data_sync.add_argument("--symbols", help="Comma-separated symbols; SPY is always included")
    data_sync.add_argument("--years", type=int, default=10)
    data_validate = data_subparsers.add_parser("validate", help="Validate stored market data")
    data_validate.add_argument("--symbols", help="Comma-separated symbols; SPY is always included")
    data_validate.add_argument(
        "--as-of", help="ISO timestamp used for deterministic freshness checks"
    )
    data_snapshot = data_subparsers.add_parser("snapshot", help="Create an immutable dataset")
    data_snapshot.add_argument("--symbols", help="Comma-separated symbols; SPY is always included")
    data_inspect = data_subparsers.add_parser("inspect", help="Inspect stored bars and actions")
    data_inspect.add_argument("symbol")
    data_inspect.add_argument("--rows", type=int, default=5)
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.command == "data":
        _run_data_command(args, settings)
        return
    if args.command == "serve":
        import uvicorn

        uvicorn.run("northstar.api:app", host=args.host, port=args.port, reload=args.reload)
        return

    provider_name = getattr(args, "provider", "yahoo")
    if provider_name == "snapshot":
        provider = _snapshot_provider(settings, args.snapshot_id)
    elif provider_name == "demo":
        provider = DemoProvider()
    else:
        provider = YahooFinanceProvider()
    snapshot = build_dashboard_snapshot(
        provider,
        settings,
        _symbols(args.watchlist, settings.watchlist),
    )
    if args.command == "export-site":
        export_site(snapshot, Path(args.output))
        print(f"Static dashboard written to {Path(args.output).resolve()}")
        return

    store = Store(settings.db_path)
    store.save_snapshot(snapshot)
    decisions = snapshot["strategies"][0]["recommendations"]
    print(f"Completed run {snapshot['run_id']} with {len(decisions)} decisions")
    for decision in decisions:
        print(
            f"{decision['ticker']:6} {decision['signal']:7} "
            f"score={decision['score']:5.1f} {decision['reason']}"
        )


if __name__ == "__main__":
    main()
