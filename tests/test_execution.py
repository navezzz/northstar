import pytest

from northstar.execution import NextOpenExecution
from northstar.research.contracts import ExecutionConfig


def test_next_open_execution_makes_buys_worse_and_sells_worse():
    policy = NextOpenExecution(
        ExecutionConfig(policy="NEXT_OPEN", slippage_bps=10, fee_per_order=1)
    )

    buy = policy.fill(100, "BUY")
    sell = policy.fill(100, "SELL")

    assert buy.price == pytest.approx(100.10)
    assert sell.price == pytest.approx(99.90)
    assert buy.fee == sell.fee == 1


def test_next_open_execution_rejects_nonpositive_prices():
    policy = NextOpenExecution(ExecutionConfig())
    with pytest.raises(ValueError):
        policy.fill(0, "BUY")
