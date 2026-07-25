"""
Mock Fill Engines for E2E Paper Trading Certification.

These doubles simulate different execution behaviors deterministically.
"""

from decimal import Decimal
from datetime import datetime, timezone
from typing import List
import time
import random

from titan.paper.fills import FillEngine
from titan.paper.models import PaperFill
from titan.brokers.models import OrderRequest, Quote, OrderType


class MockInstantFillEngine(FillEngine):
    """Simulates immediate full fill at the current quote price."""

    def fill(
        self,
        request: OrderRequest,
        quote: Quote,
        order_id: str,
        broker_order_id: str,
    ) -> List[PaperFill]:
        price = (
            request.price
            if request.order_type == OrderType.LIMIT and request.price
            else quote.last_price
        )
        return [
            PaperFill(
                fill_id=f"FILL-{order_id}-1",
                order_id=order_id,
                broker_order_id=broker_order_id,
                symbol=request.symbol,
                exchange=request.exchange,
                side=request.side,
                quantity=request.quantity,
                price=price,
                timestamp=datetime.now(timezone.utc),
            )
        ]


class MockPartialFillEngine(FillEngine):
    """Simulates a partial fill (e.g., 50% of requested quantity)."""

    def fill(
        self,
        request: OrderRequest,
        quote: Quote,
        order_id: str,
        broker_order_id: str,
    ) -> List[PaperFill]:
        price = (
            request.price
            if request.order_type == OrderType.LIMIT and request.price
            else quote.last_price
        )
        partial_qty = request.quantity // 2
        if partial_qty == 0:
            partial_qty = request.quantity

        return [
            PaperFill(
                fill_id=f"FILL-{order_id}-1",
                order_id=order_id,
                broker_order_id=broker_order_id,
                symbol=request.symbol,
                exchange=request.exchange,
                side=request.side,
                quantity=partial_qty,
                price=price,
                timestamp=datetime.now(timezone.utc),
            )
        ]


class MockDelayedFillEngine(FillEngine):
    """Simulates a deterministic delayed fill."""

    def fill(
        self,
        request: OrderRequest,
        quote: Quote,
        order_id: str,
        broker_order_id: str,
    ) -> List[PaperFill]:
        time.sleep(0.01)  # small deterministic delay
        price = (
            request.price
            if request.order_type == OrderType.LIMIT and request.price
            else quote.last_price
        )
        return [
            PaperFill(
                fill_id=f"FILL-{order_id}-1",
                order_id=order_id,
                broker_order_id=broker_order_id,
                symbol=request.symbol,
                exchange=request.exchange,
                side=request.side,
                quantity=request.quantity,
                price=price,
                timestamp=datetime.now(timezone.utc),
            )
        ]


class MockRejectFillEngine(FillEngine):
    """Simulates an exchange rejection (returns empty fill list)."""

    def fill(
        self,
        request: OrderRequest,
        quote: Quote,
        order_id: str,
        broker_order_id: str,
    ) -> List[PaperFill]:
        return []


class MockSlippageFillEngine(FillEngine):
    """Simulates slippage (worse fill price)."""

    def fill(
        self,
        request: OrderRequest,
        quote: Quote,
        order_id: str,
        broker_order_id: str,
    ) -> List[PaperFill]:
        base_price = (
            request.price
            if request.order_type == OrderType.LIMIT and request.price
            else quote.last_price
        )
        slippage = base_price * Decimal("0.005")  # 0.5% slippage
        # For simplicity, assuming BUY is higher, SELL is lower
        # In a generic fill, just add slippage for tests
        filled_price = base_price + slippage

        return [
            PaperFill(
                fill_id=f"FILL-{order_id}-1",
                order_id=order_id,
                broker_order_id=broker_order_id,
                symbol=request.symbol,
                exchange=request.exchange,
                side=request.side,
                quantity=request.quantity,
                price=filled_price,
                timestamp=datetime.now(timezone.utc),
            )
        ]


class MockTimeoutFillEngine(FillEngine):
    """Simulates a timeout exception during fill."""

    def fill(
        self,
        request: OrderRequest,
        quote: Quote,
        order_id: str,
        broker_order_id: str,
    ) -> List[PaperFill]:
        raise TimeoutError("Exchange connection timed out during fill.")


class MockRandomLatencyFillEngine(FillEngine):
    """Simulates random latency before filling."""

    def fill(
        self,
        request: OrderRequest,
        quote: Quote,
        order_id: str,
        broker_order_id: str,
    ) -> List[PaperFill]:
        time.sleep(random.uniform(0.001, 0.005))
        price = (
            request.price
            if request.order_type == OrderType.LIMIT and request.price
            else quote.last_price
        )
        return [
            PaperFill(
                fill_id=f"FILL-{order_id}-1",
                order_id=order_id,
                broker_order_id=broker_order_id,
                symbol=request.symbol,
                exchange=request.exchange,
                side=request.side,
                quantity=request.quantity,
                price=price,
                timestamp=datetime.now(timezone.utc),
            )
        ]
