import ast
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from titan.core.evidence import Evidence, EvidenceCategory, EvidenceSignal
from titan.options.analytics import (
    BackwardationAnalyzer,
    BackwardationResult,
    CalendarAnalyzer,
    CalendarResult,
    ContangoAnalyzer,
    ContangoResult,
    MarketBias,
    TermStructureAnalysis,
    TermStructureAnalyzer,
    TermStructureExpiry,
    TermStructureExplanation,
    TermStructureShape,
    TermStructureSnapshot,
    TermStructureStrength,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 7, 2, 9, 30)


def make_expiry(
    days_out: int,
    *,
    atm_iv: float | None = None,
    average_iv: float | None = None,
) -> TermStructureExpiry:
    return TermStructureExpiry(
        expiry=NOW + timedelta(days=days_out),
        atm_iv=atm_iv,
        average_iv=average_iv,
    )


def make_snapshot(
    expiries: tuple[TermStructureExpiry, ...],
    *,
    underlying: str = "SPY",
) -> TermStructureSnapshot:
    return TermStructureSnapshot(
        underlying=underlying,
        timestamp=NOW,
        expiries=expiries,
    )


def contango_snapshot() -> TermStructureSnapshot:
    return make_snapshot(
        expiries=(
            make_expiry(30, atm_iv=0.20),
            make_expiry(60, atm_iv=0.21),
            make_expiry(90, atm_iv=0.22),
            make_expiry(180, atm_iv=0.22),
        ),
    )


def backwardation_snapshot() -> TermStructureSnapshot:
    return make_snapshot(
        expiries=(
            make_expiry(30, atm_iv=0.22),
            make_expiry(60, atm_iv=0.21),
            make_expiry(90, atm_iv=0.20),
            make_expiry(180, atm_iv=0.20),
        ),
    )


def flat_snapshot() -> TermStructureSnapshot:
    return make_snapshot(
        expiries=(
            make_expiry(30, atm_iv=0.20),
            make_expiry(60, atm_iv=0.201),
            make_expiry(90, atm_iv=0.202),
            make_expiry(180, atm_iv=0.203),
        ),
    )


def event_premium_snapshot() -> TermStructureSnapshot:
    return make_snapshot(
        expiries=(
            make_expiry(30, atm_iv=0.20),
            make_expiry(60, atm_iv=0.35),
            make_expiry(90, atm_iv=0.22),
            make_expiry(180, atm_iv=0.24),
        ),
    )


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestTermStructureExpiry:
    def test_defaults(self) -> None:
        expiry = TermStructureExpiry(expiry=NOW)

        assert expiry.expiry == NOW
        assert expiry.atm_iv is None
        assert expiry.average_iv is None
        assert expiry.metadata == {}

    def test_frozen(self) -> None:
        expiry = TermStructureExpiry(expiry=NOW, atm_iv=0.20)

        with pytest.raises(AttributeError):
            expiry.atm_iv = 0.25  # type: ignore[misc]


class TestTermStructureSnapshot:
    def test_defaults(self) -> None:
        snapshot = make_snapshot(expiries=())

        assert snapshot.underlying == "SPY"
        assert snapshot.expiries == ()

    def test_frozen(self) -> None:
        snapshot = make_snapshot(expiries=())

        with pytest.raises(AttributeError):
            snapshot.underlying = "QQQ"  # type: ignore[misc]


class TestTermStructureAnalysisModel:
    def test_neutral_placeholder(self) -> None:
        analysis = TermStructureAnalysis.neutral_placeholder()

        assert analysis.shape is TermStructureShape.UNKNOWN
        assert analysis.strength is TermStructureStrength.UNKNOWN
        assert analysis.front_iv is None
        assert analysis.back_iv is None
        assert analysis.overall_bias is MarketBias.UNKNOWN
        assert analysis.confidence == 0.0
        assert "Term structure data unavailable" in analysis.warnings[0]

    def test_frozen(self) -> None:
        analysis = TermStructureAnalysis.neutral_placeholder()

        with pytest.raises(AttributeError):
            analysis.confidence = 0.5  # type: ignore[misc]

    def test_enum_values(self) -> None:
        assert TermStructureShape.NORMAL.value == "normal"
        assert TermStructureShape.CONTANGO.value == "contango"
        assert TermStructureShape.BACKWARDATION.value == "backwardation"
        assert TermStructureShape.FLAT.value == "flat"
        assert TermStructureShape.INVERTED.value == "inverted"
        assert TermStructureShape.UNKNOWN.value == "unknown"

        assert TermStructureStrength.LOW.value == "low"
        assert TermStructureStrength.MEDIUM.value == "medium"
        assert TermStructureStrength.HIGH.value == "high"
        assert TermStructureStrength.EXTREME.value == "extreme"
        assert TermStructureStrength.UNKNOWN.value == "unknown"


class TestCalendarResultModel:
    def test_defaults(self) -> None:
        result = CalendarResult()

        assert result.front_iv is None
        assert result.back_iv is None
        assert result.calendar_spread is None
        assert result.confidence == 0.0

    def test_frozen(self) -> None:
        result = CalendarResult()

        with pytest.raises(AttributeError):
            result.front_iv = 0.20  # type: ignore[misc]


class TestContangoResultModel:
    def test_defaults(self) -> None:
        result = ContangoResult()

        assert result.is_contango is False
        assert result.strength is TermStructureStrength.UNKNOWN

    def test_frozen(self) -> None:
        result = ContangoResult()

        with pytest.raises(AttributeError):
            result.is_contango = True  # type: ignore[misc]


class TestBackwardationResultModel:
    def test_defaults(self) -> None:
        result = BackwardationResult()

        assert result.is_backwardation is False
        assert result.stress_indicator is False

    def test_frozen(self) -> None:
        result = BackwardationResult()

        with pytest.raises(AttributeError):
            result.is_backwardation = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CalendarAnalyzer tests
# ---------------------------------------------------------------------------


class TestCalendarAnalyzer:
    def test_missing_expiries(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = make_snapshot(expiries=())

        result = analyzer.analyze(snapshot)

        assert result.front_iv is None
        assert result.back_iv is None
        assert "no expiry" in result.warnings[0].lower()

    def test_single_expiry(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = make_snapshot(
            expiries=(make_expiry(30, atm_iv=0.20),),
        )

        result = analyzer.analyze(snapshot)

        assert result.front_iv is None
        assert result.back_iv is None
        assert "insufficient expiries" in result.warnings[0].lower()

    def test_two_expiries(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = make_snapshot(
            expiries=(
                make_expiry(30, atm_iv=0.20),
                make_expiry(60, atm_iv=0.25),
            ),
        )

        result = analyzer.analyze(snapshot)

        assert result.front_iv == 0.20
        assert result.back_iv == 0.25
        assert result.calendar_spread == pytest.approx(0.05, abs=1e-10)
        assert result.curve_slope == pytest.approx(0.05, abs=1e-10)

    def test_multiple_expiries_contango(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = contango_snapshot()

        result = analyzer.analyze(snapshot)

        assert result.front_iv == 0.20
        assert result.back_iv == 0.22
        assert result.calendar_spread == pytest.approx(0.02, abs=1e-10)
        assert result.curve_slope == pytest.approx(0.02 / 3)
        assert result.max_discontinuity is not None

    def test_multiple_expiries_backwardation(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = backwardation_snapshot()

        result = analyzer.analyze(snapshot)

        assert result.front_iv == 0.22
        assert result.back_iv == 0.20
        assert result.calendar_spread == pytest.approx(-0.02, abs=1e-10)

    def test_event_premium(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = event_premium_snapshot()

        result = analyzer.analyze(snapshot)

        assert result.event_premium is not None
        assert result.event_premium > 0.02

    def test_no_event_premium_flat(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = flat_snapshot()

        result = analyzer.analyze(snapshot)

        assert result.event_premium is None

    def test_average_iv_fallback(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = make_snapshot(
            expiries=(
                make_expiry(30, average_iv=0.20),
                make_expiry(60, average_iv=0.25),
            ),
        )

        result = analyzer.analyze(snapshot)

        assert result.front_iv == 0.20
        assert result.back_iv == 0.25

    def test_atm_iv_preferred_over_average(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = make_snapshot(
            expiries=(
                make_expiry(30, atm_iv=0.18, average_iv=0.20),
                make_expiry(60, atm_iv=0.23, average_iv=0.25),
            ),
        )

        result = analyzer.analyze(snapshot)

        assert result.front_iv == 0.18
        assert result.back_iv == 0.23

    def test_missing_iv_skipped(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = make_snapshot(
            expiries=(
                make_expiry(30, atm_iv=0.20),
                make_expiry(60),
                make_expiry(90, atm_iv=0.28),
            ),
        )

        result = analyzer.analyze(snapshot)

        assert result.front_iv == 0.20
        assert result.back_iv == 0.28
        assert "missing iv" in result.warnings[0].lower()

    def test_confidence_reliable(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = contango_snapshot()

        result = analyzer.analyze(snapshot)

        assert result.confidence > 0.5

    def test_confidence_low_with_sparse_data(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = make_snapshot(
            expiries=(
                make_expiry(30, atm_iv=0.20),
                make_expiry(60, atm_iv=0.25),
            ),
        )

        result = analyzer.analyze(snapshot)

        assert result.confidence > 0.0
        assert result.confidence < 0.7

    def test_all_ivs_none(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = make_snapshot(
            expiries=(
                make_expiry(30),
                make_expiry(60),
            ),
        )

        result = analyzer.analyze(snapshot)

        assert result.front_iv is None
        assert result.confidence == 0.0

    def test_non_snapshot_input_raises(self) -> None:
        analyzer = CalendarAnalyzer()

        with pytest.raises(TypeError, match="snapshot must be a TermStructureSnapshot"):
            analyzer.analyze("not-a-snapshot")  # type: ignore[arg-type]

    def test_average_slope(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = contango_snapshot()

        result = analyzer.analyze(snapshot)

        assert result.average_slope is not None
        assert result.average_slope > 0

    def test_max_discontinuity(self) -> None:
        analyzer = CalendarAnalyzer()
        snapshot = make_snapshot(
            expiries=(
                make_expiry(30, atm_iv=0.18),
                make_expiry(60, atm_iv=0.25),
                make_expiry(90, atm_iv=0.26),
            ),
        )

        result = analyzer.analyze(snapshot)

        assert result.max_discontinuity is not None
        assert result.max_discontinuity == 0.07


# ---------------------------------------------------------------------------
# ContangoAnalyzer tests
# ---------------------------------------------------------------------------


class TestContangoAnalyzer:
    def test_contango_detected(self) -> None:
        analyzer = ContangoAnalyzer()
        calendar = CalendarResult(calendar_spread=0.05, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.is_contango is True
        assert result.confidence > 0.5

    def test_no_contango(self) -> None:
        analyzer = ContangoAnalyzer()
        calendar = CalendarResult(calendar_spread=-0.03, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.is_contango is False

    def test_strength_low(self) -> None:
        analyzer = ContangoAnalyzer()
        calendar = CalendarResult(calendar_spread=0.015, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.strength is TermStructureStrength.LOW

    def test_strength_medium(self) -> None:
        analyzer = ContangoAnalyzer()
        calendar = CalendarResult(calendar_spread=0.04, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.strength is TermStructureStrength.MEDIUM

    def test_strength_high(self) -> None:
        analyzer = ContangoAnalyzer()
        calendar = CalendarResult(calendar_spread=0.07, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.strength is TermStructureStrength.HIGH

    def test_strength_extreme(self) -> None:
        analyzer = ContangoAnalyzer()
        calendar = CalendarResult(calendar_spread=0.15, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.strength is TermStructureStrength.EXTREME

    def test_missing_spread(self) -> None:
        analyzer = ContangoAnalyzer()
        calendar = CalendarResult()

        result = analyzer.analyze(calendar)

        assert result.is_contango is False
        assert "unavailable" in result.interpretation.lower()

    def test_non_calendar_input_raises(self) -> None:
        analyzer = ContangoAnalyzer()

        with pytest.raises(TypeError, match="calendar must be a CalendarResult"):
            analyzer.analyze("not-a-calendar")  # type: ignore[arg-type]

    def test_interpretation_present_when_contango(self) -> None:
        analyzer = ContangoAnalyzer()
        calendar = CalendarResult(calendar_spread=0.05, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.interpretation
        assert "contango" in result.interpretation.lower()


# ---------------------------------------------------------------------------
# BackwardationAnalyzer tests
# ---------------------------------------------------------------------------


class TestBackwardationAnalyzer:
    def test_backwardation_detected(self) -> None:
        analyzer = BackwardationAnalyzer()
        calendar = CalendarResult(calendar_spread=-0.05, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.is_backwardation is True
        assert result.confidence > 0.5

    def test_no_backwardation(self) -> None:
        analyzer = BackwardationAnalyzer()
        calendar = CalendarResult(calendar_spread=0.03, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.is_backwardation is False

    def test_strength_low(self) -> None:
        analyzer = BackwardationAnalyzer()
        calendar = CalendarResult(calendar_spread=-0.015, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.strength is TermStructureStrength.LOW

    def test_strength_extreme(self) -> None:
        analyzer = BackwardationAnalyzer()
        calendar = CalendarResult(calendar_spread=-0.15, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.strength is TermStructureStrength.EXTREME

    def test_stress_indicator(self) -> None:
        analyzer = BackwardationAnalyzer()
        calendar = CalendarResult(calendar_spread=-0.08, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.stress_indicator is True

    def test_no_stress_for_mild(self) -> None:
        analyzer = BackwardationAnalyzer()
        calendar = CalendarResult(calendar_spread=-0.02, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert result.stress_indicator is False

    def test_missing_spread(self) -> None:
        analyzer = BackwardationAnalyzer()
        calendar = CalendarResult()

        result = analyzer.analyze(calendar)

        assert result.is_backwardation is False
        assert "unavailable" in result.interpretation.lower()

    def test_stress_in_interpretation(self) -> None:
        analyzer = BackwardationAnalyzer()
        calendar = CalendarResult(calendar_spread=-0.08, confidence=0.8)

        result = analyzer.analyze(calendar)

        assert "STRESS" in result.interpretation

    def test_non_calendar_input_raises(self) -> None:
        analyzer = BackwardationAnalyzer()

        with pytest.raises(TypeError, match="calendar must be a CalendarResult"):
            analyzer.analyze("not-a-calendar")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TermStructureAnalyzer tests
# ---------------------------------------------------------------------------


class TestTermStructureAnalyzer:
    def test_missing_expiries(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = make_snapshot(expiries=())

        analysis = analyzer.analyze(snapshot)

        assert analysis.shape is TermStructureShape.UNKNOWN
        assert analysis.confidence == 0.0
        assert "no expiry" in analysis.warnings[0].lower()

    def test_contango_shape(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)

        assert analysis.shape is TermStructureShape.NORMAL
        assert analysis.front_iv == 0.20
        assert analysis.back_iv == 0.22
        assert analysis.curve_slope is not None

    def test_backwardation_shape(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = backwardation_snapshot()

        analysis = analyzer.analyze(snapshot)

        assert analysis.shape is TermStructureShape.BACKWARDATION
        assert analysis.overall_bias is MarketBias.BEARISH

    def test_flat_shape(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = flat_snapshot()

        analysis = analyzer.analyze(snapshot)

        assert analysis.shape is TermStructureShape.FLAT

    def test_single_expiry(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = make_snapshot(
            expiries=(make_expiry(30, atm_iv=0.20),),
        )

        analysis = analyzer.analyze(snapshot)

        assert analysis.shape is TermStructureShape.UNKNOWN

    def test_event_premium_in_analysis(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = event_premium_snapshot()

        analysis = analyzer.analyze(snapshot)

        assert analysis.event_premium is not None
        assert analysis.event_premium > 0.02

    def test_confidence_calculation(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)

        assert 0.0 <= analysis.confidence <= 1.0

    def test_non_snapshot_input_raises(self) -> None:
        analyzer = TermStructureAnalyzer()

        with pytest.raises(TypeError, match="snapshot must be a TermStructureSnapshot"):
            analyzer.analyze("not-a-snapshot")  # type: ignore[arg-type]

    def test_strong_contango_shape(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = make_snapshot(
            expiries=(
                make_expiry(30, atm_iv=0.15),
                make_expiry(60, atm_iv=0.18),
                make_expiry(90, atm_iv=0.21),
                make_expiry(180, atm_iv=0.24),
            ),
        )

        analysis = analyzer.analyze(snapshot)

        assert analysis.shape is TermStructureShape.CONTANGO
        assert analysis.strength is TermStructureStrength.HIGH

    def test_extreme_backwardation_shape(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = make_snapshot(
            expiries=(
                make_expiry(30, atm_iv=0.40),
                make_expiry(60, atm_iv=0.30),
                make_expiry(90, atm_iv=0.22),
                make_expiry(180, atm_iv=0.18),
            ),
        )

        analysis = analyzer.analyze(snapshot)

        assert analysis.shape is TermStructureShape.INVERTED
        assert analysis.strength in (
            TermStructureStrength.HIGH,
            TermStructureStrength.EXTREME,
        )


# ---------------------------------------------------------------------------
# Evidence generation
# ---------------------------------------------------------------------------


class TestEvidenceGeneration:
    def test_evidence_produced(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)

        assert analysis.evidence is not None
        assert isinstance(analysis.evidence, Evidence)

    def test_evidence_source(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.source == "Volatility Term Structure"

    def test_evidence_category(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.category is EvidenceCategory.OPTION_CHAIN

    def test_evidence_signal_backwardation(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = backwardation_snapshot()

        analysis = analyzer.analyze(snapshot)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.signal is EvidenceSignal.BEARISH

    def test_evidence_signal_contango(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.signal is EvidenceSignal.NEUTRAL

    def test_evidence_score_in_range(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = backwardation_snapshot()

        analysis = analyzer.analyze(snapshot)
        evidence = analysis.evidence

        assert evidence is not None
        assert 0.0 <= float(evidence.score) <= 100.0

    def test_evidence_confidence_in_range(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)
        evidence = analysis.evidence

        assert evidence is not None
        assert 0.0 <= float(evidence.confidence) <= 1.0

    def test_evidence_reasons_present(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)
        evidence = analysis.evidence

        assert evidence is not None
        assert len(evidence.reasons) > 0

    def test_evidence_metadata(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.metadata["analyzer"] == "TermStructureAnalyzer"
        assert evidence.metadata["shape"] == analysis.shape.value


# ---------------------------------------------------------------------------
# Explanation generation
# ---------------------------------------------------------------------------


class TestExplanationGeneration:
    def test_explanation_produced(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)

        assert analysis.explanation is not None
        assert isinstance(analysis.explanation, TermStructureExplanation)

    def test_explanation_sections(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)
        explanation = analysis.explanation

        assert explanation is not None
        assert explanation.curve_shape
        assert explanation.calendar_analysis
        assert explanation.slope_interpretation
        assert explanation.institutional_view
        assert explanation.risk_assessment
        assert explanation.future_considerations

    def test_explanation_contango_shape(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)
        explanation = analysis.explanation

        assert explanation is not None
        assert "upward" in explanation.curve_shape.lower()

    def test_explanation_backwardation(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = backwardation_snapshot()

        analysis = analyzer.analyze(snapshot)
        explanation = analysis.explanation

        assert explanation is not None
        assert "backwardation" in explanation.curve_shape.lower()

    def test_explanation_flat(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = flat_snapshot()

        analysis = analyzer.analyze(snapshot)
        explanation = analysis.explanation

        assert explanation is not None
        assert "flat" in explanation.curve_shape.lower()

    def test_explanation_institutional_view(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = backwardation_snapshot()

        analysis = analyzer.analyze(snapshot)
        explanation = analysis.explanation

        assert explanation is not None
        assert explanation.institutional_view

    def test_explanation_risk_assessment(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = backwardation_snapshot()

        analysis = analyzer.analyze(snapshot)
        explanation = analysis.explanation

        assert explanation is not None
        assert "risk" in explanation.risk_assessment.lower()

    def test_explanation_insufficient_data(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = make_snapshot(expiries=())

        analysis = analyzer.analyze(snapshot)
        explanation = analysis.explanation

        assert explanation is not None
        assert "unavailable" in explanation.curve_shape.lower()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_ts_chain_type_validated(self) -> None:
        analyzer = TermStructureAnalyzer()

        with pytest.raises(TypeError):
            analyzer.analyze(None)  # type: ignore[arg-type]

    def test_calendar_type_validated(self) -> None:
        analyzer = CalendarAnalyzer()

        with pytest.raises(TypeError):
            analyzer.analyze(None)  # type: ignore[arg-type]

    def test_contango_type_validated(self) -> None:
        analyzer = ContangoAnalyzer()

        with pytest.raises(TypeError):
            analyzer.analyze(None)  # type: ignore[arg-type]

    def test_backwardation_type_validated(self) -> None:
        analyzer = BackwardationAnalyzer()

        with pytest.raises(TypeError):
            analyzer.analyze(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# forbidden imports
# ---------------------------------------------------------------------------


def test_term_structure_has_no_forbidden_imports():
    analytics_dir = Path("titan/options/analytics")
    forbidden_terms = (
        "angel_one",
        "smartapi",
        "smartconnect",
        "broker",
        "black_scholes",
        "numpy",
        "scipy",
    )
    ts_files = (
        "term_structure.py",
        "calendar.py",
        "contango.py",
        "backwardation.py",
    )

    for filename in ts_files:
        path = analytics_dir / filename
        tree = ast.parse(path.read_text())

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names = {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported_names = {node.module or ""}
            else:
                continue

            assert all(
                term not in imported_name.lower()
                for imported_name in imported_names
                for term in forbidden_terms
            ), f"Forbidden import found in {path}: {imported_names}"


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_expiries(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = make_snapshot(expiries=())

        analysis = analyzer.analyze(snapshot)

        assert analysis.shape is TermStructureShape.UNKNOWN
        assert analysis.confidence == 0.0

    def test_all_ivs_none(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = make_snapshot(
            expiries=(
                make_expiry(30),
                make_expiry(60),
                make_expiry(90),
            ),
        )

        analysis = analyzer.analyze(snapshot)

        assert analysis.shape is TermStructureShape.UNKNOWN
        assert analysis.front_iv is None

    def test_mixed_iv_availability(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = make_snapshot(
            expiries=(
                make_expiry(30, atm_iv=0.20),
                make_expiry(60),
                make_expiry(90, atm_iv=0.28),
            ),
        )

        analysis = analyzer.analyze(snapshot)

        assert analysis.front_iv == 0.20
        assert analysis.back_iv == 0.28
        assert len(analysis.warnings) > 0

    def test_only_two_expiries(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = make_snapshot(
            expiries=(
                make_expiry(30, atm_iv=0.20),
                make_expiry(60, atm_iv=0.22),
            ),
        )

        analysis = analyzer.analyze(snapshot)

        assert analysis.front_iv == 0.20
        assert analysis.back_iv == 0.22
        assert analysis.shape is TermStructureShape.NORMAL
        assert analysis.strength is TermStructureStrength.LOW

    def test_analysis_is_frozen(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)

        with pytest.raises(AttributeError):
            analysis.confidence = 0.5  # type: ignore[misc]

    def test_serialization_metadata(self) -> None:
        analyzer = TermStructureAnalyzer()
        snapshot = contango_snapshot()

        analysis = analyzer.analyze(snapshot)

        assert analysis.metadata["analyzer"] == "TermStructureAnalyzer"
        assert analysis.metadata["underlying"] == "SPY"
        assert analysis.metadata["shape"] == analysis.shape.value
