"""Reusable sidebar navigation widget for the TITAN TUI application shell."""

from __future__ import annotations

from typing import Any, ClassVar

from textual import events
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static


class SidebarSelected(Message):
    """Posted when the user activates a sidebar section."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


class SidebarWidget(Widget):
    """Sidebar with section list, keyboard/mouse navigation, and active highlight.

    The widget is focusable: the up/down arrow keys move the active highlight
    between sections and Enter activates the highlighted section. Clicking a
    section also activates it. Every activation posts a SidebarSelected message.
    """

    can_focus = True

    DEFAULT_CSS: ClassVar[str] = """
    SidebarWidget {
        width: 24;
        background: $surface;
        border-right: solid $primary;
        padding: 0;
        layout: vertical;
    }
    .sidebar-section {
        height: 1;
        padding: 0 1;
    }
    .sidebar-section-active {
        background: $primary;
        color: $text;
        text-style: bold;
    }
    .sidebar-section-inactive {
        color: $text-muted;
    }
    .sidebar-title {
        height: 1;
        padding: 0 1;
        text-style: bold;
        color: $primary;
        border-bottom: solid $primary;
    }
    .sidebar-spacer {
        height: 1fr;
    }
    .sidebar-footer {
        height: 1;
        padding: 0 1;
        color: $text-muted;
        border-top: solid $primary;
    }
    """

    SECTIONS: ClassVar[list] = [
        ("Dashboard", "dashboard"),
        ("Runtime", "runtime"),
        ("Paper Trading", "paper"),
        ("─" * 20, None),
        ("Live Trading", "live_trading"),
        ("Monitoring & Alerting", "monitoring"),
        ("─" * 20, None),
        ("Config & Deployment", "config"),
        ("Market Intel", "market"),
        ("Decision Journal", "decision"),
        ("Decision Replay", "decision_replay"),
        ("Trade Journal", "trade_journal"),
        ("─" * 20, None),
        ("Logs", "logs"),
        ("Audit", "audit"),
        ("─" * 20, None),
        ("Help", "help"),
    ]

    BINDINGS: ClassVar[list] = [
        ("up", "select_previous", "Previous"),
        ("down", "select_next", "Next"),
        ("enter", "activate", "Go"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._active: str = "dashboard"
        self._rows: list[Static] = []
        self._names: list[str] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("TITAN OS", classes="sidebar-title")
        yield self._title
        for label, key in self.SECTIONS:
            if key is None:
                yield Static(label, classes="sidebar-section sidebar-section-inactive")
            else:
                cls = (
                    "sidebar-section sidebar-section-active"
                    if key == self._active
                    else "sidebar-section sidebar-section-inactive"
                )
                row = Static(f"  {label}", classes=cls, id=f"sidebar-{key}")
                self._rows.append(row)
                self._names.append(key)
                yield row
        yield Static("", classes="sidebar-spacer")
        self._footer = Static("F1 Help", classes="sidebar-footer")
        yield self._footer

    def set_active(self, name: str) -> None:
        """Set the active section by screen name."""
        self._active = name
        if not self._rows:
            return
        for row in self._rows:
            row_id = row.id or ""
            section_name = row_id.replace("sidebar-", "")
            if section_name == name:
                row.add_class("sidebar-section-active")
                row.remove_class("sidebar-section-inactive")
            else:
                row.remove_class("sidebar-section-active")
                row.add_class("sidebar-section-inactive")

    def _select_offset(self, offset: int) -> None:
        """Move the active highlight by a relative row offset."""
        if not self._names:
            return
        try:
            index = self._names.index(self._active)
        except ValueError:
            index = 0
        self.set_active(self._names[(index + offset) % len(self._names)])

    def action_select_previous(self) -> None:
        self._select_offset(-1)

    def action_select_next(self) -> None:
        self._select_offset(1)

    def action_activate(self) -> None:
        self.post_message(SidebarSelected(self._active))

    def on_click(self, event: events.Click) -> None:
        widget_id = getattr(event.widget, "id", None) or ""
        if not widget_id.startswith("sidebar-"):
            return
        section = widget_id[len("sidebar-") :]
        if section in self._names:
            self.set_active(section)
            self.post_message(SidebarSelected(section))

    @property
    def active(self) -> str:
        """Currently active section name."""
        return self._active

    def render(self) -> str:
        return ""
