import uuid
from datetime import UTC, datetime
from typing import Any

from titan.trading.journal import TradeJournalEntry, TradeLifecycleState


class TradeJournalFactory:
    """
    Factory for constructing journal entries without bleeding instantiation logic
    into runtime orchestration components.
    """

    @staticmethod
    def from_pipeline_report(
        report: Any, runtime_session_id: str
    ) -> list[tuple[TradeJournalEntry, str]]:
        """
        Create initial TradeJournal entries from a pipeline execution report.

        Args:
            report: The PipelineReport containing execution results.
            runtime_session_id: The session ID of the current runtime.

        Returns:
            A list of tuples containing (TradeJournalEntry, broker_id)
        """
        entries = []
        for broker_id in report.broker_order_ids:
            trade_id = str(uuid.uuid4())
            entry = TradeJournalEntry(
                trade_id=trade_id,
                decision_id=str(uuid.uuid4()),  # Derived or mocked for simulation
                runtime_session_id=runtime_session_id,
                symbol=report.symbol,
                exchange=report.exchange,
                direction=report.decision_action or "UNKNOWN",
                quantity=1,
                entry_price=0.0,
                exit_price=0.0,
                gross_pnl=0.0,
                net_pnl=0.0,
                fees=0.0,
                slippage=0.0,
                strategy="Unknown",
                tags=(),
                decision_status="executed",
                execution_status=TradeLifecycleState.SUBMITTED,
                open_time=datetime.now(UTC),
                close_time=None,
                lifecycle_events=(),
            )
            entries.append((entry, broker_id))
        return entries
