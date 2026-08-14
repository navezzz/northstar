from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from northstar.data.repository import MarketDataRepository
from northstar.research.validation import DataIssue, validate_ohlcv_frame


@dataclass(frozen=True, slots=True)
class RepositoryValidationReport:
    expected_latest_session: str
    symbols: tuple[str, ...]
    issues: tuple[DataIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "ERROR" for issue in self.issues)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "expected_latest_session": self.expected_latest_session,
            "symbols": list(self.symbols),
            "issues": [asdict(issue) for issue in self.issues],
        }


def expected_latest_xnys_session(now: datetime | None = None) -> pd.Timestamp:
    current = now or datetime.now(ZoneInfo("America/New_York"))
    if current.tzinfo is None:
        current = current.replace(tzinfo=ZoneInfo("America/New_York"))
    else:
        current = current.astimezone(ZoneInfo("America/New_York"))
    calendar = xcals.get_calendar("XNYS")
    day = pd.Timestamp(current.date())
    sessions = calendar.sessions_in_range(day - pd.Timedelta(days=14), day)
    completed = sessions[sessions < day]
    if calendar.is_session(day) and current.time() >= time(16, 30):
        return day
    if completed.empty:
        raise ValueError(f"Could not resolve a prior XNYS session for {day.date()}")
    return completed[-1]


def validate_repository(
    repository: MarketDataRepository,
    symbols: tuple[str, ...],
    *,
    now: datetime | None = None,
    min_rows: int = 200,
) -> RepositoryValidationReport:
    expected_latest = expected_latest_xnys_session(now)
    calendar = xcals.get_calendar("XNYS")
    issues: list[DataIssue] = []
    normalized_symbols = tuple(sorted({symbol.upper() for symbol in symbols}))

    for symbol in normalized_symbols:
        try:
            bars = repository.load_bars(symbol)
            raw = repository.load_raw("yahoo", symbol)
            actions = repository.load_actions(symbol)
        except (FileNotFoundError, OSError) as exc:
            issues.append(DataIssue("ERROR", "MISSING_STORED_DATA", symbol, str(exc)))
            continue

        issues.extend(validate_ohlcv_frame(symbol, bars, min_rows))
        if bars.empty:
            continue
        last = pd.Timestamp(bars.index.max()).normalize()
        if last < expected_latest:
            issues.append(
                DataIssue(
                    "ERROR",
                    "STALE_DATA",
                    symbol,
                    f"Latest bar is {last.date()}; expected {expected_latest.date()}",
                )
            )
        elif last > expected_latest:
            issues.append(
                DataIssue(
                    "ERROR",
                    "FUTURE_DATA",
                    symbol,
                    f"Latest bar {last.date()} exceeds expected session {expected_latest.date()}",
                )
            )

        expected = calendar.sessions_in_range(bars.index.min(), min(last, expected_latest))
        actual = pd.DatetimeIndex(bars.index).normalize()
        missing = expected.difference(actual)
        if len(missing):
            examples = ", ".join(str(value.date()) for value in missing[:3])
            issues.append(
                DataIssue(
                    "WARNING",
                    "MISSING_SESSIONS",
                    symbol,
                    f"Missing {len(missing)} expected sessions; first: {examples}",
                    len(missing),
                )
            )

        required_raw = {"Open", "High", "Low", "Close", "AdjClose", "Volume"}
        missing_raw = sorted(required_raw.difference(raw.columns))
        if missing_raw:
            issues.append(
                DataIssue(
                    "ERROR",
                    "MISSING_RAW_COLUMNS",
                    symbol,
                    f"Missing raw columns: {', '.join(missing_raw)}",
                )
            )
        else:
            factor = raw["AdjClose"] / raw["Close"].replace(0, np.nan)
            invalid_factor = int((~np.isfinite(factor) | (factor <= 0)).sum())
            if invalid_factor:
                issues.append(
                    DataIssue(
                        "ERROR",
                        "INVALID_ADJUSTMENT_FACTOR",
                        symbol,
                        "Adjusted/raw close factor must be finite and positive",
                        invalid_factor,
                    )
                )

        if not actions.empty and "Split" in actions:
            invalid_splits = int(((actions["Split"] != 0) & (actions["Split"] <= 0)).sum())
            if invalid_splits:
                issues.append(
                    DataIssue(
                        "ERROR",
                        "INVALID_SPLIT",
                        symbol,
                        "Split ratios must be positive",
                        invalid_splits,
                    )
                )

    return RepositoryValidationReport(
        expected_latest_session=str(expected_latest.date()),
        symbols=normalized_symbols,
        issues=tuple(issues),
    )
