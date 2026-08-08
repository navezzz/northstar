from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from northstar.research.contracts import ExecutionConfig

Side = Literal["BUY", "SELL"]


@dataclass(frozen=True, slots=True)
class Fill:
    """A simulated fill produced by an execution policy."""

    reference_price: float
    price: float
    fee: float


class NextOpenExecution:
    """Execute prior-close intents at the next available session open."""

    def __init__(self, config: ExecutionConfig):
        if config.policy != "NEXT_OPEN":
            raise ValueError(f"NextOpenExecution cannot run policy {config.policy}")
        self.config = config

    def fill(self, open_price: float, side: Side) -> Fill:
        if open_price <= 0:
            raise ValueError("Execution reference price must be positive")
        direction = 1.0 if side == "BUY" else -1.0
        price = open_price * (1.0 + direction * self.config.slippage_bps / 10_000.0)
        return Fill(
            reference_price=float(open_price),
            price=float(price),
            fee=self.config.fee_per_order,
        )
