from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

from titan.portfolio.replay_models import PortfolioReplayResult


class ReplayTimelineWidget(Static):
    """Displays a chronological list of events up to the replay snapshot."""

    replay: reactive[PortfolioReplayResult | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Replay Timeline", classes="widget-title")
            yield Static(id="timeline_data")

    def watch_replay(self, replay: PortfolioReplayResult | None) -> None:
        if replay and replay.timeline.events:
            lines = []
            # Show the last 10 events for context
            for event in replay.timeline.events[-10:]:
                time_str = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                lines.append(
                    f"[{time_str}] {event.status.value.upper()}: {event.reason}"
                )
            self.query_one("#timeline_data", Static).update("\n".join(lines))
        else:
            self.query_one("#timeline_data", Static).update("No events to display.")


class HistoricalAnalyticsWidget(Static):
    """Displays historical analytics specific to the replay point in time."""

    replay: reactive[PortfolioReplayResult | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Historical Analytics", classes="widget-title")
            yield Static(id="historical_data")

    def watch_replay(self, replay: PortfolioReplayResult | None) -> None:
        if replay:
            snap = replay.snapshot
            data = (
                f"Capital Used:   ${snap.snapshot.capital_used:,.2f}\n"
                f"Positions:      {snap.snapshot.position_count}\n"
                f"Max Drawdown:   ${snap.drawdown.max_drawdown:,.2f}\n"
                f"Win Rate:       {snap.performance.win_rate * 100:.1f}%\n"
                f"Profit Factor:  {snap.performance.profit_factor:.2f}"
            )
            self.query_one("#historical_data", Static).update(data)
        else:
            self.query_one("#historical_data", Static).update(
                "Loading historical data..."
            )
