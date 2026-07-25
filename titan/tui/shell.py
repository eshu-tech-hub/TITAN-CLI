"""TITAN TUI application shell.

Provides the unified institutional desktop layout with:
- Persistent header bar
- Sidebar navigation
- Central content area (screens)
- Persistent status bar
- Central refresh timer
- Screen router for navigation
"""

from __future__ import annotations

import socket
from typing import TYPE_CHECKING, Any

from textual.app import App
from textual.containers import Horizontal, Vertical
from textual.screen import Screen

from titan.tui.router import ScreenRouter
from titan.tui.widgets.header import HeaderWidget
from titan.tui.widgets.sidebar import SidebarWidget
from titan.tui.widgets.status_bar import StatusBarWidget

if TYPE_CHECKING:
    from collections.abc import Callable

REFRESH_INTERVAL = 1.0

SCREEN_CSS = """
#app-body {
    height: 1fr;
}
#app-content {
    width: 1fr;
    height: 1fr;
}
"""


class ShellApp(App):
    """TITAN institutional desktop application shell.

    Composes header, sidebar, content area, and status bar.
    Navigation is handled by ScreenRouter. Refresh is central.
    """

    TITLE = "TITAN OS"
    SUB_TITLE = "Trading Intelligence & Tactical Analysis Network"

    CSS = SCREEN_CSS

    BINDINGS = [
        ("f1", "goto_dashboard", "Dashboard"),
        ("f2", "goto_runtime", "Runtime"),
        ("f3", "goto_paper", "Paper"),
        ("f5", "goto_live", "Live"),
        ("f6", "goto_monitoring", "Monitoring"),
        ("f7", "goto_config", "Config & Deploy"),
        ("f8", "goto_market", "Market Intel"),
        ("f9", "goto_decision", "Decision"),
        ("f10", "goto_decision_replay", "Replay"),
        ("f11", "goto_trade_journal", "Trade Jnl"),
        ("f12", "goto_logs", "Logs & Audit"),
        ("?", "goto_help", "Help"),
        ("h", "goto_help", "Help"),
        ("ctrl+r", "refresh", "Refresh"),
        ("ctrl+q", "quit", "Quit"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._router = ScreenRouter(default="dashboard")
        self._state_builders: dict[str, Callable[..., Any]] = {}
        self._header: HeaderWidget | None = None
        self._sidebar: SidebarWidget | None = None
        self._status_bar: StatusBarWidget | None = None
        self._content_container: Vertical | None = None

    def register_screen(
        self,
        name: str,
        factory: Callable[..., Screen],
        *,
        is_default: bool = False,
    ) -> None:
        """Register a screen factory with the router."""
        self._router.register(name, factory, is_default=is_default)

    def set_state_builder(self, name: str, builder: Callable[..., Any]) -> None:
        """Register a state builder for a screen."""
        self._state_builders[name] = builder

    def _get_hostname(self) -> str:
        try:
            return socket.gethostname()
        except Exception:
            return ""

    def _get_version(self) -> str:
        try:
            from titan.core import __version__ as ver  # type: ignore[attr-defined]

            return str(ver)
        except Exception:
            return "1.0.0"

    def compose(self):  # type: ignore[override]
        self._header = HeaderWidget(id="app-header")
        self._sidebar = SidebarWidget(id="app-sidebar")
        self._status_bar = StatusBarWidget(id="app-status")
        with Horizontal(id="app-body"):
            yield self._sidebar
            with Vertical(id="app-content"):
                yield from ()
        yield self._header
        yield self._status_bar

    def on_mount(self) -> None:
        """Initialize the shell on mount."""
        assert self._header is not None
        assert self._sidebar is not None
        assert self._status_bar is not None
        self._header.update_data(
            version=self._get_version(),
            hostname=self._get_hostname(),
            profile="default",
        )
        self._sidebar.set_active("dashboard")
        self._status_bar.update_data(
            environment="Development",
            runtime_status="Stopped",
            broker_status="Disconnected",
            mode="Paper",
            refresh_interval=REFRESH_INTERVAL,
        )
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)
        self._navigate_to("dashboard")

    def _tick_refresh(self) -> None:
        """Central refresh tick — updates header clock, status bar time."""
        if self._header is not None:
            self._header.update_clock()
        if self._status_bar is not None:
            self._status_bar.update_time()

    def _navigate_to(self, name: str) -> None:
        """Navigate to a screen using the router."""
        try:
            screen = self._router.navigate(name)
            if name in self._state_builders:
                builder = self._state_builders[name]
                if hasattr(screen, "set_state_builder"):
                    screen.set_state_builder(builder)
            self.push_screen(screen)
            if self._sidebar is not None:
                self._sidebar.set_active(name)
            self._update_status_for_screen(name)
        except KeyError:
            pass

    def _update_status_for_screen(self, name: str) -> None:
        """Update the status bar mode based on the active screen."""
        mode_map = {
            "dashboard": "Overview",
            "runtime": "Runtime",
            "paper": "Paper",
            "market": "Market Intel",
            "live_trading": "Live",
            "monitoring": "Monitoring & Alerting",
            "logs": "Logs & Audit",
            "audit": "Logs & Audit",
            "config": "Configuration & Deployment",
            "decision": "Decision Journal",
            "decision_replay": "Decision Replay",
            "trade_journal": "Trade Journal",
            "help": "Help",
        }
        mode = mode_map.get(name, name)
        if self._status_bar is not None:
            self._status_bar.update_data(mode=mode)

    def _action_goto(self, name: str) -> None:
        """Navigate to a named screen."""
        self._navigate_to(name)

    def action_goto_dashboard(self) -> None:
        self._action_goto("dashboard")

    def action_goto_runtime(self) -> None:
        self._action_goto("runtime")

    def action_goto_paper(self) -> None:
        self._action_goto("paper")

    def action_goto_market(self) -> None:
        self._action_goto("market")

    def action_goto_live(self) -> None:
        self._action_goto("live_trading")

    def action_goto_monitoring(self) -> None:
        self._action_goto("monitoring")

    def action_goto_logs(self) -> None:
        self._action_goto("logs")

    def action_goto_audit(self) -> None:
        self._action_goto("audit")

    def action_goto_decision(self) -> None:
        self._action_goto("decision")

    def action_goto_decision_replay(self) -> None:
        self._action_goto("decision_replay")

    def action_goto_trade_journal(self) -> None:
        self._action_goto("trade_journal")

    def action_goto_config(self) -> None:
        self._action_goto("config")

    def action_goto_deployment(self) -> None:
        self._action_goto("deployment")

    def action_goto_help(self) -> None:
        self._action_goto("help")

    def action_refresh(self) -> None:
        """Refresh the current screen."""
        current = self.screen
        if hasattr(current, "action_refresh"):
            current.action_refresh()

    def action_go_back(self) -> None:
        """Navigate to the previous screen."""
        prev = self._router.go_back()
        if prev is not None:
            self.push_screen(prev)
            if self._sidebar is not None:
                self._sidebar.set_active(self._router.current)
            self._update_status_for_screen(self._router.current)

    @property
    def router(self) -> ScreenRouter:
        return self._router

    @property
    def header(self) -> HeaderWidget | None:
        return self._header

    @property
    def sidebar(self) -> SidebarWidget | None:
        return self._sidebar

    @property
    def status_bar(self) -> StatusBarWidget | None:
        return self._status_bar
