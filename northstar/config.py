from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    db_path: Path
    watchlist: tuple[str, ...]
    portfolio_value: float
    risk_pct: float

    @classmethod
    def from_env(cls) -> Settings:
        raw_path = Path(os.getenv("NORTHSTAR_DB_PATH", "data/northstar.db"))
        db_path = raw_path if raw_path.is_absolute() else _project_root() / raw_path
        watchlist = tuple(
            symbol.strip().upper()
            for symbol in os.getenv("NORTHSTAR_WATCHLIST", "AAPL,MSFT,NVDA,AMZN,META,GOOGL").split(
                ","
            )
            if symbol.strip()
        )
        return cls(
            db_path=db_path,
            watchlist=watchlist,
            portfolio_value=float(os.getenv("NORTHSTAR_PORTFOLIO_VALUE", "100000")),
            risk_pct=float(os.getenv("NORTHSTAR_RISK_PCT", "0.005")),
        )
