from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from northstar.models import Decision


class BaseStrategy(ABC):
    """Contract between a strategy and the shared portfolio replay engine."""

    id: str
    name: str
    version: str
    status: str = "research"
    description: str
    universe: tuple[str, ...]

    @abstractmethod
    def prepare_bars(self, bars: pd.DataFrame) -> pd.DataFrame:
        """Precompute strategy-specific indicators without future leakage."""

    @abstractmethod
    def evaluate(
        self,
        ticker: str,
        prepared_bars: pd.DataFrame,
    ) -> Decision:
        """Evaluate completed bars without mutating or sizing a portfolio."""

    @abstractmethod
    def close_exit(
        self,
        ticker: str,
        prepared_bars: pd.DataFrame,
        as_of_date: pd.Timestamp,
        held_sessions: int,
    ) -> str | None:
        """Return an EOD exit reason to execute at the next session open."""

    @property
    @abstractmethod
    def execution_summary(self) -> dict:
        """Human-readable execution contract for the dashboard."""
