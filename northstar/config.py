from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    db_path: Path
    watchlist: tuple[str, ...]
    portfolio_value: float
    risk_pct: float
    max_positions: int = 5
    max_position_pct: float = 0.20
    slippage_bps: float = 10.0
    fee_per_order: float = 0.0
    backtest_start: date = date(2021, 1, 1)
    paper_start: date = date(2026, 8, 7)

    @classmethod
    def from_env(cls) -> Settings:
        raw_path = Path(os.getenv("NORTHSTAR_DB_PATH", "data/northstar.db"))
        db_path = raw_path if raw_path.is_absolute() else _project_root() / raw_path
        watchlist = tuple(
            symbol.strip().upper()
            for symbol in os.getenv(
                "NORTHSTAR_WATCHLIST", "AAPL,MSFT,NVDA,AMZN,META,GOOGL,TSLA"
            ).split(",")
            if symbol.strip()
        )
        return cls(
            db_path=db_path,
            watchlist=watchlist,
            portfolio_value=float(os.getenv("NORTHSTAR_PORTFOLIO_VALUE", "10000")),
            risk_pct=float(os.getenv("NORTHSTAR_RISK_PCT", "0.01")),
            max_positions=int(os.getenv("NORTHSTAR_MAX_POSITIONS", "5")),
            max_position_pct=float(os.getenv("NORTHSTAR_MAX_POSITION_PCT", "0.20")),
            slippage_bps=float(os.getenv("NORTHSTAR_SLIPPAGE_BPS", "10")),
            fee_per_order=float(os.getenv("NORTHSTAR_FEE_PER_ORDER", "0")),
            backtest_start=date.fromisoformat(os.getenv("NORTHSTAR_BACKTEST_START", "2021-01-01")),
            paper_start=date.fromisoformat(os.getenv("NORTHSTAR_PAPER_START", "2026-08-07")),
        )
