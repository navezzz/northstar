import pandas as pd

from northstar.demo import DemoProvider
from northstar.strategy import add_indicators, evaluate


def test_indicators_are_available_after_warmup():
    bars = DemoProvider().daily_bars("AAPL")
    row = add_indicators(bars).iloc[-1]
    assert pd.notna(row["MA200"])
    assert pd.notna(row["ATR14"])


def test_decision_has_coherent_price_plan():
    decision = evaluate("AAPL", DemoProvider().daily_bars("AAPL"))
    assert decision.signal in {"BUY", "WATCH", "AVOID"}
    assert decision.stop < decision.reference_price
    assert decision.target is None


def test_short_history_returns_no_data():
    bars = DemoProvider().daily_bars("AAPL").tail(50)
    assert evaluate("AAPL", bars).signal == "NO_DATA"
