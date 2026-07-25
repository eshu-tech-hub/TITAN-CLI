from datetime import datetime

import pytest

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.options.analytics import (
    MarketBias,
    SkewAnalysis,
    SkewDirection,
    SkewStrength,
    SmileAnalysis,
    SmileQuality,
    SmileRegime,
    SmileShape,
    SmileSymmetry,
    SurfaceAnomaly,
    SurfaceAnomalyAnalyzer,
    SurfaceAnomalyType,
    SurfaceComponentScore,
    SurfaceConsistencyAnalyzer,
    SurfaceConsistencyLevel,
    SurfaceExplanation,
    SurfaceHealthAnalyzer,
    SurfaceHealthLevel,
    SurfaceIntelligenceAnalysis,
    SurfaceIntelligenceAnalyzer,
    TermStructureAnalysis,
    TermStructureShape,
    TermStructureStrength,
    VolatilityAnalysis,
    VolatilityRegime,
    VolatilitySurfaceInput,
)

NOW = datetime(2026, 7, 2, 9, 30)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_vol_analysis(
    *,
    confidence: float = 0.8,
    bias: MarketBias = MarketBias.NEUTRAL,
    evidence_signal: EvidenceSignal = EvidenceSignal.NEUTRAL,
) -> VolatilityAnalysis:
    analysis = VolatilityAnalysis(
        current_iv=0.20,
        current_hv=0.18,
        iv_rank=50.0,
        iv_percentile=50.0,
        iv_vs_hv="normal",
        volatility_regime=VolatilityRegime.STABLE,
        iv_level="normal",
        iv_rank_level="neutral",
        iv_trend="flat",
        hv_trend="flat",
        hv_stability="stable",
        buying_bias=False,
        selling_bias=False,
        overall_bias=bias,
        confidence=confidence,
    )
    evidence = Evidence(
        source="Volatility",
        category=EvidenceCategory.OPTION_CHAIN,
        signal=evidence_signal,
        score=Score(50.0),
        confidence=Confidence(confidence),
        weight=1.0,
    )
    object.__setattr__(analysis, "evidence", evidence)
    return analysis


def make_smile_analysis(
    *,
    confidence: float = 0.8,
    shape: SmileShape = SmileShape.NORMAL,
    symmetry: SmileSymmetry = SmileSymmetry.SYMMETRIC,
    regime: SmileRegime = SmileRegime.NORMAL_CONVEXITY,
    evidence_signal: EvidenceSignal = EvidenceSignal.NEUTRAL,
) -> SmileAnalysis:
    analysis = SmileAnalysis(
        atm_strike=450.0,
        atm_iv=0.20,
        smile_shape=shape,
        smile_symmetry=symmetry,
        smile_regime=regime,
        smile_quality=SmileQuality.RELIABLE,
        curvature=0.15,
        left_wing_iv=0.22,
        right_wing_iv=0.22,
        strike_count=20,
        iv_completeness=0.95,
        confidence=confidence,
    )
    evidence = Evidence(
        source="Volatility Smile",
        category=EvidenceCategory.OPTION_CHAIN,
        signal=evidence_signal,
        score=Score(50.0),
        confidence=Confidence(confidence),
        weight=1.0,
    )
    if evidence_signal:
        object.__setattr__(analysis, "evidence", evidence)
    return analysis


def make_skew_analysis(
    *,
    confidence: float = 0.8,
    direction: SkewDirection = SkewDirection.SYMMETRIC,
    strength: SkewStrength = SkewStrength.LOW,
    bias: MarketBias = MarketBias.NEUTRAL,
    evidence_signal: EvidenceSignal = EvidenceSignal.NEUTRAL,
) -> SkewAnalysis:
    analysis = SkewAnalysis(
        direction=direction,
        strength=strength,
        risk_reversal=None,
        butterfly=None,
        overall_bias=bias,
        confidence=confidence,
    )
    evidence = Evidence(
        source="Volatility Skew",
        category=EvidenceCategory.OPTION_CHAIN,
        signal=evidence_signal,
        score=Score(50.0),
        confidence=Confidence(confidence),
        weight=1.0,
    )
    if evidence_signal:
        object.__setattr__(analysis, "evidence", evidence)
    return analysis


def make_term_analysis(
    *,
    confidence: float = 0.8,
    shape: TermStructureShape = TermStructureShape.NORMAL,
    strength: TermStructureStrength = TermStructureStrength.LOW,
    bias: MarketBias = MarketBias.NEUTRAL,
    evidence_signal: EvidenceSignal = EvidenceSignal.NEUTRAL,
) -> TermStructureAnalysis:
    analysis = TermStructureAnalysis(
        shape=shape,
        strength=strength,
        front_iv=0.20,
        back_iv=0.22,
        curve_slope=0.02,
        event_premium=None,
        calendar_bias=bias,
        overall_bias=bias,
        confidence=confidence,
    )
    evidence = Evidence(
        source="Volatility Term Structure",
        category=EvidenceCategory.OPTION_CHAIN,
        signal=evidence_signal,
        score=Score(50.0),
        confidence=Confidence(confidence),
        weight=1.0,
    )
    if evidence_signal:
        object.__setattr__(analysis, "evidence", evidence)
    return analysis


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestSurfaceHealthLevel:
    def test_enum_values(self) -> None:
        assert SurfaceHealthLevel.HEALTHY.value == "healthy"
        assert SurfaceHealthLevel.GOOD.value == "good"
        assert SurfaceHealthLevel.CAUTION.value == "caution"
        assert SurfaceHealthLevel.UNHEALTHY.value == "unhealthy"
        assert SurfaceHealthLevel.UNKNOWN.value == "unknown"


class TestSurfaceConsistencyLevel:
    def test_enum_values(self) -> None:
        assert SurfaceConsistencyLevel.CONSISTENT.value == "consistent"
        assert (
            SurfaceConsistencyLevel.PARTIALLY_CONSISTENT.value == "partially_consistent"
        )
        assert SurfaceConsistencyLevel.INCONSISTENT.value == "inconsistent"
        assert SurfaceConsistencyLevel.UNKNOWN.value == "unknown"


class TestSurfaceAnomalyType:
    def test_enum_values(self) -> None:
        assert SurfaceAnomalyType.EXTREME_SMILE.value == "extreme_smile"
        assert SurfaceAnomalyType.CONFLICTING_SIGNALS.value == "conflicting_signals"


class TestSurfaceIntelligenceAnalysis:
    def test_neutral_placeholder(self) -> None:
        analysis = SurfaceIntelligenceAnalysis.neutral_placeholder()

        assert analysis.health is SurfaceHealthLevel.UNKNOWN
        assert analysis.consistency is SurfaceConsistencyLevel.UNKNOWN
        assert analysis.overall_bias is MarketBias.UNKNOWN
        assert analysis.institutional_confidence == 0.0
        assert "Volatility surface data unavailable" in analysis.warnings[0]

    def test_frozen(self) -> None:
        analysis = SurfaceIntelligenceAnalysis.neutral_placeholder()

        with pytest.raises(AttributeError):
            analysis.health = SurfaceHealthLevel.HEALTHY  # type: ignore[misc]


class TestSurfaceAnomaly:
    def test_defaults(self) -> None:
        anomaly = SurfaceAnomaly(
            type=SurfaceAnomalyType.EXTREME_SMILE,
            source="Smile",
            description="Extreme smile detected.",
        )

        assert anomaly.type is SurfaceAnomalyType.EXTREME_SMILE
        assert anomaly.source == "Smile"

    def test_frozen(self) -> None:
        anomaly = SurfaceAnomaly(
            type=SurfaceAnomalyType.EXTREME_SMILE,
            source="Smile",
            description="Extreme smile detected.",
        )

        with pytest.raises(AttributeError):
            anomaly.type = SurfaceAnomalyType.LOW_CONFIDENCE  # type: ignore[misc]


class TestSurfaceComponentScore:
    def test_defaults(self) -> None:
        score = SurfaceComponentScore(
            name="Volatility",
            score=75.0,
            confidence=0.8,
            signal=EvidenceSignal.BULLISH,
            available=True,
        )

        assert score.name == "Volatility"
        assert score.score == 75.0
        assert score.signal is EvidenceSignal.BULLISH


class TestVolatilitySurfaceInput:
    def test_all_fields_default_to_none(self) -> None:
        inp = VolatilitySurfaceInput()

        assert inp.volatility is None
        assert inp.smile is None
        assert inp.skew is None
        assert inp.term_structure is None


class TestSurfaceExplanation:
    def test_defaults(self) -> None:
        exp = SurfaceExplanation()

        assert exp.overall_surface == ""
        assert exp.health == ""


# ---------------------------------------------------------------------------
# SurfaceHealthAnalyzer tests
# ---------------------------------------------------------------------------


class TestSurfaceHealthAnalyzer:
    def test_healthy_all_components(self) -> None:
        analyzer = SurfaceHealthAnalyzer()
        inp = VolatilitySurfaceInput(
            volatility=make_vol_analysis(confidence=0.8),
            smile=make_smile_analysis(confidence=0.8),
            skew=make_skew_analysis(confidence=0.8),
            term_structure=make_term_analysis(confidence=0.8),
        )

        result = analyzer.analyze(inp)

        assert result.level is SurfaceHealthLevel.HEALTHY
        assert result.reason

    def test_good_three_components(self) -> None:
        analyzer = SurfaceHealthAnalyzer()
        inp = VolatilitySurfaceInput(
            volatility=make_vol_analysis(confidence=0.7),
            smile=make_smile_analysis(confidence=0.7),
            skew=make_skew_analysis(confidence=0.7),
            term_structure=None,
        )

        result = analyzer.analyze(inp)

        assert result.level is SurfaceHealthLevel.GOOD

    def test_caution_two_components(self) -> None:
        analyzer = SurfaceHealthAnalyzer()
        inp = VolatilitySurfaceInput(
            volatility=make_vol_analysis(confidence=0.6),
            smile=make_smile_analysis(confidence=0.6),
            skew=None,
            term_structure=None,
        )

        result = analyzer.analyze(inp)

        assert result.level is SurfaceHealthLevel.CAUTION

    def test_unhealthy_one_component(self) -> None:
        analyzer = SurfaceHealthAnalyzer()
        inp = VolatilitySurfaceInput(
            volatility=make_vol_analysis(confidence=0.5),
            smile=None,
            skew=None,
            term_structure=None,
        )

        result = analyzer.analyze(inp)

        assert result.level is SurfaceHealthLevel.UNHEALTHY

    def test_unknown_no_components(self) -> None:
        analyzer = SurfaceHealthAnalyzer()
        inp = VolatilitySurfaceInput()

        result = analyzer.analyze(inp)

        assert result.level is SurfaceHealthLevel.UNKNOWN
        assert "No volatility intelligence components" in result.reason

    def test_component_status_missing(self) -> None:
        analyzer = SurfaceHealthAnalyzer()
        inp = VolatilitySurfaceInput(
            volatility=make_vol_analysis(confidence=0.8),
            smile=None,
            skew=None,
            term_structure=None,
        )

        result = analyzer.analyze(inp)

        assert result.component_status["Volatility"] == "healthy"
        assert result.component_status["Smile"] == "missing"

    def test_non_input_raises(self) -> None:
        analyzer = SurfaceHealthAnalyzer()

        with pytest.raises(TypeError, match="surface must be a VolatilitySurfaceInput"):
            analyzer.analyze("not-an-input")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SurfaceConsistencyAnalyzer tests
# ---------------------------------------------------------------------------


class TestSurfaceConsistencyAnalyzer:
    def test_all_neutral_consistent(self) -> None:
        analyzer = SurfaceConsistencyAnalyzer()
        inp = VolatilitySurfaceInput(
            volatility=make_vol_analysis(
                evidence_signal=EvidenceSignal.NEUTRAL,
            ),
            smile=make_smile_analysis(
                evidence_signal=EvidenceSignal.NEUTRAL,
            ),
            skew=make_skew_analysis(
                evidence_signal=EvidenceSignal.NEUTRAL,
            ),
            term_structure=make_term_analysis(
                evidence_signal=EvidenceSignal.NEUTRAL,
            ),
        )

        result = analyzer.analyze(inp)

        assert result.level is SurfaceConsistencyLevel.CONSISTENT

    def test_all_bullish_consistent(self) -> None:
        analyzer = SurfaceConsistencyAnalyzer()
        inp = VolatilitySurfaceInput(
            volatility=make_vol_analysis(
                evidence_signal=EvidenceSignal.BULLISH,
            ),
            smile=make_smile_analysis(
                evidence_signal=EvidenceSignal.BULLISH,
            ),
            skew=make_skew_analysis(
                evidence_signal=EvidenceSignal.BULLISH,
            ),
            term_structure=make_term_analysis(
                evidence_signal=EvidenceSignal.BULLISH,
            ),
        )

        result = analyzer.analyze(inp)

        assert result.level is SurfaceConsistencyLevel.CONSISTENT

    def test_conflicting_bullish_bearish_inconsistent(self) -> None:
        analyzer = SurfaceConsistencyAnalyzer()
        inp = VolatilitySurfaceInput(
            volatility=make_vol_analysis(
                evidence_signal=EvidenceSignal.BULLISH,
            ),
            smile=make_smile_analysis(
                evidence_signal=EvidenceSignal.BEARISH,
            ),
            skew=make_skew_analysis(
                evidence_signal=EvidenceSignal.NEUTRAL,
            ),
            term_structure=make_term_analysis(
                evidence_signal=EvidenceSignal.NEUTRAL,
            ),
        )

        result = analyzer.analyze(inp)

        assert result.level is SurfaceConsistencyLevel.INCONSISTENT
        assert len(result.conflicts) > 0

    def test_no_signals_unknown(self) -> None:
        analyzer = SurfaceConsistencyAnalyzer()
        result = analyzer.analyze(VolatilitySurfaceInput())

        assert result.level is SurfaceConsistencyLevel.UNKNOWN

    def test_non_input_raises(self) -> None:
        analyzer = SurfaceConsistencyAnalyzer()

        with pytest.raises(TypeError, match="surface must be a VolatilitySurfaceInput"):
            analyzer.analyze("not-an-input")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SurfaceAnomalyAnalyzer tests
# ---------------------------------------------------------------------------


class TestSurfaceAnomalyAnalyzer:
    def test_no_anomalies(self) -> None:
        analyzer = SurfaceAnomalyAnalyzer()
        inp = VolatilitySurfaceInput(
            volatility=make_vol_analysis(confidence=0.8),
            smile=make_smile_analysis(
                confidence=0.8,
                shape=SmileShape.NORMAL,
            ),
            skew=make_skew_analysis(
                confidence=0.8,
                strength=SkewStrength.LOW,
            ),
            term_structure=make_term_analysis(
                confidence=0.8,
                shape=TermStructureShape.NORMAL,
                strength=TermStructureStrength.LOW,
            ),
        )

        result = analyzer.analyze(inp)
        assert result.anomaly_count == 0

    def test_extreme_smile_detected(self) -> None:
        analyzer = SurfaceAnomalyAnalyzer()
        inp = VolatilitySurfaceInput(
            smile=make_smile_analysis(
                shape=SmileShape.EXTREME,
            ),
        )

        result = analyzer.analyze(inp)
        types = [a.type for a in result.anomalies]

        assert SurfaceAnomalyType.EXTREME_SMILE in types

    def test_extreme_skew_detected(self) -> None:
        analyzer = SurfaceAnomalyAnalyzer()
        inp = VolatilitySurfaceInput(
            skew=make_skew_analysis(
                strength=SkewStrength.EXTREME,
            ),
        )

        result = analyzer.analyze(inp)
        types = [a.type for a in result.anomalies]

        assert SurfaceAnomalyType.EXTREME_SKEW in types

    def test_broken_term_structure_detected(self) -> None:
        analyzer = SurfaceAnomalyAnalyzer()
        inp = VolatilitySurfaceInput(
            term_structure=make_term_analysis(
                shape=TermStructureShape.INVERTED,
                strength=TermStructureStrength.HIGH,
            ),
        )

        result = analyzer.analyze(inp)
        types = [a.type for a in result.anomalies]

        assert SurfaceAnomalyType.BROKEN_TERM_STRUCTURE in types

    def test_conflicting_signals_detected(self) -> None:
        analyzer = SurfaceAnomalyAnalyzer()
        inp = VolatilitySurfaceInput(
            volatility=make_vol_analysis(
                bias=MarketBias.BULLISH,
            ),
            smile=make_smile_analysis(
                regime=SmileRegime.NORMAL_CONVEXITY,
            ),
            skew=make_skew_analysis(
                direction=SkewDirection.LEFT,
                strength=SkewStrength.HIGH,
                bias=MarketBias.BEARISH,
            ),
            term_structure=make_term_analysis(
                shape=TermStructureShape.NORMAL,
                bias=MarketBias.NEUTRAL,
            ),
        )

        result = analyzer.analyze(inp)
        types = [a.type for a in result.anomalies]

        assert SurfaceAnomalyType.CONFLICTING_SIGNALS in types

    def test_missing_intelligence_detected(self) -> None:
        analyzer = SurfaceAnomalyAnalyzer()
        inp = VolatilitySurfaceInput(
            volatility=make_vol_analysis(),
            smile=None,
            skew=None,
            term_structure=None,
        )

        result = analyzer.analyze(inp)

        assert result.anomaly_count >= 3
        missing_sources = [
            a.source
            for a in result.anomalies
            if a.type is SurfaceAnomalyType.MISSING_INTELLIGENCE
        ]
        assert "Smile" in missing_sources
        assert "Skew" in missing_sources
        assert "Term Structure" in missing_sources

    def test_low_confidence_detected(self) -> None:
        analyzer = SurfaceAnomalyAnalyzer()
        inp = VolatilitySurfaceInput(
            volatility=make_vol_analysis(confidence=0.2),
            smile=make_smile_analysis(confidence=0.2),
            skew=make_skew_analysis(confidence=0.2),
            term_structure=make_term_analysis(confidence=0.2),
        )

        result = analyzer.analyze(inp)
        low_conf = [
            a for a in result.anomalies if a.type is SurfaceAnomalyType.LOW_CONFIDENCE
        ]

        assert len(low_conf) == 4

    def test_multiple_anomalies(self) -> None:
        analyzer = SurfaceAnomalyAnalyzer()
        inp = VolatilitySurfaceInput(
            smile=make_smile_analysis(shape=SmileShape.EXTREME),
            skew=make_skew_analysis(strength=SkewStrength.EXTREME),
            term_structure=make_term_analysis(
                shape=TermStructureShape.INVERTED,
                strength=TermStructureStrength.EXTREME,
            ),
        )

        result = analyzer.analyze(inp)

        assert result.anomaly_count >= 3

    def test_non_input_raises(self) -> None:
        analyzer = SurfaceAnomalyAnalyzer()

        with pytest.raises(TypeError, match="surface must be a VolatilitySurfaceInput"):
            analyzer.analyze("not-an-input")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SurfaceIntelligenceAnalyzer (orchestrator) tests
# ---------------------------------------------------------------------------


class TestSurfaceIntelligenceAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze()

        assert analysis.health is SurfaceHealthLevel.UNKNOWN
        assert analysis.consistency is SurfaceConsistencyLevel.UNKNOWN
        assert analysis.overall_bias is MarketBias.UNKNOWN
        assert analysis.institutional_confidence == 0.0

    def test_healthy_surface(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
            smile=make_smile_analysis(confidence=0.8),
            skew=make_skew_analysis(confidence=0.8),
            term_structure=make_term_analysis(confidence=0.8),
        )

        assert analysis.health is SurfaceHealthLevel.HEALTHY
        assert analysis.institutional_confidence > 0

    def test_conflicting_surface(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(
                evidence_signal=EvidenceSignal.BULLISH,
            ),
            smile=make_smile_analysis(
                evidence_signal=EvidenceSignal.NEUTRAL,
            ),
            skew=make_skew_analysis(
                evidence_signal=EvidenceSignal.BEARISH,
            ),
            term_structure=make_term_analysis(
                evidence_signal=EvidenceSignal.BEARISH,
            ),
        )

        assert analysis.consistency is SurfaceConsistencyLevel.INCONSISTENT

    def test_missing_component(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
            smile=None,
            skew=make_skew_analysis(confidence=0.8),
            term_structure=None,
        )

        assert analysis.health is SurfaceHealthLevel.CAUTION
        assert analysis.component_scores is not None
        scores = {s.name: s.available for s in analysis.component_scores}
        assert scores["Volatility"] is True
        assert scores["Smile"] is False

    def test_missing_smile(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
            smile=None,
            skew=make_skew_analysis(confidence=0.8),
            term_structure=make_term_analysis(confidence=0.8),
        )

        assert analysis.health is SurfaceHealthLevel.GOOD

    def test_missing_skew(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
            smile=make_smile_analysis(confidence=0.8),
            skew=None,
            term_structure=make_term_analysis(confidence=0.8),
        )

        assert analysis.health is SurfaceHealthLevel.GOOD

    def test_missing_term(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
            smile=make_smile_analysis(confidence=0.8),
            skew=make_skew_analysis(confidence=0.8),
            term_structure=None,
        )

        assert analysis.health is SurfaceHealthLevel.GOOD

    def test_mixed_confidence(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.9),
            smile=make_smile_analysis(confidence=0.2),
            skew=make_skew_analysis(confidence=0.8),
            term_structure=make_term_analysis(confidence=0.8),
        )

        assert analysis.health is SurfaceHealthLevel.GOOD
        anomalies = [
            a for a in analysis.anomalies if a.type is SurfaceAnomalyType.LOW_CONFIDENCE
        ]
        assert len(anomalies) == 1
        assert anomalies[0].source == "Smile"

    def test_anomalies_present(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            smile=make_smile_analysis(shape=SmileShape.EXTREME),
            skew=make_skew_analysis(strength=SkewStrength.EXTREME),
            term_structure=make_term_analysis(
                shape=TermStructureShape.INVERTED,
                strength=TermStructureStrength.EXTREME,
            ),
        )

        assert len(analysis.anomalies) >= 2

    def test_component_scores(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        vol = make_vol_analysis(confidence=0.8)
        analysis = analyzer.analyze(volatility=vol)

        scores = analysis.component_scores
        assert len(scores) == 4
        vol_score = next(s for s in scores if s.name == "Volatility")
        assert vol_score.available is True
        assert vol_score.confidence == 0.8
        assert vol_score.signal is not None

    def test_evidence_produced(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
            smile=make_smile_analysis(confidence=0.8),
            skew=make_skew_analysis(confidence=0.8),
            term_structure=make_term_analysis(confidence=0.8),
        )

        assert analysis.evidence is not None
        assert analysis.evidence.source == "Volatility Surface"
        assert analysis.evidence.category is EvidenceCategory.OPTION_CHAIN

    def test_evidence_signal_bearish(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(
                bias=MarketBias.BEARISH,
                evidence_signal=EvidenceSignal.BEARISH,
            ),
            smile=make_smile_analysis(
                evidence_signal=EvidenceSignal.BEARISH,
            ),
            skew=make_skew_analysis(
                bias=MarketBias.BEARISH,
                evidence_signal=EvidenceSignal.BEARISH,
            ),
            term_structure=make_term_analysis(
                bias=MarketBias.BEARISH,
                evidence_signal=EvidenceSignal.BEARISH,
            ),
        )

        assert analysis.evidence is not None
        assert analysis.evidence.signal is EvidenceSignal.BEARISH

    def test_evidence_signal_neutral(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(
                evidence_signal=EvidenceSignal.NEUTRAL,
            ),
            smile=make_smile_analysis(
                evidence_signal=EvidenceSignal.NEUTRAL,
            ),
            skew=make_skew_analysis(
                evidence_signal=EvidenceSignal.NEUTRAL,
            ),
            term_structure=make_term_analysis(
                evidence_signal=EvidenceSignal.NEUTRAL,
            ),
        )

        assert analysis.evidence is not None
        assert analysis.evidence.signal is EvidenceSignal.NEUTRAL

    def test_evidence_score_in_range(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.9),
            smile=make_smile_analysis(confidence=0.9),
            skew=make_skew_analysis(confidence=0.9),
            term_structure=make_term_analysis(confidence=0.9),
        )

        assert analysis.evidence is not None
        assert 0.0 <= float(analysis.evidence.score) <= 100.0

    def test_evidence_confidence_in_range(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
            smile=make_smile_analysis(confidence=0.8),
        )

        assert analysis.evidence is not None
        assert 0.0 <= float(analysis.evidence.confidence) <= 1.0

    def test_evidence_reasons_present(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
            smile=make_smile_analysis(confidence=0.8),
            skew=make_skew_analysis(confidence=0.8),
            term_structure=make_term_analysis(confidence=0.8),
        )

        assert analysis.evidence is not None
        assert len(analysis.evidence.reasons) > 0

    def test_explanation_produced(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
            smile=make_smile_analysis(confidence=0.8),
            skew=make_skew_analysis(confidence=0.8),
            term_structure=make_term_analysis(confidence=0.8),
        )

        assert analysis.explanation is not None
        assert isinstance(analysis.explanation, SurfaceExplanation)

    def test_explanation_sections(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
            smile=make_smile_analysis(confidence=0.8),
            skew=make_skew_analysis(confidence=0.8),
            term_structure=make_term_analysis(confidence=0.8),
        )

        explanation = analysis.explanation
        assert explanation is not None
        assert explanation.overall_surface
        assert explanation.health
        assert explanation.consistency
        assert explanation.institutional_interpretation
        assert explanation.risk_assessment

    def test_explanation_anomalies(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            smile=make_smile_analysis(shape=SmileShape.EXTREME),
        )

        explanation = analysis.explanation
        assert explanation is not None
        assert "anomalies" in explanation.anomalies.lower()

    def test_bias_calculation_bullish(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(
                evidence_signal=EvidenceSignal.BULLISH,
            ),
            smile=make_smile_analysis(
                evidence_signal=EvidenceSignal.BULLISH,
            ),
            skew=make_skew_analysis(
                evidence_signal=EvidenceSignal.BULLISH,
            ),
            term_structure=make_term_analysis(
                evidence_signal=EvidenceSignal.BULLISH,
            ),
        )

        assert analysis.overall_bias is MarketBias.BULLISH

    def test_bias_calculation_bearish(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(
                evidence_signal=EvidenceSignal.BEARISH,
            ),
            skew=make_skew_analysis(
                evidence_signal=EvidenceSignal.BEARISH,
            ),
            term_structure=make_term_analysis(
                evidence_signal=EvidenceSignal.BEARISH,
            ),
        )

        assert analysis.overall_bias is MarketBias.BEARISH

    def test_serialization_metadata(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
            smile=make_smile_analysis(confidence=0.8),
        )

        assert analysis.metadata["analyzer"] == "SurfaceIntelligenceAnalyzer"
        assert analysis.metadata["volatility_available"] is True
        assert analysis.metadata["smile_available"] is True
        assert analysis.metadata["skew_available"] is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestSurfaceIntelligenceEdgeCases:
    def test_empty_all_none(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze()

        assert analysis.health is SurfaceHealthLevel.UNKNOWN
        assert analysis.institutional_confidence == 0.0
        assert "No volatility intelligence data" in analysis.warnings[0]

    def test_no_evidence_on_missing_component(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
        )

        scores = analysis.component_scores
        missing = [s for s in scores if not s.available]
        for m in missing:
            assert m.score == 50.0
            assert m.confidence == 0.0
            assert m.signal is None

    def test_analysis_is_frozen(self) -> None:
        analyzer = SurfaceIntelligenceAnalyzer()
        analysis = analyzer.analyze(
            volatility=make_vol_analysis(confidence=0.8),
        )

        with pytest.raises(AttributeError):
            analysis.health = SurfaceHealthLevel.HEALTHY  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


class TestSurfaceValidation:
    def test_health_type_validated(self) -> None:
        analyzer = SurfaceHealthAnalyzer()

        with pytest.raises(TypeError):
            analyzer.analyze(None)  # type: ignore[arg-type]

    def test_consistency_type_validated(self) -> None:
        analyzer = SurfaceConsistencyAnalyzer()

        with pytest.raises(TypeError):
            analyzer.analyze(None)  # type: ignore[arg-type]

    def test_anomaly_type_validated(self) -> None:
        analyzer = SurfaceAnomalyAnalyzer()

        with pytest.raises(TypeError):
            analyzer.analyze(None)  # type: ignore[arg-type]
