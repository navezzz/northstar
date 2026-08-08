from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime

import pandas as pd

from northstar.research.contracts import ExecutionConfig, PortfolioConfig
from northstar.research.validation import REQUIRED_OHLCV_COLUMNS, DataQualityReport


def _canonical_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def frame_fingerprint(frame: pd.DataFrame) -> str:
    """Hash canonical OHLCV values and dates without serializing the full dataset."""
    columns = [column for column in REQUIRED_OHLCV_COLUMNS if column in frame]
    canonical = frame.loc[:, columns].sort_index()
    values = pd.util.hash_pandas_object(canonical, index=True).values.tobytes()
    return hashlib.sha256(values).hexdigest()


def dataset_manifest(
    bars_by_symbol: dict[str, pd.DataFrame], benchmark_symbol: str, benchmark: pd.DataFrame
) -> dict:
    frames = {**bars_by_symbol, benchmark_symbol: benchmark}
    symbols = {
        symbol: {
            "rows": len(frame),
            "first_date": str(frame.index.min().date()) if not frame.empty else None,
            "last_date": str(frame.index.max().date()) if not frame.empty else None,
            "sha256": frame_fingerprint(frame),
        }
        for symbol, frame in sorted(frames.items())
    }
    return {"id": _canonical_hash(symbols), "symbols": symbols}


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def build_run_manifest(
    *,
    strategy_id: str,
    strategy_version: str,
    dataset: dict,
    data_quality: DataQualityReport,
    execution: ExecutionConfig,
    portfolio: PortfolioConfig,
    start: str,
    end: str | None,
) -> dict:
    assumptions = {
        "strategy_id": strategy_id,
        "strategy_version": strategy_version,
        "dataset_id": dataset["id"],
        "execution": asdict(execution),
        "portfolio": asdict(portfolio),
        "start": start,
        "end": end,
    }
    return {
        "run_config_id": _canonical_hash(assumptions),
        "generated_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "assumptions": assumptions,
        "data_quality": data_quality.to_dict(),
    }
