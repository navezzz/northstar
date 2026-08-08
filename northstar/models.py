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
    reference_price: float | None
    stop: float | None
    target: float | None
    score: float
    reason: str
    exit_rule: str
    valid_for: str

    def to_dict(self) -> dict:
        return asdict(self)
