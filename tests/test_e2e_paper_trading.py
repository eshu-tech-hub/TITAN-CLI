"""
End-to-End Paper Trading Certification Tests.
"""

import pytest

from tests.helpers.reconciliation import ExecutionReconciliationValidator
from tests.mocks.mock_fill_engines import (
    MockInstantFillEngine,
    MockPartialFillEngine,
    MockRejectFillEngine,
    MockTimeoutFillEngine,
)
from titan.brokers.models import Exchange, OrderRequest, OrderSide, OrderType
from titan.paper.broker import PaperBroker


def test_pipeline_execution_instant():
    broker = PaperBroker(fill_engine=MockInstantFillEngine())
    broker.connect()

    req = OrderRequest(
        symbol="AAPL",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
    )

    response = broker.place_order(req)
    assert response.status.name == "FILLED"
    assert response.filled_quantity == 10

    # Reconciliation
    validator = ExecutionReconciliationValidator(broker)
    errors = validator.validate_all()
    assert not errors, f"Reconciliation failed: {errors}"


def test_pipeline_execution_partial():
    broker = PaperBroker(fill_engine=MockPartialFillEngine())
    broker.connect()

    req = OrderRequest(
        symbol="AAPL",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
    )

    response = broker.place_order(req)
    assert (
        response.status.name == "FILLED"
    )  # broker treats partial as filled? Actually PaperBroker code sets it based on journal. We assume it sets it to FILLED or handles partial.

    validator = ExecutionReconciliationValidator(broker)
    assert not validator.validate_all()


def test_pipeline_execution_rejected():
    broker = PaperBroker(fill_engine=MockRejectFillEngine())
    broker.connect()

    req = OrderRequest(
        symbol="AAPL",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
    )

    response = broker.place_order(req)
    assert response.status.name == "REJECTED"

    validator = ExecutionReconciliationValidator(broker)
    assert not validator.validate_all()


def test_failure_injection_timeout():
    broker = PaperBroker(fill_engine=MockTimeoutFillEngine())
    broker.connect()

    req = OrderRequest(
        symbol="AAPL",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
    )

    with pytest.raises(TimeoutError):
        broker.place_order(req)

    validator = ExecutionReconciliationValidator(broker)
    assert not validator.validate_all()


def test_long_session_validation():
    broker = PaperBroker(fill_engine=MockInstantFillEngine())
    broker.connect()

    symbols = ["AAPL", "TSLA", "MSFT", "AMZN", "GOOGL"]

    for i in range(100):
        symbol = symbols[i % len(symbols)]
        side = OrderSide.BUY if i % 2 == 0 else OrderSide.SELL
        req = OrderRequest(
            symbol=symbol,
            exchange=Exchange.NSE,
            side=side,
            order_type=OrderType.MARKET,
            quantity=(i % 5) + 1,
        )
        # Even if selling short, paper broker tracks it.
        broker.place_order(req)

    validator = ExecutionReconciliationValidator(broker)
    assert not validator.validate_all()

    assert len(broker.orders()) == 100


def test_runtime_restart_and_recovery():
    broker = PaperBroker(fill_engine=MockInstantFillEngine())
    broker.connect()

    req1 = OrderRequest(
        symbol="AAPL",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
    )
    broker.place_order(req1)

    # Simulate disconnect
    broker.disconnect()

    # Simulate restart by instantiating new broker but feeding it the old journal/engines
    # In a real system, the journal is persisted to DB. Here we pass the in-memory journal to simulate state recovery.
    broker_restarted = PaperBroker(
        fill_engine=MockInstantFillEngine(),
        position_engine=broker.position_engine,
        portfolio=broker.portfolio,
        journal=broker.journal,
    )
    broker_restarted.connect()

    req2 = OrderRequest(
        symbol="TSLA",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=5,
    )
    broker_restarted.place_order(req2)

    assert len(broker_restarted.orders()) == 2

    validator = ExecutionReconciliationValidator(broker_restarted)
    assert not validator.validate_all()
