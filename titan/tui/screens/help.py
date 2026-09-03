"""Help screen — keyboard shortcuts, navigation guide, and reference."""

from __future__ import annotations

from typing import Any, ClassVar

from textual.containers import VerticalScroll
from textual.widgets import Static

SHORTCUTS = [
    (
        "Global Navigation",
        [
            ("F1", "Dashboard"),
            ("F2", "Runtime"),
            ("F3", "Paper Trading"),
            ("F4", "Live Trading"),
            ("F5", "Monitoring"),
            ("F6", "Alerts"),
            ("F7", "Logs"),
            ("F8", "Audit"),
            ("F9", "Configuration"),
            ("F10", "Deployment"),
            ("F11", "Help"),
        ],
    ),
    (
        "Controls",
        [
            ("Ctrl+R", "Refresh"),
            ("Ctrl+Q", "Quit"),
            ("Escape", "Previous Screen"),
            ("Up/Down", "Navigate"),
            ("Enter", "Select"),
        ],
    ),
    (
        "Screen-Specific",
        [
            ("Page Up/Down", "Scroll content"),
            ("Home/End", "Jump to top/bottom"),
            ("R", "Refresh (single screen)"),
            ("Q", "Quit"),
        ],
    ),
]


class HelpScreen(VerticalScroll):
    """Full-screen help view with keyboard shortcuts and navigation reference."""

    BINDINGS: ClassVar[list] = [
        ("escape", "back", "Back"),
        ("q", "back", "Back"),
        ("f11", "back", "Back"),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        layout: vertical;
        padding: 1 2;
    }
    #help-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        height: 1;
        margin-bottom: 1;
    }
    #help-content {
        height: 1fr;
    }
    .help-section {
        text-style: bold;
        color: $primary;
        height: 1;
        margin-top: 1;
    }
    .help-row {
        height: 1;
        padding: 0 2;
    }
    .help-footer {
        height: 1;
        color: $text-muted;
        text-align: center;
        dock: bottom;
        border-top: solid $primary;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def compose(self):  # type: ignore[override]
        yield Static("Help", id="help-title")
        with VerticalScroll(id="help-content"):
            for section_name, bindings in SHORTCUTS:
                yield Static(section_name, classes="help-section")
                for key, desc in bindings:
                    yield Static(
                        f"  [bold]{key}[/bold]  —  {desc}",
                        classes="help-row",
                    )
        yield Static("Press Escape or Q to return", classes="help-footer")

    def action_back(self) -> None:
        """Return to previous view via the shell router."""
        try:
            self.app.action_go_back()
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass
