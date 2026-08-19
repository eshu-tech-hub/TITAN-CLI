from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from titan.brokers.broker import Broker
from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)

if TYPE_CHECKING:
    from titan.decision.models import TradeDecision
from titan.execution.allocator import AllocationInstruction, ExecutionAllocator
from titan.execution.execution import ExecutionEngine
from titan.execution.models import ExecutionRequest, OrderState
from titan.execution.planner import ExecutionPlan, ExecutionPlanner
from titan.execution.validator import ExecutionValidator, ValidationResult
from titan.portfolio.models import PortfolioSnapshot
from titan.risk.models import RiskAnalysis


@dataclass(frozen=True, slots=True)
class OrchestratorReport:
    execution_id: str
    orders_submitted: int = 0
    orders_accepted: int = 0
    orders_rejected: int = 0
    average_price: Decimal | None = None
    broker_order_ids: tuple[str, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class OrchestratorExplanation:
    summary: str = ""
    validation: str = ""
    planning: str = ""
    allocation: str = ""
    submission: str = ""
    broker_response: str = ""


class ExecutionOrchestrator:
    def __init__(
        self,
        planner: ExecutionPlanner,
        validator: ExecutionValidator,
        allocator: ExecutionAllocator,
        oms: ExecutionEngine,
        broker: Broker,
    ) -> None:
        self._planner = planner
        self._validator = validator
        self._allocator = allocator
        self._oms = oms
        self._broker = broker

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        decision: TradeDecision,
        portfolio: PortfolioSnapshot,
        risk: RiskAnalysis,
        strategy: str = "simple",
        **kwargs: Any,
    ) -> OrchestratorReport:
        errors: list[str] = []
        warnings: list[str] = []
        broker_order_ids: list[str] = []
        total_filled_qty: int = 0
        total_filled_value: Decimal = Decimal(0)
        orders_submitted: int = 0
        orders_accepted: int = 0
        orders_rejected: int = 0

        execution_id = str(uuid4())

        # 1. Plan
        try:
            plan = self._planner.plan(decision, strategy=strategy, **kwargs)
        except Exception as exc:
            errors.append(f"Planning failed: {exc}")
            return self._build_report(
                execution_id=execution_id,
                errors=errors,
            )

        # 2. Validate
        required_capital = kwargs.get("required_capital")
        validation: ValidationResult = self._validator.validate(
            plan,
            self._broker,
            self._oms,
            required_capital=required_capital,
        )
        if not validation.valid:
            errors.extend(validation.issues)
            return self._build_report(
                execution_id=execution_id,
                errors=errors,
            )

        # 3. Allocate
        try:
            allocation: AllocationInstruction = self._allocator.allocate(
                decision,
                portfolio,
                risk,
            )
        except Exception as exc:
            errors.append(f"Allocation failed: {exc}")
            return self._build_report(
                execution_id=execution_id,
                errors=errors,
            )

        # 4. Submit orders via OMS
        for planned_order in plan.orders:
            orders_submitted += 1
            qty = planned_order.quantity
            if allocation.execution_quantity > 0:
                qty = min(qty, allocation.execution_quantity)

            request = ExecutionRequest(
                request_id=f"EXEC-{execution_id[:8]}-{orders_submitted}",
                symbol=planned_order.symbol,
                exchange=planned_order.exchange,
                side=planned_order.side,
                order_type=planned_order.order_type,
                quantity=qty,
                product=planned_order.product,
                validity=planned_order.validity,
                price=planned_order.price or allocation.execution_price,
                trigger_price=planned_order.trigger_price,
                tag=planned_order.tag,
                trade_decision_id="",
                portfolio_context_id="",
                risk_analysis_id="",
            )

            try:
                result = self._oms.execute(request)
                if result.success and result.order:
                    orders_accepted += 1
                    if result.order.broker_order_id:
                        broker_order_ids.append(result.order.broker_order_id)
                    if (
                        result.order.average_price is not None
                        and result.order.filled_quantity > 0
                    ):
                        total_filled_value += result.order.average_price * Decimal(
                            str(result.order.filled_quantity)
                        )
                        total_filled_qty += result.order.filled_quantity
                    if result.order.state == OrderState.REJECTED:
                        orders_rejected += 1
                else:
                    orders_rejected += 1
                    errors.extend(result.errors)
            except Exception as exc:
                errors.append(f"OMS execution failed for order: {exc}")
                orders_rejected += 1

        # 5. Calculate average price
        avg_price: Decimal | None = None
        if total_filled_qty > 0:
            avg_price = (total_filled_value / Decimal(str(total_filled_qty))).quantize(
                Decimal("0.01")
            )

        return OrchestratorReport(
            execution_id=execution_id,
            orders_submitted=orders_submitted,
            orders_accepted=orders_accepted,
            orders_rejected=orders_rejected,
            average_price=avg_price,
            broker_order_ids=tuple(broker_order_ids),
            timestamp=datetime.now(UTC),
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def generate_evidence(self, report: OrchestratorReport) -> Evidence:
        reasons: list[str] = []
        if report.orders_submitted > 0:
            reasons.append(
                f"Submitted {report.orders_submitted} order(s), "
                f"{report.orders_accepted} accepted, "
                f"{report.orders_rejected} rejected."
            )
        if report.average_price is not None:
            reasons.append(f"Average execution price: {report.average_price}")
        if report.broker_order_ids:
            reasons.append(f"Broker order IDs: {', '.join(report.broker_order_ids)}")
        if not reasons:
            reasons.append("No orders were executed.")

        score_value: float = 0.0
        confidence_value: float = 0.0
        if report.orders_submitted > 0:
            accepted_ratio = report.orders_accepted / report.orders_submitted
            score_value = accepted_ratio * 100.0
            confidence_value = accepted_ratio
            if (
                report.orders_accepted == report.orders_submitted
                or report.orders_accepted > 0
            ):
                signal = EvidenceSignal.NEUTRAL
            else:
                signal = EvidenceSignal.NEUTRAL
        else:
            signal = EvidenceSignal.NEUTRAL

        return Evidence(
            source="ExecutionOrchestrator",
            category=EvidenceCategory.EXECUTION,
            signal=signal,
            score=Score(score_value),
            confidence=Confidence(confidence_value),
            weight=1.0,
            reasons=tuple(reasons),
            warnings=report.warnings,
            metadata={
                "execution_id": report.execution_id,
                "orders_submitted": report.orders_submitted,
                "orders_accepted": report.orders_accepted,
                "orders_rejected": report.orders_rejected,
                "has_errors": len(report.errors) > 0,
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def generate_explanation(
        self,
        report: OrchestratorReport,
        plan: ExecutionPlan | None = None,
        validation: ValidationResult | None = None,
        allocation: AllocationInstruction | None = None,
    ) -> OrchestratorExplanation:
        validation_text = "All checks passed." if (validation is None or validation.valid) else f"Issues: {'; '.join(validation.issues)}" if validation else "No validation performed."  # fmt: skip

        planning_text = (
            f"Strategy: {plan.strategy}, {len(plan.orders)} order(s)"
            if plan
            else "No plan."
        )

        allocation_text = (
            f"Quantity: {allocation.execution_quantity}, Capital: {allocation.capital_allocated:.2f}"
            if allocation
            else "No allocation."
        )

        submission_text = (
            f"Submitted: {report.orders_submitted}, "
            f"Accepted: {report.orders_accepted}, "
            f"Rejected: {report.orders_rejected}"
        )

        broker_text = (
            f"Broker IDs: {', '.join(report.broker_order_ids)}"
            if report.broker_order_ids
            else "No broker responses."
        )

        if report.errors:
            summary = f"Execution failed: {'; '.join(report.errors)}"
        elif report.orders_rejected > 0:
            summary = f"Execution partially complete: {report.orders_accepted}/{report.orders_submitted} accepted."
        else:
            summary = (
                f"Execution completed: {report.orders_accepted} order(s) accepted."
            )

        return OrchestratorExplanation(
            summary=summary,
            validation=validation_text,
            planning=planning_text,
            allocation=allocation_text,
            submission=submission_text,
            broker_response=broker_text,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_report(
        execution_id: str,
        errors: list[str] | None = None,
    ) -> OrchestratorReport:
        return OrchestratorReport(
            execution_id=execution_id,
            errors=tuple(errors or []),
            timestamp=datetime.now(UTC),
        )
