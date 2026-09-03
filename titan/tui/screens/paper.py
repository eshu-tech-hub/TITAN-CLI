"""Paper Trading screen — session, portfolio, performance with auto-refresh."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from textual import work
from textual.containers import VerticalScroll
from textual.widgets import Static

from titan.cli.common import get_runtime_engine
from titan.tui.models import PaperScreenState
from titan.tui.widgets.paper import (
    AccountSummaryWidget,
    ActiveOrdersWidget,
    PaperSessionWidget,
    PerformanceWidget,
    PortfolioWidget,
    PositionWidget,
    TradeHistoryWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable

REFRESH_INTERVAL = 1.0


class PaperScreen(VerticalScroll):
    """Paper Trading view with five status widgets.

    Refreshes automatically every REFRESH_INTERVAL seconds.
    Data is read-only from all managers.
    """

    DEFAULT_CSS: ClassVar[str] = """
    PaperScreen {
        layout: vertical;
        padding: 1 2;
    }
    #paper-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        height: 1;
        margin-bottom: 1;
    }
    #refresh-indicator {
        text-align: right;
        height: 1;
        color: $text-muted;
        dock: top;
    }
    #widgets-container {
        height: 1fr;
    }
    """

    BINDINGS: ClassVar[list] = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("s", "start_paper", "Start Paper Session"),
        ("x", "stop_paper", "Stop Paper Session"),
        ("escape", "back", "Back"),
        ("page_up", "scroll_up", "Scroll Up"),
        ("page_down", "scroll_down", "Scroll Down"),
        ("home", "scroll_top", "Scroll Top"),
        ("end", "scroll_bottom", "Scroll Bottom"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = PaperScreenState()
        self._state_builder: Callable[[], PaperScreenState] | None = None
        self._session_widget: PaperSessionWidget | None = None
        self._account_widget: AccountSummaryWidget | None = None
        self._portfolio_widget: PortfolioWidget | None = None
        self._performance_widget: PerformanceWidget | None = None
        self._position_widget: PositionWidget | None = None
        self._orders_widget: ActiveOrdersWidget | None = None
        self._trades_widget: TradeHistoryWidget | None = None

    def compose(self):  # type: ignore[override]
        yield Static("Paper Trading", id="paper-title")
        yield Static("", id="refresh-indicator")
        with VerticalScroll(id="widgets-container"):
            self._session_widget = PaperSessionWidget(id="session-widget")
            self._account_widget = AccountSummaryWidget(id="account-widget")
            self._portfolio_widget = PortfolioWidget(id="portfolio-widget")
            self._position_widget = PositionWidget(id="position-widget")
            self._orders_widget = ActiveOrdersWidget(id="orders-widget")
            self._performance_widget = PerformanceWidget(id="performance-widget")
            self._trades_widget = TradeHistoryWidget(id="trades-widget")
            yield self._session_widget
            yield self._account_widget
            yield self._portfolio_widget
            yield self._position_widget
            yield self._orders_widget
            yield self._performance_widget
            yield self._trades_widget

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)

    def set_state_builder(self, builder: Callable[[], PaperScreenState]) -> None:
        self._state_builder = builder

    def _tick_refresh(self) -> None:
        self._refresh_state()

    def _refresh_state(self) -> None:
        if self._state_builder is not None:
            try:
                self._state = self._state_builder()
            except Exception:  # noqa: BLE001
                self._state = PaperScreenState()
        self._update_widgets()
        self._update_refresh_indicator()

    def _update_widgets(self) -> None:
        if self._session_widget is not None:
            self._session_widget.update_data(self._state.session)
        if self._account_widget is not None:
            self._account_widget.update_data(self._state.account)
        if self._portfolio_widget is not None:
            self._portfolio_widget.update_data(self._state.portfolio)
        if self._performance_widget is not None:
            self._performance_widget.update_data(self._state.performance)
        if self._position_widget is not None:
            self._position_widget.update_data(self._state.positions)
        if self._orders_widget is not None:
            self._orders_widget.update_data(self._state.orders)
        if self._trades_widget is not None:
            self._trades_widget.update_data(self._state.trades)

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#refresh-indicator", Static)
            now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display
            indicator.update(f"Last refresh: {now}")
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass

    def action_refresh(self) -> None:
        self._refresh_state()

    # ─── Paper session control ─────────────────────────────────

    @work(exclusive=True, thread=True)
    def _start_paper_worker(self) -> None:
        """Start the paper trading session off the asyncio event loop.

        engine.start() performs blocking broker/session I/O; running it in a
        Textual thread worker keeps the TUI responsive. Failures are surfaced
        via app.notify instead of dying silently in the worker thread.
        """
        try:
            engine = get_runtime_engine()
            engine.start()
        except Exception as exc:  # noqa: BLE001
            self.app.call_from_thread(
                self.app.notify,
                f"Engine Error: {exc!s}",
                title="Failure",
                severity="error",
            )
            self.app.call_from_thread(self._on_paper_start_failed, exc)
        else:
            self.app.call_from_thread(self._on_paper_started)

    @work(exclusive=True, thread=True)
    def _stop_paper_worker(self) -> None:
        """Stop the paper trading session off the asyncio event loop.

        Failures are surfaced via app.notify instead of dying silently in the
        worker thread.
        """
        try:
            engine = get_runtime_engine()
            engine.stop()
        except Exception as exc:  # noqa: BLE001
            self.app.call_from_thread(
                self.app.notify,
                f"Engine Error: {exc!s}",
                title="Failure",
                severity="error",
            )
            self.app.call_from_thread(self._on_paper_stop_failed, exc)
        else:
            self.app.call_from_thread(self._on_paper_stopped)

    def action_start_paper(self) -> None:
        """Start the paper trading session as the primary control node."""
        engine = get_runtime_engine()
        if engine.is_running:
            self.notify("Paper session is already running.", severity="warning")
            return
        self.notify("Starting paper session...")
        self._start_paper_worker()

    def action_stop_paper(self) -> None:
        """Stop the paper trading session gracefully."""
        engine = get_runtime_engine()
        if not engine.is_running:
            self.notify("Paper session is not running.", severity="warning")
            return
        self.notify("Stopping paper session...")
        self._stop_paper_worker()

    def _on_paper_started(self) -> None:
        self._refresh_state()
        self._update_engine_status_bar("Running")
        self.notify("Paper session started.", severity="information")

    def _on_paper_start_failed(self, exc: Exception) -> None:
        self._refresh_state()
        self.notify(f"Failed to start paper session: {exc}", severity="error")

    def _on_paper_stopped(self) -> None:
        self._refresh_state()
        self._update_engine_status_bar("Stopped")
        self.notify("Paper session stopped.", severity="information")

    def _on_paper_stop_failed(self, exc: Exception) -> None:
        self._refresh_state()
        self.notify(f"Failed to stop paper session: {exc}", severity="error")

    def _update_engine_status_bar(self, runtime_status: str) -> None:
        try:
            status_bar = getattr(self.app, "status_bar", None)
        except Exception:  # noqa: BLE001
            return
        if status_bar is not None:
            status_bar.update_data(runtime_status=runtime_status)

    def action_back(self) -> None:
        """Return to the previous view via the shell router."""
        try:
            self.app.action_go_back()
        except Exception:  # noqa: BLE001
            pass

    def action_scroll_up(self) -> None:
        """Scroll the container up."""
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:  # noqa: BLE001
            pass

    def action_scroll_down(self) -> None:
        """Scroll the container down."""
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:  # noqa: BLE001
            pass

    def action_scroll_top(self) -> None:
        """Scroll the container to the top."""
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:  # noqa: BLE001
            pass

    def action_scroll_bottom(self) -> None:
        """Scroll the container to the bottom."""
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:  # noqa: BLE001
            pass

    @property
    def state(self) -> PaperScreenState:
        return self._state
