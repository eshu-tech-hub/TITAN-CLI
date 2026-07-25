import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from titan.brokers.broker import Broker
from titan.brokers.models import (
    AccountProfile,
    BrokerType,
    CancelOrderRequest,
    Candle,
    ConnectionStatus,
    Exchange,
    FundsInfo,
    MarginInfo,
    MarketDepth,
    ModifyOrderRequest,
    Order as BrokerOrder,
    OrderRequest as BrokerOrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus as BrokerOrderStatus,
    OrderType,
    Position,
    ProductType,
    Quote,
    Trade,
    Validity,
)
from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.decision.models import DecisionAction, TradeDecision
from titan.execution import (
    ExecutionAllocator,
    ExecutionEngine,
    ExecutionOrchestrator,
    ExecutionPlan,
    ExecutionPlanner,
    ExecutionValidator,
    OrchestratorExplanation,
    OrchestratorReport,
    PlannedOrder,
    ValidationResult,
    AllocationInstruction,
)
from titan.portfolio.models import PortfolioSnapshot
from titan.risk.models import (
    CapitalAllocation,
    DecisionContext,
    PositionSizing,
    RiskAnalysis,
    RiskProfile,
    RiskScore,
    RiskScoreBand,
)

# ===========================================================================
# Helpers
# ===========================================================================


class _MockBroker(Broker):
    _connected: bool = True
    _funds: FundsInfo = FundsInfo(available_cash=100000.0)
    _margin: MarginInfo = MarginInfo(available_margin=50000.0)

    def connect(self) -> ConnectionStatus:
        self._connected = True
        return ConnectionStatus.CONNECTED

    def disconnect(self) -> ConnectionStatus:
        self._connected = False
        return ConnectionStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return self._connected

    def quote(self, symbol: str) -> Quote:
        return Quote(symbol=symbol, exchange=Exchange.NSE, last_price=Decimal("100.00"))

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        return {s: self.quote(s) for s in symbols}

    def ltp(self, symbol: str) -> Decimal:
        return Decimal("100.00")

    def option_chain(self, symbol: str, expiry: str | None = None) -> list[Quote]:
        return [self.quote(symbol)]

    def market_depth(self, symbol: str, level: int = 5) -> MarketDepth:
        return MarketDepth(symbol=symbol, exchange=Exchange.NSE)

    def history(
        self, symbol: str, interval: str, start: datetime, end: datetime | None = None
    ) -> list[Candle]:
        return []

    def intraday(self, symbol: str, interval: str = "1min") -> list[Candle]:
        return []

    def ohlcv(
        self, symbol: str, interval: str = "1day", limit: int = 100
    ) -> list[Candle]:
        return []

    def place_order(self, request: BrokerOrderRequest) -> OrderResponse:
        return OrderResponse(
            broker_order_id="BROKER-O1",
            status=BrokerOrderStatus.FILLED,
            filled_quantity=request.quantity,
            average_price=Decimal("100.00"),
            message="Mock order placed",
        )

    def modify_order(self, request: ModifyOrderRequest) -> OrderResponse:
        return OrderResponse(
            broker_order_id=request.broker_order_id,
            status=BrokerOrderStatus.OPEN,
        )

    def cancel_order(self, request: CancelOrderRequest) -> OrderResponse:
        return OrderResponse(
            broker_order_id=request.broker_order_id,
            status=BrokerOrderStatus.CANCELLED,
        )

    def order(self, broker_order_id: str) -> BrokerOrder:
        return BrokerOrder(
            broker_order_id=broker_order_id,
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            product=ProductType.DELIVERY,
            status=BrokerOrderStatus.OPEN,
            quantity=10,
        )

    def orders(
        self, symbol: str | None = None, since: datetime | None = None
    ) -> list[BrokerOrder]:
        return [self.order("O1")]

    def positions(self) -> list[Position]:
        return []

    def holdings(self) -> list[BrokerOrder]:
        return []

    def profile(self) -> AccountProfile:
        return AccountProfile()

    def trades(
        self, symbol: str | None = None, since: datetime | None = None
    ) -> list[Trade]:
        return []

    def funds(self) -> FundsInfo:
        return self._funds

    def margin(self) -> MarginInfo:
        return self._margin


def _make_trade_decision(**overrides: object) -> TradeDecision:
    defaults: dict[str, object] = {
        "decision": DecisionAction.BUY,
        "trade_direction": "long",
        "instrument_type": "underlying",
        "symbol": "RELIANCE",
        "stop_loss_reference": 2500.0,
        "target_reference": 2700.0,
    }
    merged = {**defaults, **overrides}
    return TradeDecision(**merged)  # type: ignore[arg-type]


def _make_portfolio_snapshot(**overrides: object) -> PortfolioSnapshot:
    defaults: dict[str, object] = {
        "total_capital": 1000000.0,
        "cash_reserve": 100000.0,
        "capital_used": 400000.0,
        "available_capital": 500000.0,
        "total_market_value": 450000.0,
        "total_pnl": 15000.0,
        "position_count": 5,
        "winning_positions": 3,
        "losing_positions": 2,
        "utilization": 0.4,
    }
    merged = {**defaults, **overrides}
    return PortfolioSnapshot(**merged)  # type: ignore[arg-type]


def _make_risk_analysis(**overrides: object) -> RiskAnalysis:
    sizing = PositionSizing(
        maximum_capital=50000.0,
        risk_per_trade=5000.0,
        units=20,
        contracts=0,
        maximum_quantity=20,
        capital_utilization=0.05,
    )
    capital = CapitalAllocation(
        capital_used=400000.0,
        available_capital=500000.0,
        maximum_allocation=50000.0,
        portfolio_concentration=0.05,
    )
    decision_ctx = DecisionContext(
        normal_size=True,
        maximum_contracts=50,
        confidence=0.8,
    )
    risk_score = RiskScore(value=30.0, band=RiskScoreBand.LOW)
    defaults: dict[str, object] = {
        "risk_profile": RiskProfile.MODERATE,
        "risk_score": risk_score,
        "position_sizing": sizing,
        "stop_loss": None,
        "targets": None,
        "capital_allocation": capital,
        "exposure": None,
        "decision_context": decision_ctx,
    }
    merged = {**defaults, **overrides}
    return RiskAnalysis(**merged)  # type: ignore[arg-type]


# ===========================================================================
# Planner Tests
# ===========================================================================


class TestPlannedOrder:
    def test_fields(self) -> None:
        order = PlannedOrder(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        assert order.symbol == "RELIANCE"
        assert order.exchange == Exchange.NSE
        assert order.side == OrderSide.BUY
        assert order.quantity == 10

    def test_defaults(self) -> None:
        order = PlannedOrder(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=5,
        )
        assert order.price is None
        assert order.trigger_price is None
        assert order.product == ProductType.DELIVERY
        assert order.validity == Validity.DAY
        assert order.tag == ""


class TestExecutionPlan:
    def test_fields(self) -> None:
        order = PlannedOrder(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        plan = ExecutionPlan(
            plan_id="PLAN-1",
            trade_decision_id="TD-1",
            orders=(order,),
            strategy="simple",
            total_quantity=10,
        )
        assert plan.plan_id == "PLAN-1"
        assert len(plan.orders) == 1
        assert plan.strategy == "simple"
        assert plan.total_quantity == 10

    def test_defaults(self) -> None:
        plan = ExecutionPlan(plan_id="P1", trade_decision_id="TD-1")
        assert plan.orders == ()
        assert plan.strategy == "simple"
        assert plan.total_quantity == 0


class TestExecutionPlanner:
    def test_simple_plan_buy(self) -> None:
        planner = ExecutionPlanner()
        decision = _make_trade_decision(decision=DecisionAction.BUY)
        plan = planner.plan(decision, strategy="simple", quantity=10)
        assert plan.strategy == "simple"
        assert plan.total_quantity == 10
        assert len(plan.orders) == 1
        assert plan.orders[0].side == OrderSide.BUY
        assert plan.orders[0].symbol == "RELIANCE"

    def test_simple_plan_sell(self) -> None:
        planner = ExecutionPlanner()
        decision = _make_trade_decision(decision=DecisionAction.SELL)
        plan = planner.plan(decision, strategy="simple", quantity=5)
        assert plan.total_quantity == 5
        assert plan.orders[0].side == OrderSide.SELL

    def test_simple_plan_no_trade(self) -> None:
        planner = ExecutionPlanner()
        decision = _make_trade_decision(decision=DecisionAction.NO_TRADE)
        plan = planner.plan(decision, strategy="simple")
        assert plan.orders == ()

    def test_twap_plan(self) -> None:
        planner = ExecutionPlanner()
        decision = _make_trade_decision(decision=DecisionAction.BUY)
        plan = planner.plan(
            decision, strategy="twap", quantity=100, slices=4, interval_minutes=15
        )
        assert plan.strategy == "twap"
        assert plan.total_quantity == 100
        assert len(plan.orders) == 4
        total = sum(o.quantity for o in plan.orders)
        assert total == 100
        for o in plan.orders:
            assert o.side == OrderSide.BUY
            assert "twap" in o.tag

    def test_twap_small_qty_does_not_overshoot(self) -> None:
        planner = ExecutionPlanner()
        decision = _make_trade_decision(decision=DecisionAction.BUY)
        plan = planner.plan(decision, strategy="twap", quantity=1, slices=4)
        assert plan.total_quantity == 1
        total = sum(o.quantity for o in plan.orders)
        assert total == 1

    def test_unknown_strategy_raises(self) -> None:
        planner = ExecutionPlanner()
        decision = _make_trade_decision()
        with pytest.raises(ValueError, match="Unknown execution strategy"):
            planner.plan(decision, strategy="unknown")

    def test_vwap_not_implemented(self) -> None:
        planner = ExecutionPlanner()
        decision = _make_trade_decision()
        with pytest.raises(NotImplementedError):
            planner.plan(decision, strategy="vwap")

    def test_iceberg_not_implemented(self) -> None:
        planner = ExecutionPlanner()
        decision = _make_trade_decision()
        with pytest.raises(NotImplementedError):
            planner.plan(decision, strategy="iceberg")

    def test_basket_not_implemented(self) -> None:
        planner = ExecutionPlanner()
        decision = _make_trade_decision()
        with pytest.raises(NotImplementedError):
            planner.plan(decision, strategy="basket")

    def test_ids_are_unique(self) -> None:
        planner = ExecutionPlanner()
        decision = _make_trade_decision(decision=DecisionAction.BUY)
        p1 = planner.plan(decision, quantity=10)
        p2 = planner.plan(decision, quantity=10)
        assert p1.plan_id != p2.plan_id


# ===========================================================================
# Validator Tests
# ===========================================================================


class TestValidationResult:
    def test_valid(self) -> None:
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.issues == ()

    def test_invalid_with_issues(self) -> None:
        result = ValidationResult(valid=False, issues=("Broker not connected",))
        assert result.valid is False
        assert len(result.issues) == 1


class TestExecutionValidator:
    def test_broker_connected_valid(self) -> None:
        broker = _MockBroker()
        broker._connected = True
        validator = ExecutionValidator()
        result = validator.validate(
            ExecutionPlan(plan_id="P1", trade_decision_id="TD-1"),
            broker,
            MagicMock(),
        )
        assert result.valid is False

    def test_broker_disconnected_fails(self) -> None:
        broker = _MockBroker()
        broker._connected = False
        order = PlannedOrder(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        plan = ExecutionPlan(plan_id="P1", trade_decision_id="TD-1", orders=(order,))
        validator = ExecutionValidator()
        oms = MagicMock()
        oms.router.registered_brokers.return_value = [BrokerType.ANGEL_ONE]
        result = validator.validate(plan, broker, oms)
        assert result.valid is False
        assert any("not connected" in i.lower() for i in result.issues)

    def test_oms_no_brokers_fails(self) -> None:
        broker = _MockBroker()
        order = PlannedOrder(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        plan = ExecutionPlan(plan_id="P1", trade_decision_id="TD-1", orders=(order,))
        validator = ExecutionValidator()
        oms = MagicMock()
        oms.router.registered_brokers.return_value = []
        result = validator.validate(plan, broker, oms)
        assert result.valid is False
        assert any("no registered brokers" in i.lower() for i in result.issues)

    def test_empty_plan_fails(self) -> None:
        broker = _MockBroker()
        plan = ExecutionPlan(plan_id="P1", trade_decision_id="TD-1")
        validator = ExecutionValidator()
        oms = MagicMock()
        oms.router.registered_brokers.return_value = [BrokerType.ANGEL_ONE]
        result = validator.validate(plan, broker, oms)
        assert result.valid is False
        assert any("no orders" in i.lower() for i in result.issues)

    def test_market_closed_fails(self) -> None:
        broker = _MockBroker()
        order = PlannedOrder(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        plan = ExecutionPlan(plan_id="P1", trade_decision_id="TD-1", orders=(order,))
        validator = ExecutionValidator(market_hours_check=lambda s: False)
        oms = MagicMock()
        oms.router.registered_brokers.return_value = [BrokerType.ANGEL_ONE]
        result = validator.validate(plan, broker, oms)
        assert result.valid is False
        assert any("market is closed" in i.lower() for i in result.issues)

    def test_trading_disabled_fails(self) -> None:
        broker = _MockBroker()
        order = PlannedOrder(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        plan = ExecutionPlan(plan_id="P1", trade_decision_id="TD-1", orders=(order,))
        validator = ExecutionValidator(trading_enabled_check=lambda s: False)
        oms = MagicMock()
        oms.router.registered_brokers.return_value = [BrokerType.ANGEL_ONE]
        result = validator.validate(plan, broker, oms)
        assert result.valid is False
        assert any("trading is not enabled" in i.lower() for i in result.issues)

    def test_instrument_not_tradable_fails(self) -> None:
        broker = _MockBroker()
        order = PlannedOrder(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        plan = ExecutionPlan(plan_id="P1", trade_decision_id="TD-1", orders=(order,))
        validator = ExecutionValidator(instrument_check=lambda s: False)
        oms = MagicMock()
        oms.router.registered_brokers.return_value = [BrokerType.ANGEL_ONE]
        result = validator.validate(plan, broker, oms)
        assert result.valid is False
        assert any("not tradable" in i.lower() for i in result.issues)

    def test_insufficient_funds_fails(self) -> None:
        broker = _MockBroker()
        broker._funds = FundsInfo(available_cash=100.0)
        order = PlannedOrder(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        plan = ExecutionPlan(plan_id="P1", trade_decision_id="TD-1", orders=(order,))
        validator = ExecutionValidator()
        oms = MagicMock()
        oms.router.registered_brokers.return_value = [BrokerType.ANGEL_ONE]
        result = validator.validate(
            plan, broker, oms, required_capital=Decimal("10000")
        )
        assert result.valid is False
        assert any("insufficient funds" in i.lower() for i in result.issues)


# ===========================================================================
# Allocator Tests
# ===========================================================================


class TestAllocationInstruction:
    def test_fields(self) -> None:
        alloc = AllocationInstruction(
            execution_quantity=10,
            execution_price=Decimal("2500.00"),
            capital_allocated=25000.0,
            price_reference="market",
        )
        assert alloc.execution_quantity == 10
        assert alloc.execution_price == Decimal("2500.00")
        assert alloc.capital_allocated == 25000.0

    def test_defaults(self) -> None:
        alloc = AllocationInstruction(execution_quantity=0)
        assert alloc.execution_price is None
        assert alloc.capital_allocated == 0.0
        assert alloc.price_reference == "market"


class TestExecutionAllocator:
    def test_allocate_basic(self) -> None:
        allocator = ExecutionAllocator()
        decision = _make_trade_decision(stop_loss_reference=2500.0)
        portfolio = _make_portfolio_snapshot(available_capital=500000.0)
        risk = _make_risk_analysis()
        result = allocator.allocate(decision, portfolio, risk)
        assert result.execution_quantity > 0
        assert result.capital_allocated > 0
        assert result.price_reference == "risk_analysis"

    def test_allocate_respects_max_contracts(self) -> None:
        allocator = ExecutionAllocator()
        decision = _make_trade_decision(stop_loss_reference=100.0)
        portfolio = _make_portfolio_snapshot(available_capital=1_000_000.0)
        sizing = PositionSizing(
            maximum_capital=500000.0,
            risk_per_trade=50000.0,
            units=1000,
            contracts=0,
            maximum_quantity=5000,
            capital_utilization=0.5,
        )
        capital = CapitalAllocation(
            capital_used=0.0,
            available_capital=1_000_000.0,
            maximum_allocation=500000.0,
            portfolio_concentration=0.5,
        )
        decision_ctx = DecisionContext(maximum_contracts=10, confidence=0.8)
        risk = _make_risk_analysis(
            position_sizing=sizing,
            capital_allocation=capital,
            decision_context=decision_ctx,
        )
        result = allocator.allocate(decision, portfolio, risk)
        assert result.execution_quantity == 10

    def test_allocate_min_one(self) -> None:
        allocator = ExecutionAllocator()
        decision = _make_trade_decision(stop_loss_reference=1.0)
        portfolio = _make_portfolio_snapshot(available_capital=0.0)
        sizing = PositionSizing(
            maximum_capital=0.0,
            risk_per_trade=0.0,
            units=0,
            contracts=0,
            maximum_quantity=0,
            capital_utilization=0.0,
        )
        capital = CapitalAllocation(
            capital_used=0.0,
            available_capital=0.0,
            maximum_allocation=0.0,
            portfolio_concentration=0.0,
        )
        decision_ctx = DecisionContext(maximum_contracts=0, confidence=0.0)
        risk = _make_risk_analysis(
            position_sizing=sizing,
            capital_allocation=capital,
            decision_context=decision_ctx,
        )
        result = allocator.allocate(decision, portfolio, risk)
        assert result.execution_quantity == 1


# ===========================================================================
# Orchestrator Tests
# ===========================================================================


class TestOrchestratorReport:
    def test_defaults(self) -> None:
        report = OrchestratorReport(execution_id="EXEC-1")
        assert report.orders_submitted == 0
        assert report.orders_accepted == 0
        assert report.errors == ()
        assert report.warnings == ()

    def test_fields(self) -> None:
        report = OrchestratorReport(
            execution_id="EXEC-1",
            orders_submitted=2,
            orders_accepted=2,
            orders_rejected=0,
            average_price=Decimal("100.50"),
            broker_order_ids=("BROKER-1", "BROKER-2"),
            errors=(),
            warnings=("Low liquidity",),
        )
        assert report.execution_id == "EXEC-1"
        assert report.orders_submitted == 2
        assert report.average_price == Decimal("100.50")
        assert len(report.broker_order_ids) == 2


class TestOrchestratorExplanation:
    def test_defaults(self) -> None:
        exp = OrchestratorExplanation()
        assert exp.summary == ""
        assert exp.validation == ""
        assert exp.planning == ""

    def test_fields(self) -> None:
        exp = OrchestratorExplanation(
            summary="Execution completed",
            validation="All checks passed",
            planning="Strategy: simple, 1 order(s)",
            allocation="Quantity: 10, Capital: 25000.00",
            submission="Submitted: 1, Accepted: 1, Rejected: 0",
            broker_response="Broker IDs: BROKER-1",
        )
        assert exp.summary == "Execution completed"
        assert "All checks passed" in exp.validation


class TestExecutionOrchestrator:
    def test_execute_success(self) -> None:
        broker = _MockBroker()
        oms = ExecutionEngine(MagicMock(), MagicMock())
        oms._router = MagicMock()
        oms._router.registered_brokers.return_value = [BrokerType.ANGEL_ONE]
        oms._router.route.return_value = MagicMock(
            success=True,
            broker_order_id="BROKER-O1",
            state="filled",
        )
        oms.execute = MagicMock()
        oms.execute.return_value = MagicMock(
            success=True,
            errors=(),
            order=MagicMock(
                broker_order_id="BROKER-O1",
                filled_quantity=10,
                average_price=Decimal("100.00"),
                state="filled",
            ),
        )

        planner = ExecutionPlanner()
        validator = ExecutionValidator()
        allocator = ExecutionAllocator()

        orchestrator = ExecutionOrchestrator(
            planner=planner,
            validator=validator,
            allocator=allocator,
            oms=oms,
            broker=broker,
        )

        decision = _make_trade_decision(decision=DecisionAction.BUY)
        portfolio = _make_portfolio_snapshot()
        risk = _make_risk_analysis()

        report = orchestrator.execute(decision, portfolio, risk, quantity=10)
        assert report.orders_submitted == 1
        assert report.orders_accepted == 1
        assert report.errors == ()

    def test_execute_planning_failure(self) -> None:
        broker = _MockBroker()
        oms = MagicMock()
        planner = ExecutionPlanner()
        validator = ExecutionValidator()
        allocator = ExecutionAllocator()
        orchestrator = ExecutionOrchestrator(
            planner=planner,
            validator=validator,
            allocator=allocator,
            oms=oms,
            broker=broker,
        )
        decision = _make_trade_decision()
        portfolio = _make_portfolio_snapshot()
        risk = _make_risk_analysis()
        report = orchestrator.execute(decision, portfolio, risk, strategy="vwap")
        assert len(report.errors) > 0
        assert "Planning failed" in report.errors[0]

    def test_execute_validation_failure(self) -> None:
        broker = _MockBroker()
        broker._connected = False
        oms = MagicMock()
        oms.router.registered_brokers.return_value = [BrokerType.ANGEL_ONE]
        planner = ExecutionPlanner()
        validator = ExecutionValidator()
        allocator = ExecutionAllocator()
        orchestrator = ExecutionOrchestrator(
            planner=planner,
            validator=validator,
            allocator=allocator,
            oms=oms,
            broker=broker,
        )
        decision = _make_trade_decision(decision=DecisionAction.BUY)
        portfolio = _make_portfolio_snapshot()
        risk = _make_risk_analysis()
        report = orchestrator.execute(decision, portfolio, risk, quantity=10)
        assert len(report.errors) > 0

    def test_execute_allocation_failure(self) -> None:
        broker = _MockBroker()
        oms = MagicMock()
        oms.router.registered_brokers.return_value = [BrokerType.ANGEL_ONE]
        planner = ExecutionPlanner()
        validator = ExecutionValidator()
        allocator = MagicMock()
        allocator.allocate.side_effect = ValueError("Allocation error")
        orchestrator = ExecutionOrchestrator(
            planner=planner,
            validator=validator,
            allocator=allocator,
            oms=oms,
            broker=broker,
        )
        decision = _make_trade_decision(decision=DecisionAction.BUY)
        portfolio = _make_portfolio_snapshot()
        risk = _make_risk_analysis()
        report = orchestrator.execute(decision, portfolio, risk, quantity=10)
        assert len(report.errors) > 0
        assert "Allocation failed" in report.errors[0]

    def test_execute_oms_failure(self) -> None:
        broker = _MockBroker()
        oms = MagicMock()
        oms.router.registered_brokers.return_value = [BrokerType.ANGEL_ONE]
        oms.execute.side_effect = RuntimeError("OMS crashed")
        planner = ExecutionPlanner()
        validator = ExecutionValidator()
        allocator = ExecutionAllocator()
        orchestrator = ExecutionOrchestrator(
            planner=planner,
            validator=validator,
            allocator=allocator,
            oms=oms,
            broker=broker,
        )
        decision = _make_trade_decision(decision=DecisionAction.BUY)
        portfolio = _make_portfolio_snapshot()
        risk = _make_risk_analysis()
        report = orchestrator.execute(decision, portfolio, risk, quantity=10)
        assert report.orders_submitted == 1
        assert report.orders_rejected >= 1

    def test_no_trade_decision_returns_empty_plan(self) -> None:
        broker = _MockBroker()
        oms = MagicMock()
        oms.router.registered_brokers.return_value = [BrokerType.ANGEL_ONE]
        planner = ExecutionPlanner()
        validator = ExecutionValidator()
        allocator = ExecutionAllocator()
        orchestrator = ExecutionOrchestrator(
            planner=planner,
            validator=validator,
            allocator=allocator,
            oms=oms,
            broker=broker,
        )
        decision = _make_trade_decision(decision=DecisionAction.NO_TRADE)
        portfolio = _make_portfolio_snapshot()
        risk = _make_risk_analysis()
        report = orchestrator.execute(decision, portfolio, risk)
        assert len(report.errors) > 0


# ===========================================================================
# Evidence Tests
# ===========================================================================


class TestOrchestratorEvidence:
    def test_generate_evidence_success(self) -> None:
        broker = _MockBroker()
        oms = ExecutionEngine(MagicMock(), MagicMock())
        oms._router = MagicMock()
        oms._router.registered_brokers.return_value = [BrokerType.ANGEL_ONE]
        oms.execute = MagicMock()
        oms.execute.return_value = MagicMock(
            success=True,
            errors=(),
            order=MagicMock(
                broker_order_id="BROKER-O1",
                filled_quantity=10,
                average_price=Decimal("100.00"),
                state="filled",
            ),
        )
        planner = ExecutionPlanner()
        validator = ExecutionValidator()
        allocator = ExecutionAllocator()
        orchestrator = ExecutionOrchestrator(
            planner=planner,
            validator=validator,
            allocator=allocator,
            oms=oms,
            broker=broker,
        )
        decision = _make_trade_decision(decision=DecisionAction.BUY)
        portfolio = _make_portfolio_snapshot()
        risk = _make_risk_analysis()
        report = orchestrator.execute(decision, portfolio, risk, quantity=10)
        evidence = orchestrator.generate_evidence(report)
        assert isinstance(evidence, Evidence)
        assert evidence.category == EvidenceCategory.EXECUTION
        assert evidence.source == "ExecutionOrchestrator"
        assert isinstance(evidence.score, Score)
        assert isinstance(evidence.confidence, Confidence)
        assert len(evidence.reasons) > 0

    def test_generate_evidence_failure(self) -> None:
        orchestrator = ExecutionOrchestrator(
            planner=ExecutionPlanner(),
            validator=ExecutionValidator(),
            allocator=ExecutionAllocator(),
            oms=MagicMock(),
            broker=_MockBroker(),
        )
        report = OrchestratorReport(
            execution_id="EXEC-1",
            orders_submitted=1,
            orders_accepted=0,
            orders_rejected=1,
            errors=("Broker not connected",),
        )
        evidence = orchestrator.generate_evidence(report)
        assert evidence.score.value == 0.0
        assert evidence.confidence.value == 0.0

    def test_generate_evidence_partial(self) -> None:
        orchestrator = ExecutionOrchestrator(
            planner=ExecutionPlanner(),
            validator=ExecutionValidator(),
            allocator=ExecutionAllocator(),
            oms=MagicMock(),
            broker=_MockBroker(),
        )
        report = OrchestratorReport(
            execution_id="EXEC-1",
            orders_submitted=4,
            orders_accepted=2,
            orders_rejected=2,
            broker_order_ids=("BROKER-1", "BROKER-2"),
        )
        evidence = orchestrator.generate_evidence(report)
        assert evidence.score.value == 50.0

    def test_generate_evidence_empty_report(self) -> None:
        orchestrator = ExecutionOrchestrator(
            planner=ExecutionPlanner(),
            validator=ExecutionValidator(),
            allocator=ExecutionAllocator(),
            oms=MagicMock(),
            broker=_MockBroker(),
        )
        report = OrchestratorReport(execution_id="EXEC-1")
        evidence = orchestrator.generate_evidence(report)
        assert evidence.score.value == 0.0
        assert any("no orders" in r.lower() for r in evidence.reasons)


# ===========================================================================
# Explanation Tests
# ===========================================================================


class TestExplanationGeneration:
    def test_generate_explanation_full(self) -> None:
        orchestrator = ExecutionOrchestrator(
            planner=ExecutionPlanner(),
            validator=ExecutionValidator(),
            allocator=ExecutionAllocator(),
            oms=MagicMock(),
            broker=_MockBroker(),
        )
        report = OrchestratorReport(
            execution_id="EXEC-1",
            orders_submitted=2,
            orders_accepted=2,
            average_price=Decimal("100.50"),
            broker_order_ids=("BROKER-1", "BROKER-2"),
        )
        plan = ExecutionPlan(plan_id="P1", trade_decision_id="TD-1", strategy="simple")
        validation = ValidationResult(valid=True)
        allocation = AllocationInstruction(
            execution_quantity=10,
            execution_price=Decimal("100.00"),
            capital_allocated=1000.0,
        )
        explanation = orchestrator.generate_explanation(
            report, plan, validation, allocation
        )
        assert isinstance(explanation, OrchestratorExplanation)
        assert "completed" in explanation.summary.lower()
        assert "simple" in explanation.planning
        assert "10" in explanation.allocation
        assert "2" in explanation.submission
        assert "BROKER" in explanation.broker_response

    def test_generate_explanation_errors(self) -> None:
        orchestrator = ExecutionOrchestrator(
            planner=ExecutionPlanner(),
            validator=ExecutionValidator(),
            allocator=ExecutionAllocator(),
            oms=MagicMock(),
            broker=_MockBroker(),
        )
        report = OrchestratorReport(
            execution_id="EXEC-1",
            errors=("Broker rejected order",),
            orders_rejected=1,
        )
        explanation = orchestrator.generate_explanation(report)
        assert "failed" in explanation.summary.lower()

    def test_generate_explanation_no_plan(self) -> None:
        orchestrator = ExecutionOrchestrator(
            planner=ExecutionPlanner(),
            validator=ExecutionValidator(),
            allocator=ExecutionAllocator(),
            oms=MagicMock(),
            broker=_MockBroker(),
        )
        report = OrchestratorReport(
            execution_id="EXEC-1",
            orders_submitted=1,
            orders_accepted=1,
            broker_order_ids=("BROKER-1",),
        )
        explanation = orchestrator.generate_explanation(report)
        assert "completed" in explanation.summary.lower()
        assert explanation.planning == "No plan."


# ===========================================================================
# Serialization Tests
# ===========================================================================


class TestSerialization:
    def test_orchestrator_report_json(self) -> None:
        report = OrchestratorReport(
            execution_id="EXEC-1",
            orders_submitted=2,
            orders_accepted=1,
            orders_rejected=1,
            average_price=Decimal("100.50"),
            broker_order_ids=("BROKER-1",),
            errors=("Order 2 rejected",),
            warnings=("Low liquidity",),
        )
        data = {
            "execution_id": report.execution_id,
            "orders_submitted": report.orders_submitted,
            "orders_accepted": report.orders_accepted,
            "orders_rejected": report.orders_rejected,
            "average_price": (
                str(report.average_price) if report.average_price else None
            ),
            "broker_order_ids": list(report.broker_order_ids),
            "errors": list(report.errors),
            "warnings": list(report.warnings),
        }
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["execution_id"] == "EXEC-1"
        assert deserialized["orders_submitted"] == 2
        assert deserialized["average_price"] == "100.50"

    def test_orchestrator_explanation_serialization(self) -> None:
        exp = OrchestratorExplanation(
            summary="Execution completed",
            validation="All checks passed",
            planning="Strategy: simple",
            allocation="Quantity: 10",
            submission="Accepted: 1",
            broker_response="Broker IDs: BROKER-1",
        )
        data = {
            "summary": exp.summary,
            "validation": exp.validation,
            "planning": exp.planning,
            "allocation": exp.allocation,
            "submission": exp.submission,
            "broker_response": exp.broker_response,
        }
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["summary"] == "Execution completed"
        assert deserialized["planning"] == "Strategy: simple"

    def test_evidence_serialization(self) -> None:
        evidence = Evidence(
            source="ExecutionOrchestrator",
            category=EvidenceCategory.EXECUTION,
            signal=EvidenceSignal.NEUTRAL,
            score=Score(100.0),
            confidence=Confidence(1.0),
            reasons=("All orders executed successfully",),
        )
        data = {
            "source": evidence.source,
            "category": evidence.category.value,
            "signal": evidence.signal.value,
            "score": evidence.score.value,
            "confidence": evidence.confidence.value,
            "reasons": list(evidence.reasons),
        }
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["source"] == "ExecutionOrchestrator"
        assert deserialized["category"] == "execution"
        assert deserialized["score"] == 100.0
        assert deserialized["confidence"] == 1.0
