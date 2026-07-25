"""Reusable sidebar navigation widget for the TITAN TUI application shell."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static


class SidebarWidget(Widget):
    """Sidebar with section list, keyboard/mouse navigation, and active highlight."""

    DEFAULT_CSS = """
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

    SECTIONS = [
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

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._active: str = "dashboard"
        self._rows: list[Static] = []

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

    @property
    def active(self) -> str:
        """Currently active section name."""
        return self._active

    def render(self) -> str:
        return ""
