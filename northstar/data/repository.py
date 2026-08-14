from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import pandas as pd

from northstar.data.schema import SCHEMA_VERSION, MarketDataBundle
from northstar.market_data import MarketDataProvider
from northstar.research.manifest import frame_fingerprint, table_fingerprint


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(handle)
    temporary_path = Path(temporary)
    try:
        frame.to_parquet(temporary_path, compression="zstd", index=True)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _atomic_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(handle)
    temporary_path = Path(temporary)
    try:
        temporary_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


class MarketDataRepository:
    def __init__(self, root: Path):
        self.root = root

    def raw_path(self, provider: str, symbol: str) -> Path:
        return self.root / "raw" / provider / "1d" / f"{symbol.upper()}.parquet"

    def bars_path(self, symbol: str) -> Path:
        return self.root / "normalized" / "1d" / f"{symbol.upper()}.parquet"

    def actions_path(self, symbol: str) -> Path:
        return self.root / "actions" / f"{symbol.upper()}.parquet"

    def metadata_path(self, symbol: str) -> Path:
        return self.root / "metadata" / f"{symbol.upper()}.json"

    def save(self, bundle: MarketDataBundle) -> None:
        _atomic_parquet(bundle.raw, self.raw_path(bundle.provider, bundle.symbol))
        _atomic_parquet(bundle.bars, self.bars_path(bundle.symbol))
        _atomic_parquet(bundle.actions, self.actions_path(bundle.symbol))
        _atomic_json(
            {
                "schema_version": SCHEMA_VERSION,
                "symbol": bundle.symbol,
                "provider": bundle.provider,
                "fetched_at": bundle.fetched_at,
                "rows": len(bundle.bars),
                "first_date": str(bundle.bars.index.min().date())
                if not bundle.bars.empty
                else None,
                "last_date": str(bundle.bars.index.max().date()) if not bundle.bars.empty else None,
                "bars_sha256": frame_fingerprint(bundle.bars),
            },
            self.metadata_path(bundle.symbol),
        )

    def load_bars(self, symbol: str) -> pd.DataFrame:
        path = self.bars_path(symbol)
        if not path.exists():
            raise FileNotFoundError(f"No normalized bars for {symbol}: {path}")
        return pd.read_parquet(path).sort_index()

    def load_raw(self, provider: str, symbol: str) -> pd.DataFrame:
        return pd.read_parquet(self.raw_path(provider, symbol)).sort_index()

    def load_actions(self, symbol: str) -> pd.DataFrame:
        path = self.actions_path(symbol)
        if not path.exists():
            return pd.DataFrame(columns=["Dividend", "Split"])
        return pd.read_parquet(path).sort_index()

    def load_metadata(self, symbol: str) -> dict:
        return json.loads(self.metadata_path(symbol).read_text(encoding="utf-8"))

    def available_symbols(self) -> tuple[str, ...]:
        directory = self.root / "normalized" / "1d"
        if not directory.exists():
            return ()
        return tuple(path.stem for path in sorted(directory.glob("*.parquet")))

    def snapshot_path(self, snapshot_id: str) -> Path:
        return self.root / "snapshots" / snapshot_id

    def create_snapshot(self, symbols: tuple[str, ...], *, provider: str) -> dict:
        entries = {}
        sources = {}
        for symbol in sorted({symbol.upper() for symbol in symbols}):
            bars = self.load_bars(symbol)
            raw = self.load_raw(provider, symbol)
            actions = self.load_actions(symbol)
            metadata = self.load_metadata(symbol)
            entries[symbol] = {
                "rows": len(bars),
                "first_date": str(bars.index.min().date()),
                "last_date": str(bars.index.max().date()),
                "bars_sha256": frame_fingerprint(bars),
                "raw_sha256": table_fingerprint(raw),
                "actions_sha256": table_fingerprint(actions),
            }
            sources[symbol] = {"fetched_at": metadata["fetched_at"]}

        import hashlib

        identity = {
            "schema_version": SCHEMA_VERSION,
            "provider": provider,
            "symbols": entries,
        }
        canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        snapshot_id = hashlib.sha256(canonical.encode()).hexdigest()
        destination = self.snapshot_path(snapshot_id)
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=f".{snapshot_id}.", dir=destination.parent))
            try:
                (staging / "bars").mkdir()
                (staging / "raw").mkdir()
                (staging / "actions").mkdir()
                for symbol in entries:
                    shutil.copy2(self.bars_path(symbol), staging / "bars" / f"{symbol}.parquet")
                    shutil.copy2(
                        self.raw_path(provider, symbol), staging / "raw" / f"{symbol}.parquet"
                    )
                    shutil.copy2(
                        self.actions_path(symbol), staging / "actions" / f"{symbol}.parquet"
                    )
                _atomic_json(
                    {"snapshot_id": snapshot_id, **identity, "sources": sources},
                    staging / "manifest.json",
                )
                os.replace(staging, destination)
            finally:
                shutil.rmtree(staging, ignore_errors=True)
        return json.loads((destination / "manifest.json").read_text(encoding="utf-8"))


class SnapshotProvider(MarketDataProvider):
    def __init__(self, repository: MarketDataRepository, snapshot_id: str):
        self.path = repository.snapshot_path(snapshot_id)
        manifest_path = self.path / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Unknown dataset snapshot: {snapshot_id}")
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.dataset_snapshot_id = snapshot_id
        if self.manifest.get("snapshot_id") != snapshot_id:
            raise ValueError("Snapshot directory and manifest identity do not match")
        for symbol, expected in self.manifest["symbols"].items():
            tables = {
                "bars_sha256": pd.read_parquet(self.path / "bars" / f"{symbol}.parquet"),
                "raw_sha256": pd.read_parquet(self.path / "raw" / f"{symbol}.parquet"),
                "actions_sha256": pd.read_parquet(self.path / "actions" / f"{symbol}.parquet"),
            }
            for field, table in tables.items():
                fingerprint = (
                    frame_fingerprint(table) if field == "bars_sha256" else table_fingerprint(table)
                )
                if fingerprint != expected[field]:
                    raise ValueError(f"Snapshot integrity check failed for {symbol} {field}")

    def daily_bars(self, ticker: str, years: int = 6) -> pd.DataFrame:
        del years
        path = self.path / "bars" / f"{ticker.upper()}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Snapshot does not contain {ticker}")
        bars = pd.read_parquet(path).sort_index()
        expected = self.manifest["symbols"].get(ticker.upper(), {}).get("bars_sha256")
        if expected is None or frame_fingerprint(bars) != expected:
            raise ValueError(f"Snapshot integrity check failed for {ticker}")
        return bars
