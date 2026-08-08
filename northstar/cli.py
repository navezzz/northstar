from __future__ import annotations

import argparse
from pathlib import Path

from northstar.analysis import build_dashboard_snapshot
from northstar.config import Settings
from northstar.demo import DemoProvider
from northstar.market_data import YahooFinanceProvider
from northstar.site_export import export_site
from northstar.store import Store


def _symbols(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def main() -> None:
    parser = argparse.ArgumentParser(prog="northstar")
    subparsers = parser.add_subparsers(dest="command", required=True)
    daily = subparsers.add_parser("daily-run", help="Refresh data and save daily decisions")
    daily.add_argument("--watchlist", help="Comma-separated ticker symbols")
    demo = subparsers.add_parser("demo", help="Create deterministic demo decisions")
    demo.add_argument("--watchlist", help="Comma-separated ticker symbols")
    export = subparsers.add_parser("export-site", help="Build a deployable static dashboard")
    export.add_argument("--watchlist", help="Comma-separated ticker symbols")
    export.add_argument("--provider", choices=("yahoo", "demo"), default="yahoo")
    export.add_argument("--output", default="site", help="Static output directory")
    serve = subparsers.add_parser("serve", help="Run the API and dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.command == "serve":
        import uvicorn

        uvicorn.run("northstar.api:app", host=args.host, port=args.port, reload=args.reload)
        return

    provider = (
        YahooFinanceProvider()
        if args.command == "daily-run" or getattr(args, "provider", None) == "yahoo"
        else DemoProvider()
    )
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
