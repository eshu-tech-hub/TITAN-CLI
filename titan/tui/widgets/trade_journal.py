"""Widgets for the Trade Journal screen."""

from __future__ import annotations

from textual.widgets import DataTable, Static

from titan.tui.models import TradeHistoryEntry, TradeJournalSummaryInfo


class TradeSummaryWidget(Static):
    """Widget displaying key performance metrics and account health."""

    DEFAULT_CSS = """
    TradeSummaryWidget {
        height: 7;
        border: solid $primary;
        padding: 0 1;
    }
    .widget-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self):  # type: ignore[override]
        yield Static("Account Health & Summary", classes="widget-title")
        yield Static(id="ts-content")

    def update_data(self, summary: TradeJournalSummaryInfo) -> None:
        try:
            content = self.query_one("#ts-content", Static)
            text = f"""
[b]Today's PnL:[/b] {summary.today_pnl}   |   [b]Open Risk:[/b] {summary.open_risk}   |   [b]Exposure:[/b] {summary.exposure}
[b]Win %:[/b] {summary.win_percent}   |   [b]Current Drawdown:[/b] {summary.current_drawdown}
[b]Largest Winner:[/b] {summary.largest_winner}   |   [b]Largest Loser:[/b] {summary.largest_loser}
"""
            content.update(text.strip())
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass


class TradeHistoryWidget(Static):
    """Widget displaying the chronological history of executed trades."""

    DEFAULT_CSS = """
    TradeHistoryWidget {
        height: 1fr;
        border: solid $primary;
        padding: 0;
    }
    .widget-title {
        color: $primary;
        text-style: bold;
        padding: 0 1;
        border-bottom: solid $primary;
    }
    """

    def compose(self):  # type: ignore[override]
        yield Static("Trade History", classes="widget-title")
        self._table = DataTable(cursor_type="row")
        self._table.add_columns(
            "Trade ID",
            "Symbol",
            "Direction",
            "Qty",
            "Entry",
            "Exit",
            "Net PnL",
            "Status",
            "Open Time",
        )
        yield self._table

    def update_data(self, history: tuple[TradeHistoryEntry, ...]) -> None:
        try:
            self._table.clear()
            for entry in history:
                self._table.add_row(
                    entry.trade_id[:8],
                    entry.symbol,
                    entry.direction,
                    str(entry.quantity),
                    entry.entry_price,
                    entry.exit_price,
                    entry.net_pnl,
                    entry.status,
entry.open_time,
            )
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass
