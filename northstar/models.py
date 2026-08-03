from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Signal = Literal["BUY", "WATCH", "AVOID", "NO_DATA"]


@dataclass(frozen=True)
class Decision:
    ticker: str
    as_of: str
    signal: Signal
    close: float | None
    entry_low: float | None
    entry_high: float | None
    stop: float | None
    risk_per_share: float | None
    suggested_shares: int
    score: float
    reason: str
    exit_rule: str

    def to_dict(self) -> dict:
        return asdict(self)
