import csv
from datetime import datetime, timezone
from pathlib import Path

from titan.decision.journal import DecisionJournal
from titan.trading.journal import TradeJournal
from titan.portfolio.analytics import PortfolioAnalytics
from titan.portfolio.models import ExistingPortfolio


class ReportingService:
    """Unified Reporting & Export Center.

    Generates standardized CSV and JSON exports across all journals
    and analytics subsystems.
    """

    def __init__(
        self,
        trade_journal: TradeJournal,
        decision_journal: DecisionJournal,
        portfolio_analytics: PortfolioAnalytics | None = None,
    ) -> None:
        self.trade_journal = trade_journal
        self.decision_journal = decision_journal
        self.portfolio_analytics = portfolio_analytics or PortfolioAnalytics()

    def export_trade_journal_csv(self, filepath: Path) -> None:
        """Export all trade journal entries to CSV."""
        entries = self.trade_journal.repository.list(page=1, page_size=100000)
        if not entries:
            return

        fields = [
            "TradeID",
            "DecisionID",
            "Symbol",
            "Direction",
            "Quantity",
            "EntryPrice",
            "ExitPrice",
            "NetPnL",
            "ExecutionStatus",
            "OpenTime",
            "CloseTime",
        ]

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fields)
            for e in entries:
                writer.writerow(
                    [
                        e.trade_id,
                        e.decision_id,
                        e.symbol,
                        e.direction,
                        e.quantity,
                        e.entry_price,
                        e.exit_price,
                        e.net_pnl,
                        e.execution_status.value,
                        e.open_time.isoformat() if e.open_time else "",
                        e.close_time.isoformat() if e.close_time else "",
                    ]
                )

    def export_decision_journal_csv(self, filepath: Path) -> None:
        """Export all decision journal entries to CSV."""
        entries = self.decision_journal.repository.list(page=1, page_size=100000)
        if not entries:
            return

        fields = ["DecisionID", "Symbol", "Action", "Confidence", "Status", "Timestamp"]

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fields)
            for e in entries:
                writer.writerow(
                    [
                        e.id,
                        e.symbol,
                        e.decision,
                        e.confidence,
                        "recorded",
                        e.timestamp.isoformat(),
                    ]
                )

    def export_portfolio_report(
        self, filepath: Path, portfolio: ExistingPortfolio
    ) -> None:
        """Export a comprehensive portfolio health report."""
        entries = self.trade_journal.repository.list(page=1, page_size=100000)
        self.portfolio_analytics.export_json(filepath, portfolio, entries)

    def generate_daily_summary(
        self, export_dir: Path, portfolio: ExistingPortfolio
    ) -> None:
        """Generate a bundle of all daily reports into a directory."""
        export_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

        self.export_trade_journal_csv(export_dir / f"trades_{date_str}.csv")
        self.export_decision_journal_csv(export_dir / f"decisions_{date_str}.csv")
        self.export_portfolio_report(
            export_dir / f"portfolio_{date_str}.json", portfolio
        )
