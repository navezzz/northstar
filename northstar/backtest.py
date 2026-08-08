from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from northstar.execution import NextOpenExecution
from northstar.models import Decision
from northstar.research.contracts import ExecutionConfig
from northstar.strategies.base import BaseStrategy


@dataclass
class Position:
    ticker: str
    entry_date: pd.Timestamp
    entry_price: float
    shares: int
    stop: float
    entry_fee: float = 0.0
    held_sessions: int = 0


def _max_drawdown(values: list[float]) -> float:
    if not values:
        return 0.0
    series = pd.Series(values, dtype=float)
    drawdown = series / series.cummax() - 1.0
    return round(float(drawdown.min()) * 100, 2)


def run_portfolio_backtest(
    strategy: BaseStrategy,
    bars_by_ticker: dict[str, pd.DataFrame],
    spy_bars: pd.DataFrame,
    *,
    start: date,
    initial_capital: float = 10_000,
    risk_pct: float = 0.01,
    max_positions: int = 5,
    max_position_pct: float = 0.20,
    slippage_bps: float = 10.0,
    fee_per_order: float = 0.0,
    liquidate_end: bool = True,
) -> dict:
    """Replay completed-close signals at the next available session open."""
    execution_config = ExecutionConfig(
        policy="NEXT_OPEN",
        slippage_bps=slippage_bps,
        fee_per_order=fee_per_order,
    )
    execution = NextOpenExecution(execution_config)
    frames = {
        ticker: strategy.prepare_bars(bars)
        for ticker, bars in bars_by_ticker.items()
        if not bars.empty
    }
    spy = spy_bars.sort_index()
    dates = [d for d in spy.index if d.date() >= start]
    if not dates:
        return _empty_result(start, initial_capital, execution_config)

    cash = float(initial_capital)
    positions: dict[str, Position] = {}
    pending_orders: dict[str, Decision] = {}
    pending_exits: dict[str, str] = {}
    trades: list[dict] = []
    equity_curve: list[dict] = []

    def price_on(ticker: str, current_date: pd.Timestamp, column: str) -> float | None:
        frame = frames.get(ticker)
        if frame is None or current_date not in frame.index:
            return None
        value = frame.loc[current_date, column]
        return float(value) if pd.notna(value) else None

    def account_equity(current_date: pd.Timestamp, column: str = "Close") -> float:
        value = cash
        for ticker, position in positions.items():
            price = price_on(ticker, current_date, column)
            value += position.shares * (price if price is not None else position.entry_price)
        return value

    def close_position(
        ticker: str, current_date: pd.Timestamp, reference_price: float, reason: str
    ) -> None:
        nonlocal cash
        position = positions.pop(ticker)
        fill = execution.fill(reference_price, "SELL")
        cash += position.shares * fill.price - fill.fee
        total_fees = position.entry_fee + fill.fee
        pnl = (fill.price - position.entry_price) * position.shares - total_fees
        invested = position.entry_price * position.shares + position.entry_fee
        return_pct = pnl / invested * 100 if invested > 0 else 0.0
        trades.append(
            {
                "ticker": ticker,
                "entry_date": str(position.entry_date.date()),
                "entry_price": round(position.entry_price, 2),
                "exit_date": str(current_date.date()),
                "exit_price": round(fill.price, 2),
                "shares": position.shares,
                "return_pct": round(return_pct, 2),
                "pnl": round(pnl, 2),
                "fees": round(total_fees, 2),
                "reason": reason,
            }
        )

    for current_date in dates:
        # EOD exits from the prior session execute at today's open.
        for ticker, reason in list(pending_exits.items()):
            if ticker not in positions:
                pending_exits.pop(ticker, None)
                continue
            open_price = price_on(ticker, current_date, "Open")
            if open_price is not None:
                close_position(ticker, current_date, open_price, reason)
                pending_exits.pop(ticker, None)

        # Prior-close BUY signals execute at today's open. A gap through the
        # initial stop invalidates the setup before any capital is used.
        ranked_orders = sorted(pending_orders.items(), key=lambda item: item[1].score, reverse=True)
        for ticker, decision in ranked_orders:
            if ticker in positions or len(positions) >= max_positions:
                continue
            open_price = price_on(ticker, current_date, "Open")
            if open_price is None or decision.stop is None or open_price <= decision.stop:
                continue

            fill = execution.fill(open_price, "BUY")
            equity = account_equity(current_date, "Open")
            risk_per_share = max(fill.price - decision.stop, 0.01)
            risk_shares = int((equity * risk_pct) // risk_per_share)
            allocation_shares = int((equity * max_position_pct) // fill.price)
            affordable_shares = int(max(0.0, cash - fill.fee) // fill.price)
            shares = min(risk_shares, allocation_shares, affordable_shares)
            if shares <= 0:
                continue
            cash -= shares * fill.price + fill.fee
            positions[ticker] = Position(
                ticker=ticker,
                entry_date=current_date,
                entry_price=fill.price,
                shares=shares,
                stop=decision.stop,
                entry_fee=fill.fee,
            )
        pending_orders = {}

        # Protective stops are active after entry. Same-bar ambiguity is resolved
        # conservatively in favor of the stop having occurred after the fill.
        for ticker, position in list(positions.items()):
            low = price_on(ticker, current_date, "Low")
            open_price = price_on(ticker, current_date, "Open")
            if low is None or open_price is None or low > position.stop:
                continue
            close_position(ticker, current_date, min(position.stop, open_price), "STOP")

        # Closing-candle strategy exits queue for the next session's open.
        for ticker, position in positions.items():
            position.held_sessions += 1
            reason = strategy.close_exit(
                ticker, frames[ticker], current_date, position.held_sessions
            )
            if reason:
                pending_exits[ticker] = reason

        # Calculate signals only after today's closing values are known.
        for ticker, frame in frames.items():
            if ticker in positions or current_date not in frame.index:
                continue
            decision = strategy.evaluate(ticker, frame.loc[:current_date])
            if decision.signal == "BUY":
                pending_orders[ticker] = decision

        equity_curve.append(
            {"date": str(current_date.date()), "equity": round(account_equity(current_date), 2)}
        )

    last_date = dates[-1]
    if liquidate_end:
        for ticker in list(positions):
            close = price_on(ticker, last_date, "Close")
            if close is not None:
                close_position(ticker, last_date, close, "END_OF_TEST")
        final_equity = cash
        if equity_curve:
            equity_curve[-1]["equity"] = round(final_equity, 2)
    else:
        final_equity = account_equity(last_date)

    spy_window = spy.loc[dates[0] : dates[-1], "Close"].dropna()
    spy_return = (
        float(spy_window.iloc[-1] / spy_window.iloc[0] - 1.0) * 100 if len(spy_window) >= 2 else 0.0
    )
    wins = sum(1 for trade in trades if trade["return_pct"] > 0)
    return {
        "start": str(dates[0].date()),
        "as_of": str(dates[-1].date()),
        "initial_capital": round(initial_capital, 2),
        "equity": round(final_equity, 2),
        "total_return_pct": round((final_equity / initial_capital - 1.0) * 100, 2),
        "spy_return_pct": round(spy_return, 2),
        "max_drawdown_pct": _max_drawdown([row["equity"] for row in equity_curve]),
        "num_trades": len(trades),
        "win_rate_pct": round(wins / len(trades) * 100, 1) if trades else 0.0,
        "execution": {
            "policy": execution_config.policy,
            "slippage_bps": execution_config.slippage_bps,
            "fee_per_order": execution_config.fee_per_order,
        },
        "open_positions": [
            {
                "ticker": p.ticker,
                "entry_date": str(p.entry_date.date()),
                "entry_price": round(p.entry_price, 2),
                "shares": p.shares,
                "stop": round(p.stop, 2),
                "current_price": round(price_on(p.ticker, last_date, "Close") or p.entry_price, 2),
            }
            for p in positions.values()
        ],
        "trades": trades[-50:],
        "equity_curve": equity_curve,
    }


def _empty_result(start: date, initial_capital: float, execution_config: ExecutionConfig) -> dict:
    return {
        "start": str(start),
        "as_of": None,
        "initial_capital": initial_capital,
        "equity": initial_capital,
        "total_return_pct": 0.0,
        "spy_return_pct": 0.0,
        "max_drawdown_pct": 0.0,
        "num_trades": 0,
        "win_rate_pct": 0.0,
        "execution": {
            "policy": execution_config.policy,
            "slippage_bps": execution_config.slippage_bps,
            "fee_per_order": execution_config.fee_per_order,
        },
        "open_positions": [],
        "trades": [],
        "equity_curve": [],
    }
