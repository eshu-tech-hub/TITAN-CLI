"""Reusable widgets for the Decision Replay screen."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.models import (
    ReplayEvidenceInfo,
    ReplayMetadataInfo,
    ReplayQualificationInfo,
    ReplayReasonEntry,
    ReplayRiskInfo,
    ReplaySummaryInfo,
    ReplayTimelineEntry,
)
from titan.tui.widgets import markup_color


class ReplaySummaryWidget(Widget):
    """Displays the selected replay decision summary."""

    DEFAULT_CSS = """
    ReplaySummaryWidget {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ReplaySummaryWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ReplaySummaryWidget .card-row {
        height: 1;
    }
    ReplaySummaryWidget .decision-buy {
        color: $success;
        text-style: bold;
    }
    ReplaySummaryWidget .decision-sell {
        color: $error;
        text-style: bold;
    }
    ReplaySummaryWidget .decision-none {
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = ReplaySummaryInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Replay Decision Summary", classes="section-title")
        self._decision = Static("", classes="card-row")
        self._symbol = Static("", classes="card-row")
        self._details = Static("", classes="card-row")
        self._metrics = Static("", classes="card-row")
        yield self._title
        yield self._decision
        yield self._symbol
        yield self._details
        yield self._metrics

    def update_data(self, info: ReplaySummaryInfo) -> None:
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


class ReplayEvidenceWidget(Widget):
    """Displays evidence for the replayed decision."""

    DEFAULT_CSS = """
    ReplayEvidenceWidget {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ReplayEvidenceWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ReplayEvidenceWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = ReplayEvidenceInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Primary Evidence", classes="section-title")
        self._source = Static("", classes="card-row")
        self._signal = Static("", classes="card-row")
        self._metrics = Static("", classes="card-row")
        yield self._title
        yield self._source
        yield self._signal
        yield self._metrics

    def update_data(self, info: ReplayEvidenceInfo) -> None:
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


class ReplayRiskWidget(Widget):
    """Displays risk assessment for the replayed decision."""

    DEFAULT_CSS = """
    ReplayRiskWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ReplayRiskWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ReplayRiskWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = ReplayRiskInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Risk Assessment", classes="section-title")
        self._summary = Static("", classes="card-row")
        yield self._title
        yield self._summary

    def update_data(self, info: ReplayRiskInfo) -> None:
        self._info = info
        if not hasattr(self, "_summary"):
            return
        self._summary.update(info.risk_summary)

    def render(self) -> str:
        return ""


class ReplayQualificationWidget(Widget):
    """Displays qualification explanation for the replayed decision."""

    DEFAULT_CSS = """
    ReplayQualificationWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ReplayQualificationWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ReplayQualificationWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = ReplayQualificationInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Explanation", classes="section-title")
        self._summary = Static("", classes="card-row")
        yield self._title
        yield self._summary

    def update_data(self, info: ReplayQualificationInfo) -> None:
        self._info = info
        if not hasattr(self, "_summary"):
            return
        self._summary.update(info.explanation_summary)

    def render(self) -> str:
        return ""


class ReplayReasonsWidget(Widget):
    """Displays specific decision reasons as a dynamic list."""

    DEFAULT_CSS = """
    ReplayReasonsWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ReplayReasonsWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ReplayReasonsWidget .card-row {
        height: 1;
    }
    ReplayReasonsWidget .reason-info {
        color: $text;
    }
    ReplayReasonsWidget .reason-warning {
        color: $warning;
    }
    ReplayReasonsWidget .reason-critical {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._reasons: tuple[ReplayReasonEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Decision Reasons", classes="section-title")
        yield self._title

    def update_data(self, reasons: tuple[ReplayReasonEntry, ...]) -> None:
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


class ReplayTimelineWidget(Widget):
    """Displays replayed decision timeline."""

    DEFAULT_CSS = """
    ReplayTimelineWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ReplayTimelineWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ReplayTimelineWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._timeline: tuple[ReplayTimelineEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Timeline", classes="section-title")
        yield self._title

    def update_data(self, timeline: tuple[ReplayTimelineEntry, ...]) -> None:
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


class ReplayMetadataWidget(Widget):
    """Displays metadata about the replay context (e.g. index/total)."""

    DEFAULT_CSS = """
    ReplayMetadataWidget {
        height: auto;
        min-height: 3;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $secondary;
    }
    ReplayMetadataWidget .section-title {
        text-style: bold;
        color: $secondary;
        margin-bottom: 1;
    }
    ReplayMetadataWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = ReplayMetadataInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Replay Controls", classes="section-title")
        self._status = Static("", classes="card-row")
        yield self._title
        yield self._status

    def update_data(self, info: ReplayMetadataInfo) -> None:
        self._info = info
        if not hasattr(self, "_status"):
            return

        has_prev_str = "Yes" if info.has_previous else "No"
        has_next_str = "Yes" if info.has_next else "No"

        self._status.update(
            f"Decision {info.current_index} of {info.total_decisions} | "
            f"Prev: {has_prev_str} (Use '[' or 'p') | Next: {has_next_str} (Use ']' or 'n')"
        )

    def render(self) -> str:
        return ""
