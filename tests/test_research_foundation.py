from datetime import date

import pandas as pd
import pytest

from northstar.demo import DemoProvider
from northstar.research.contracts import ExperimentSpec, PortfolioConfig, ResearchWindow
from northstar.research.manifest import dataset_manifest, frame_fingerprint
from northstar.research.validation import validate_market_data


def _bars(rows: int = 220) -> pd.DataFrame:
    index = pd.bdate_range("2025-01-01", periods=rows)
    close = pd.Series(range(100, 100 + rows), index=index, dtype=float)
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1_000_000,
        },
        index=index,
    )


def test_market_data_validation_rejects_impossible_price_bars():
    frame = _bars()
    frame.loc[frame.index[-1], "High"] = frame.loc[frame.index[-1], "Low"] - 1

    report = validate_market_data({"TEST": frame}, "SPY", _bars())

    assert not report.passed
    assert any(issue.code == "INVALID_OHLC_RANGE" for issue in report.issues)


def test_market_data_validation_accepts_demo_dataset():
    provider = DemoProvider()
    report = validate_market_data(
        {"AAPL": provider.daily_bars("AAPL")}, "SPY", provider.daily_bars("SPY")
    )

    assert report.passed
    assert report.rows_checked > 400


def test_dataset_fingerprint_is_deterministic_and_value_sensitive():
    original = _bars()
    changed = original.copy()
    changed.loc[changed.index[-1], "Close"] += 0.01

    assert frame_fingerprint(original) == frame_fingerprint(original.copy())
    assert frame_fingerprint(original) != frame_fingerprint(changed)
    assert (
        dataset_manifest({"TEST": original}, "SPY", original)["id"]
        == dataset_manifest({"TEST": original.copy()}, "SPY", original.copy())["id"]
    )


def test_experiment_grid_is_bounded_and_ordered():
    experiment = ExperimentSpec(
        hypothesis="Momentum should be stable across nearby lookbacks.",
        parameter_space={"lookback": (40, 60), "top_n": (5, 10)},
    )

    assert experiment.trial_count == 4
    assert experiment.trials()[0] == {"lookback": 40, "top_n": 5}

    with pytest.raises(ValueError, match="limit"):
        ExperimentSpec(
            hypothesis="Too broad",
            parameter_space={"a": tuple(range(11)), "b": tuple(range(10))},
            max_trials=100,
        )


def test_research_contracts_reject_invalid_configuration():
    with pytest.raises(ValueError):
        PortfolioConfig(initial_capital=0)
    with pytest.raises(ValueError):
        ResearchWindow(date(2026, 2, 1), date(2026, 1, 1))
