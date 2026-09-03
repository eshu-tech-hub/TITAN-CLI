"""TITAN TUI application shell.

Provides the unified institutional desktop layout with:
- Persistent header bar
- Sidebar navigation
- Central content area (ContentSwitcher of mounted views)
- Persistent status bar
- Central refresh timer
- Screen router for navigation

Views are mounted inside the ContentSwitcher; navigation switches
``ContentSwitcher.current`` via the router. No Screen push/pop.
"""

from __future__ import annotations

import socket
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import ContentSwitcher

from titan.tui.router import ScreenRouter
from titan.tui.widgets.header import HeaderWidget
from titan.tui.widgets.sidebar import SidebarSelected, SidebarWidget
from titan.tui.widgets.status_bar import StatusBarWidget

if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.widget import Widget

REFRESH_INTERVAL = 1.0

SCREEN_CSS = """
#app-body {
    height: 1fr;
}
#app-content {
    width: 1fr;
    height: 1fr;
}
#app-content > * {
    width: 1fr;
    height: 1fr;
}
"""


class ShellApp(App):
    """TITAN institutional desktop application shell.

    Composes header, sidebar, content switcher, and status bar.
    Navigation is handled by ScreenRouter; the sidebar updates
    ``ContentSwitcher.current`` instead of pushing screens.
    Refresh is central.
    """

    TITLE = "TITAN OS"
    SUB_TITLE = "Trading Intelligence & Tactical Analysis Network"

    CSS = SCREEN_CSS

    BINDINGS: ClassVar[list] = [
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
        ("f12", "goto_help", "Help"),
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
        self._content_switcher: ContentSwitcher | None = None
        self._views: dict[str, Widget] = {}
        self._register_default_screens()

    def _register_default_screens(self) -> None:
        """Register the built-in screens so navigation works out of the box."""
        from titan.tui.screens import (
            AuditScreen,
            ConfigurationScreen,
            DashboardScreen,
            HelpScreen,
            LiveScreen,
            MarketScreen,
            MonitoringScreen,
            PaperScreen,
            RuntimeScreen,
        )
        from titan.tui.screens.decision import DecisionScreen
        from titan.tui.screens.decision_replay import DecisionReplayScreen
        from titan.tui.screens.trade_journal import TradeJournalScreen

        factories: dict[str, Callable[..., Any]] = {
            "dashboard": DashboardScreen,
            "runtime": RuntimeScreen,
            "paper": PaperScreen,
            "live_trading": LiveScreen,
            "monitoring": MonitoringScreen,
            "config": ConfigurationScreen,
            "market": MarketScreen,
            "decision": DecisionScreen,
            "decision_replay": DecisionReplayScreen,
            "trade_journal": TradeJournalScreen,
            "audit": AuditScreen,
            "help": HelpScreen,
        }
        for name, factory in factories.items():
            self.register_screen(name, factory)

    def register_screen(
        self,
        name: str,
        factory: Callable[..., Any],
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
        except Exception:  # noqa: BLE001
            return ""

    def _get_version(self) -> str:
        try:
            from titan.core import __version__ as ver  # type: ignore[attr-defined]

            return str(ver)
        except Exception:  # noqa: BLE001
            return "1.0.0"

    def _mount_views(self) -> None:
        """Create one view per registered screen and stash it by name."""
        self._views.clear()
        for name in self._router.screen_names:
            view = self._router.create(name)
            view.id = f"view-{name}"
            self._views[name] = view

    def compose(self) -> ComposeResult:
        self._header = HeaderWidget(id="app-header")
        self._sidebar = SidebarWidget(id="app-sidebar")
        self._status_bar = StatusBarWidget(id="app-status")
        with Horizontal(id="app-body"):
            yield self._sidebar
            self._content_switcher = ContentSwitcher(
                id="app-content", initial="view-dashboard"
            )
            with self._content_switcher:
                self._mount_views()
                yield from self._views.values()
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
            profile="development",
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
        self._apply_state_builders()
        self._navigate_to("dashboard")
        self.query_one("#app-sidebar", SidebarWidget).focus()

    def _apply_state_builders(self) -> None:
        """Push registered state builders into the mounted views."""
        for name, view in self._views.items():
            builder = self._state_builders.get(name)
            if builder is not None and hasattr(view, "set_state_builder"):
                view.set_state_builder(builder)

    def _set_active_view(self, name: str) -> None:
        """Switch the ContentSwitcher to the named view and focus it."""
        if self._content_switcher is None or name not in self._views:
            return
        self._content_switcher.current = f"view-{name}"
        view = self._views[name]
        if view.can_focus:
            view.focus()

    def _tick_refresh(self) -> None:
        """Central refresh tick — updates header clock, status bar time."""
        if self._header is not None:
            self._header.update_clock()
        if self._status_bar is not None:
            self._status_bar.update_time()

    def _navigate_to(self, name: str) -> None:
        """Navigate to a screen using the router."""
        try:
            self._router.navigate(name)
        except KeyError:
            return
        self._set_active_view(name)
        if self._sidebar is not None:
            self._sidebar.set_active(name)
        self._update_status_for_screen(name)

    def on_sidebar_selected(self, event: SidebarSelected) -> None:
        """Navigate when a sidebar section is selected."""
        self._navigate_to(event.name)

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
        """Refresh the current view."""
        if self._content_switcher is None:
            return
        current = self._content_switcher.visible_content
        if current is not None and hasattr(current, "action_refresh"):
            current.action_refresh()

    def action_go_back(self) -> None:
        """Navigate to the previous screen."""
        prev = self._router.go_back()
        if prev is not None:
            self._set_active_view(self._router.current)
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

    @property
    def content_switcher(self) -> ContentSwitcher | None:
        return self._content_switcher

    @property
    def views(self) -> dict[str, Widget]:
        return self._views
