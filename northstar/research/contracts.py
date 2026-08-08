from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from itertools import product
from typing import Literal


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """Execution assumptions that must accompany every research result."""

    policy: Literal["NEXT_OPEN"] = "NEXT_OPEN"
    slippage_bps: float = 10.0
    fee_per_order: float = 0.0

    def __post_init__(self) -> None:
        if self.slippage_bps < 0 or self.fee_per_order < 0:
            raise ValueError("Execution costs cannot be negative")


@dataclass(frozen=True, slots=True)
class PortfolioConfig:
    """Strategy-independent portfolio constraints."""

    initial_capital: float = 10_000.0
    risk_per_trade_pct: float = 0.01
    max_positions: int = 5
    max_position_pct: float = 0.20
    long_only: bool = True
    allow_leverage: bool = False

    def __post_init__(self) -> None:
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        if not 0 < self.risk_per_trade_pct <= 1:
            raise ValueError("Risk per trade must be in (0, 1]")
        if self.max_positions < 1:
            raise ValueError("At least one position must be allowed")
        if not 0 < self.max_position_pct <= 1:
            raise ValueError("Maximum position percentage must be in (0, 1]")


@dataclass(frozen=True, slots=True)
class ResearchWindow:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("Research window end cannot precede start")


@dataclass(frozen=True, slots=True)
class WalkForwardSpec:
    """Chronological train/validation/OOS window definition."""

    train_sessions: int
    validation_sessions: int
    oos_sessions: int
    step_sessions: int
    expanding_train: bool = True

    def __post_init__(self) -> None:
        values = (
            self.train_sessions,
            self.validation_sessions,
            self.oos_sessions,
            self.step_sessions,
        )
        if any(value < 1 for value in values):
            raise ValueError("Walk-forward session counts must be positive")


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    """A bounded, auditable parameter experiment—not an optimizer."""

    hypothesis: str
    parameter_space: dict[str, tuple[object, ...]] = field(default_factory=dict)
    selection_metric: str = "sharpe_ratio"
    max_trials: int = 100

    def __post_init__(self) -> None:
        if not self.hypothesis.strip():
            raise ValueError("An experiment requires a written hypothesis")
        if self.max_trials < 1:
            raise ValueError("max_trials must be positive")
        if any(not values for values in self.parameter_space.values()):
            raise ValueError("Every experiment parameter needs at least one value")
        if self.trial_count > self.max_trials:
            raise ValueError(
                f"Experiment expands to {self.trial_count} trials; limit is {self.max_trials}"
            )

    @property
    def trial_count(self) -> int:
        count = 1
        for values in self.parameter_space.values():
            count *= len(values)
        return count

    def trials(self) -> tuple[dict[str, object], ...]:
        keys = tuple(sorted(self.parameter_space))
        if not keys:
            return ({},)
        return tuple(
            dict(zip(keys, values, strict=True))
            for values in product(*(self.parameter_space[key] for key in keys))
        )

    def to_dict(self) -> dict:
        return asdict(self)
