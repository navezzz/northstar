from datetime import datetime
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd
import pytest

from northstar.data.normalization import normalize_yahoo_history
from northstar.data.repository import MarketDataRepository, SnapshotProvider
from northstar.data.validation import expected_latest_xnys_session, validate_repository


def _history(end: str = "2026-08-14", periods: int = 260) -> pd.DataFrame:
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range("2024-01-01", end)[-periods:]
    close = pd.Series(range(100, 100 + len(sessions)), index=sessions, dtype=float)
    frame = pd.DataFrame(index=sessions)
    frame["Open"] = close - 0.5
    frame["High"] = close + 1
    frame["Low"] = close - 1
    frame["Close"] = close
    frame["Adj Close"] = close * 0.5
    frame["Volume"] = 1_000_000
    frame["Dividends"] = 0.0
    frame["Stock Splits"] = 0.0
    frame.loc[sessions[-20], "Dividends"] = 0.25
    frame.loc[sessions[-100], "Stock Splits"] = 2.0
    return frame


def test_yahoo_normalization_preserves_raw_actions_and_adjusts_ohlc():
    bundle = normalize_yahoo_history("TEST", _history())

    assert bundle.raw.iloc[-1]["Close"] == 359
    assert bundle.bars.iloc[-1]["Close"] == 179.5
    assert bundle.bars.iloc[-1]["Open"] == 179.25
    assert list(bundle.actions.columns) == ["Dividend", "Split"]
    assert len(bundle.actions) == 2


def test_repository_round_trip_validation_and_snapshot_are_deterministic(tmp_path):
    repository = MarketDataRepository(tmp_path / "market")
    now = datetime(2026, 8, 14, 17, 0, tzinfo=ZoneInfo("America/New_York"))
    for symbol in ("TEST", "SPY"):
        repository.save(normalize_yahoo_history(symbol, _history()))

    report = validate_repository(repository, ("TEST", "SPY"), now=now)
    first = repository.create_snapshot(("TEST", "SPY"), provider="yahoo")
    second = repository.create_snapshot(("SPY", "TEST"), provider="yahoo")

    assert report.passed
    assert not report.issues
    assert first["snapshot_id"] == second["snapshot_id"]
    assert (
        SnapshotProvider(repository, first["snapshot_id"])
        .daily_bars("TEST")
        .equals(repository.load_bars("TEST"))
    )
    assert (repository.snapshot_path(first["snapshot_id"]) / "raw" / "TEST.parquet").exists()


def test_validation_rejects_stale_repository_data(tmp_path):
    repository = MarketDataRepository(tmp_path / "market")
    repository.save(normalize_yahoo_history("TEST", _history(end="2026-08-13")))
    now = datetime(2026, 8, 14, 17, 0, tzinfo=ZoneInfo("America/New_York"))

    report = validate_repository(repository, ("TEST",), now=now)

    assert not report.passed
    assert any(issue.code == "STALE_DATA" for issue in report.issues)


def test_snapshot_provider_rejects_tampered_tables(tmp_path):
    repository = MarketDataRepository(tmp_path / "market")
    for symbol in ("TEST", "SPY"):
        repository.save(normalize_yahoo_history(symbol, _history()))
    manifest = repository.create_snapshot(("TEST", "SPY"), provider="yahoo")
    path = repository.snapshot_path(manifest["snapshot_id"]) / "bars" / "TEST.parquet"
    tampered = pd.read_parquet(path)
    tampered.iloc[-1, tampered.columns.get_loc("Close")] += 1
    tampered.to_parquet(path)

    with pytest.raises(ValueError, match="integrity"):
        SnapshotProvider(repository, manifest["snapshot_id"])


def test_expected_session_waits_for_close_buffer():
    before = datetime(2026, 8, 14, 16, 0, tzinfo=ZoneInfo("America/New_York"))
    after = datetime(2026, 8, 14, 16, 31, tzinfo=ZoneInfo("America/New_York"))

    assert str(expected_latest_xnys_session(before).date()) == "2026-08-13"
    assert str(expected_latest_xnys_session(after).date()) == "2026-08-14"
