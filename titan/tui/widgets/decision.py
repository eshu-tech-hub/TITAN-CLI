"""Reusable widgets for the Decision Journal screen."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.models import (
    DecisionEvidenceInfo,
    DecisionJournalEntry,
    DecisionQualificationInfo,
    DecisionReasonEntry,
    DecisionRiskInfo,
    DecisionSummaryInfo,
    DecisionTimelineEntry,
)
from titan.tui.widgets import markup_color


class DecisionSummaryWidget(Widget):
    """Displays the latest decision summary."""

    DEFAULT_CSS = """
    DecisionSummaryWidget {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    DecisionSummaryWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    DecisionSummaryWidget .card-row {
        height: 1;
    }
    DecisionSummaryWidget .decision-buy {
        color: $success;
        text-style: bold;
    }
    DecisionSummaryWidget .decision-sell {
        color: $error;
        text-style: bold;
    }
    DecisionSummaryWidget .decision-none {
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = DecisionSummaryInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Latest Decision Summary", classes="section-title")
        self._decision = Static("", classes="card-row")
        self._symbol = Static("", classes="card-row")
        self._details = Static("", classes="card-row")
        self._metrics = Static("", classes="card-row")
        yield self._title
        yield self._decision
        yield self._symbol
        yield self._details
        yield self._metrics

    def update_data(self, info: DecisionSummaryInfo) -> None:
        self._info = info
        if not hasattr(self, "_decision"):
            return

        dec_cls = "decision-none"
        if info.decision.lower() == "buy":
            dec_cls = "decision-buy"
        elif info.decision.lower() == "sell":
            dec_cls = "decision-sell"

        self._decision.update(
            f"[bold]Decision:[/bold] [{markup_color(dec_cls)}]{info.decision.upper()}[/]"
        )
        self._symbol.update(f"[bold]Symbol:[/bold] {info.symbol}")
        self._details.update(
            f"[bold]Action:[/bold] {info.trade_direction} {info.instrument_type}"
        )

        grade_str = "Yes" if info.institutional_grade else "No"
        self._metrics.update(
            f"[bold]Score:[/bold] {info.trade_score:.1f} | "
            f"[bold]Confidence:[/bold] {info.confidence * 100:.1f}% | "
            f"[bold]Inst. Grade:[/bold] {grade_str}"
        )

    def render(self) -> str:
        return ""


class EvidenceWidget(Widget):
    """Displays evidence supporting the decision."""

    DEFAULT_CSS = """
    EvidenceWidget {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    EvidenceWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    EvidenceWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = DecisionEvidenceInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Primary Evidence", classes="section-title")
        self._source = Static("", classes="card-row")
        self._signal = Static("", classes="card-row")
        self._metrics = Static("", classes="card-row")
        yield self._title
        yield self._source
        yield self._signal
        yield self._metrics

    def update_data(self, info: DecisionEvidenceInfo) -> None:
        self._info = info
        if not hasattr(self, "_source"):
            return

        self._source.update(f"[bold]Source:[/bold] {info.source} ({info.category})")
        self._signal.update(f"[bold]Signal:[/bold] {info.signal.upper()}")
        self._metrics.update(
            f"[bold]Score:[/bold] {info.score:.1f} | [bold]Weight:[/bold] {info.weight:.2f}"
        )

    def render(self) -> str:
        return ""


class RiskWidget(Widget):
    """Displays risk assessment for the decision."""

    DEFAULT_CSS = """
    RiskWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    RiskWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    RiskWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = DecisionRiskInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Risk Assessment", classes="section-title")
        self._summary = Static("", classes="card-row")
        yield self._title
        yield self._summary

    def update_data(self, info: DecisionRiskInfo) -> None:
        self._info = info
        if not hasattr(self, "_summary"):
            return
        self._summary.update(info.risk_summary)

    def render(self) -> str:
        return ""


class QualificationWidget(Widget):
    """Displays qualification explanation."""

    DEFAULT_CSS = """
    QualificationWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    QualificationWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    QualificationWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = DecisionQualificationInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Explanation", classes="section-title")
        self._summary = Static("", classes="card-row")
        yield self._title
        yield self._summary

    def update_data(self, info: DecisionQualificationInfo) -> None:
        self._info = info
        if not hasattr(self, "_summary"):
            return
        self._summary.update(info.explanation_summary)

    def render(self) -> str:
        return ""


class DecisionReasonsWidget(Widget):
    """Displays specific decision reasons as a dynamic list."""

    DEFAULT_CSS = """
    DecisionReasonsWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    DecisionReasonsWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    DecisionReasonsWidget .card-row {
        height: 1;
    }
    DecisionReasonsWidget .reason-info {
        color: $text;
    }
    DecisionReasonsWidget .reason-warning {
        color: $warning;
    }
    DecisionReasonsWidget .reason-critical {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._reasons: tuple[DecisionReasonEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Decision Reasons", classes="section-title")
        yield self._title

    def update_data(self, reasons: tuple[DecisionReasonEntry, ...]) -> None:
        self._reasons = reasons
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()

        if not reasons:
            empty = Static("  No specific reasons given.", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for r in reasons:
                cls = f"reason-{r.severity.lower()}"
                if cls not in ("reason-info", "reason-warning", "reason-critical"):
                    cls = "reason-info"

                row = Static(
                    f"  [{markup_color(cls)}][{r.reason_type.upper()}][/] {r.description}",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class TimelineWidget(Widget):
    """Displays decision timeline."""

    DEFAULT_CSS = """
    TimelineWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    TimelineWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    TimelineWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._timeline: tuple[DecisionTimelineEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Timeline", classes="section-title")
        yield self._title

    def update_data(self, timeline: tuple[DecisionTimelineEntry, ...]) -> None:
        self._timeline = timeline
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()

        if not timeline:
            empty = Static("  Timeline not recorded.", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for t in timeline:
                row = Static(
                    f"  {t.timestamp_str} | {t.step}: {t.status}", classes="card-row"
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class DecisionHistoryWidget(Widget):
    """Displays decision journal history."""

    DEFAULT_CSS = """
    DecisionHistoryWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    DecisionHistoryWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    DecisionHistoryWidget .card-row {
        height: 1;
    }
    DecisionHistoryWidget .dec-buy { color: $success; }
    DecisionHistoryWidget .dec-sell { color: $error; }
    DecisionHistoryWidget .dec-none { color: $text-muted; }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._history: tuple[DecisionJournalEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Decision History", classes="section-title")
        yield self._title

    def update_data(self, history: tuple[DecisionJournalEntry, ...]) -> None:
        self._history = history
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()

        if not history:
            empty = Static("  No journal entries.", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for entry in history:
                cls = "dec-none"
                if entry.decision.lower() == "buy":
                    cls = "dec-buy"
                elif entry.decision.lower() == "sell":
                    cls = "dec-sell"

                row = Static(
                    f"  {entry.timestamp_str} | {entry.symbol} | [{markup_color(cls)}]{entry.decision.upper()}[/]",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""
