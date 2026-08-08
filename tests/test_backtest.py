from datetime import date

import pandas as pd

from northstar.backtest import run_portfolio_backtest
from northstar.demo import DemoProvider
from northstar.models import Decision
from northstar.strategies.base import BaseStrategy
from northstar.strategies.trend_pullback import TrendPullbackV1


class NoopStrategy(BaseStrategy):
    """A deliberately unrelated strategy used to verify the engine contract."""

    id = "noop_v1"
    name = "No-op"
    version = "1.0"
    description = "Never enters a position."
    universe = ("AAPL",)

    def __init__(self):
        self.evaluations = 0

    def prepare_bars(self, bars: pd.DataFrame) -> pd.DataFrame:
        prepared = bars.copy()
        prepared["CUSTOM_INDICATOR"] = 1.0
        return prepared

    def evaluate(
        self,
        ticker: str,
        prepared_bars: pd.DataFrame,
    ) -> Decision:
        assert "CUSTOM_INDICATOR" in prepared_bars
        self.evaluations += 1
        return Decision(
            ticker=ticker,
            as_of=str(prepared_bars.index[-1].date()),
            signal="WATCH",
            close=float(prepared_bars.iloc[-1]["Close"]),
            reference_price=float(prepared_bars.iloc[-1]["Close"]),
            stop=None,
            target=None,
            score=0.0,
            reason="No entry",
            exit_rule="None",
            valid_for="Next session",
        )

    def close_exit(
        self,
        ticker: str,
        prepared_bars: pd.DataFrame,
        as_of_date: pd.Timestamp,
        held_sessions: int,
    ) -> str | None:
        del ticker, prepared_bars, as_of_date, held_sessions
        return None

    @property
    def execution_summary(self) -> dict:
        return {"entry": "None", "signal_expiry": "None", "exits": "None"}


class BuyOnceStrategy(NoopStrategy):
    id = "buy_once_v1"

    def evaluate(self, ticker: str, prepared_bars: pd.DataFrame) -> Decision:
        self.evaluations += 1
        signal = "BUY" if self.evaluations == 1 else "WATCH"
        close = float(prepared_bars.iloc[-1]["Close"])
        return Decision(
            ticker=ticker,
            as_of=str(prepared_bars.index[-1].date()),
            signal=signal,
            close=close,
            reference_price=close,
            stop=1.0,
            target=None,
            score=100.0,
            reason="Test signal",
            exit_rule="End of test",
            valid_for="Next session open",
        )


def test_backtest_returns_strategy_and_spy_metrics():
    provider = DemoProvider()
    tickers = ("AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA")
    result = run_portfolio_backtest(
        TrendPullbackV1(),
        {ticker: provider.daily_bars(ticker) for ticker in tickers},
        provider.daily_bars("SPY"),
        start=date(2022, 1, 1),
    )

    assert result["initial_capital"] == 10_000
    assert result["as_of"] is not None
    assert "spy_return_pct" in result
    assert result["max_drawdown_pct"] <= 0


def test_paper_mode_preserves_open_positions_contract():
    provider = DemoProvider()
    result = run_portfolio_backtest(
        TrendPullbackV1(),
        {"AAPL": provider.daily_bars("AAPL")},
        provider.daily_bars("SPY"),
        start=date(2026, 1, 1),
        liquidate_end=False,
    )

    assert isinstance(result["open_positions"], list)
    assert isinstance(result["trades"], list)


def test_engine_accepts_an_unrelated_strategy_plugin():
    provider = DemoProvider()
    strategy = NoopStrategy()
    result = run_portfolio_backtest(
        strategy,
        {"AAPL": provider.daily_bars("AAPL")},
        provider.daily_bars("SPY"),
        start=date(2026, 1, 1),
    )

    assert strategy.evaluations > 0
    assert result["num_trades"] == 0


def test_signal_executes_at_following_session_open_with_cost():
    index = pd.bdate_range("2025-01-01", periods=205)
    bars = pd.DataFrame(
        {
            "Open": 100.0,
            "High": 102.0,
            "Low": 99.0,
            "Close": 101.0,
            "Volume": 1_000_000,
        },
        index=index,
    )
    result = run_portfolio_backtest(
        BuyOnceStrategy(),
        {"TEST": bars},
        bars,
        start=index[-3].date(),
        slippage_bps=10,
    )

    trade = result["trades"][0]
    assert trade["entry_date"] == str(index[-2].date())
    assert trade["entry_price"] == 100.10
    assert result["execution"]["policy"] == "NEXT_OPEN"
