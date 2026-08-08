from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

REQUIRED_OHLCV_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


@dataclass(frozen=True, slots=True)
class DataIssue:
    severity: str
    code: str
    symbol: str
    message: str
    rows: int = 0


@dataclass(frozen=True, slots=True)
class DataQualityReport:
    symbols_checked: int
    rows_checked: int
    first_date: str | None
    last_date: str | None
    issues: tuple[DataIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "ERROR" for issue in self.issues)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "symbols_checked": self.symbols_checked,
            "rows_checked": self.rows_checked,
            "first_date": self.first_date,
            "last_date": self.last_date,
            "issues": [asdict(issue) for issue in self.issues],
        }


class DataQualityError(ValueError):
    def __init__(self, report: DataQualityReport):
        self.report = report
        errors = [issue for issue in report.issues if issue.severity == "ERROR"]
        summary = "; ".join(f"{issue.symbol}:{issue.code}" for issue in errors[:5])
        super().__init__(f"Market data validation failed: {summary}")


def _validate_frame(symbol: str, frame: pd.DataFrame, min_rows: int) -> list[DataIssue]:
    issues: list[DataIssue] = []
    if frame.empty:
        return [DataIssue("ERROR", "EMPTY", symbol, "No market data rows")]

    missing = [column for column in REQUIRED_OHLCV_COLUMNS if column not in frame]
    if missing:
        return [
            DataIssue(
                "ERROR",
                "MISSING_COLUMNS",
                symbol,
                f"Missing required columns: {', '.join(missing)}",
            )
        ]
    if not isinstance(frame.index, pd.DatetimeIndex):
        issues.append(DataIssue("ERROR", "INVALID_INDEX", symbol, "Index is not datetime"))
    if frame.index.has_duplicates:
        issues.append(
            DataIssue(
                "ERROR",
                "DUPLICATE_DATES",
                symbol,
                "Duplicate trading dates",
                int(frame.index.duplicated().sum()),
            )
        )
    if not frame.index.is_monotonic_increasing:
        issues.append(DataIssue("ERROR", "UNSORTED_DATES", symbol, "Dates are not ascending"))
    if len(frame) < min_rows:
        issues.append(
            DataIssue(
                "ERROR",
                "INSUFFICIENT_HISTORY",
                symbol,
                f"Requires at least {min_rows} rows, found {len(frame)}",
                len(frame),
            )
        )

    numeric = frame.loc[:, REQUIRED_OHLCV_COLUMNS].apply(pd.to_numeric, errors="coerce")
    invalid_numbers = int((~np.isfinite(numeric.to_numpy(dtype=float))).sum())
    if invalid_numbers:
        issues.append(
            DataIssue(
                "ERROR",
                "NON_FINITE_VALUES",
                symbol,
                "OHLCV contains null or non-finite values",
                invalid_numbers,
            )
        )

    prices = numeric[["Open", "High", "Low", "Close"]]
    nonpositive = int((prices <= 0).any(axis=1).sum())
    if nonpositive:
        issues.append(
            DataIssue("ERROR", "NONPOSITIVE_PRICE", symbol, "Prices must be positive", nonpositive)
        )
    invalid_high = int((numeric["High"] < prices[["Open", "Low", "Close"]].max(axis=1)).sum())
    invalid_low = int((numeric["Low"] > prices[["Open", "High", "Close"]].min(axis=1)).sum())
    if invalid_high or invalid_low:
        issues.append(
            DataIssue(
                "ERROR",
                "INVALID_OHLC_RANGE",
                symbol,
                "High/low is inconsistent with open and close",
                invalid_high + invalid_low,
            )
        )
    negative_volume = int((numeric["Volume"] < 0).sum())
    if negative_volume:
        issues.append(
            DataIssue(
                "ERROR", "NEGATIVE_VOLUME", symbol, "Volume cannot be negative", negative_volume
            )
        )
    zero_volume = int((numeric["Volume"] == 0).sum())
    if zero_volume:
        issues.append(
            DataIssue(
                "WARNING", "ZERO_VOLUME", symbol, "Contains zero-volume sessions", zero_volume
            )
        )
    return issues


def validate_market_data(
    bars_by_symbol: dict[str, pd.DataFrame],
    benchmark_symbol: str,
    benchmark_bars: pd.DataFrame,
    *,
    min_rows: int = 200,
) -> DataQualityReport:
    """Validate data before research; callers decide whether errors fail the run."""
    all_frames = {**bars_by_symbol, benchmark_symbol: benchmark_bars}
    issues: list[DataIssue] = []
    for symbol, frame in sorted(all_frames.items()):
        issues.extend(_validate_frame(symbol, frame, min_rows))

    nonempty = [frame for frame in all_frames.values() if not frame.empty]
    first = min((frame.index.min() for frame in nonempty), default=None)
    last = max((frame.index.max() for frame in nonempty), default=None)
    return DataQualityReport(
        symbols_checked=len(all_frames),
        rows_checked=sum(len(frame) for frame in all_frames.values()),
        first_date=str(first.date()) if isinstance(first, pd.Timestamp) else None,
        last_date=str(last.date()) if isinstance(last, pd.Timestamp) else None,
        issues=tuple(issues),
    )
