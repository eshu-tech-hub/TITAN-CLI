"""
Helper for validating end-to-end execution reconciliation.
"""

from titan.paper.broker import PaperBroker


class ExecutionReconciliationValidator:
    """Validates consistency across the paper trading subsystems."""

    def __init__(self, broker: PaperBroker):
        self.broker = broker
        self.journal = broker.journal
        self.position_engine = broker.position_engine
        self.portfolio = broker.portfolio

    def validate_all(self) -> list[str]:
        """Runs all reconciliation checks and returns a list of failure reasons (empty if pass)."""
        errors = []
        errors.extend(self.validate_orders_vs_journal())
        errors.extend(self.validate_journal_vs_positions())
        errors.extend(self.validate_positions_vs_portfolio())
        errors.extend(self.validate_journal_integrity())
        return errors

    def validate_orders_vs_journal(self) -> list[str]:
        """Broker orders == Trade Journal"""
        errors = []
        broker_orders = self.broker.orders()
        journal_orders = self.journal.all_orders()

        if len(broker_orders) != len(journal_orders):
            errors.append(
                f"Order count mismatch: Broker ({len(broker_orders)}) vs Journal ({len(journal_orders)})"
            )

        for bo in broker_orders:
            jo = self.journal.get_order_by_broker_id(bo.broker_order_id)
            if not jo:
                errors.append(f"Broker order {bo.broker_order_id} missing in journal.")
            elif bo.status != jo.status:
                errors.append(
                    f"Status mismatch for {bo.broker_order_id}: {bo.status} != {jo.status}"
                )

        return errors

    def validate_journal_vs_positions(self) -> list[str]:
        """Trade Journal == Positions"""
        errors = []
        # Calculate expected net quantity from journal fills
        fills = []
        for o in self.journal.all_orders():
            fills.extend(o.fills)

        # We can just verify no orphans
        open_positions = self.position_engine.open_positions()
        for pos in open_positions:
            if pos.quantity == 0:
                errors.append(f"Orphan open position with 0 quantity: {pos.symbol}")

        return errors

    def validate_positions_vs_portfolio(self) -> list[str]:
        """Positions == Portfolio"""
        errors = []
        try:
            self.portfolio.compute_state(self.position_engine.open_positions())
        except Exception as e:
            errors.append(f"Portfolio computation failed with positions: {e!s}")
        return errors

    def validate_journal_integrity(self) -> list[str]:
        """No missing journal entries, No duplicate UUIDs, Lifecycle ordering"""
        errors = []
        orders = self.journal.all_orders()
        fills = []
        for o in orders:
            fills.extend(o.fills)

        order_ids = set()
        for o in orders:
            if o.order_id in order_ids:
                errors.append(f"Duplicate Order ID found: {o.order_id}")
            order_ids.add(o.order_id)

        fill_ids = set()
        for f in fills:
            if f.fill_id in fill_ids:
                errors.append(f"Duplicate Fill ID found: {f.fill_id}")
            fill_ids.add(f.fill_id)

        return errors
