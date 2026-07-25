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
    DealerBias,
    DealerBiasAnalyzer,
    DealerBiasLevel,
    DealerInventory,
    DealerInventoryAnalyzer,
    DealerPositioningAnalysis,
    DealerPositioningAnalyzer,
    DealerPositioningExplanation,
    DealerPositioningInput,
    DealerSide,
    GreeksAnalysis,
    MarketBias,
    OptionChainAnalysis,
    SurfaceComponentScore,
    SurfaceConsistencyLevel,
    SurfaceExplanation,
    SurfaceHealthLevel,
    SurfaceIntelligenceAnalysis,
)

NOW = datetime(2026, 7, 2, 9, 30)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_evidence(
    *,
    source: str = "test",
    category: EvidenceCategory = EvidenceCategory.OPTION_CHAIN,
    signal: EvidenceSignal = EvidenceSignal.NEUTRAL,
    score: float = 50.0,
    confidence: float = 0.5,
) -> Evidence:
    return Evidence(
        source=source,
        category=category,
        signal=signal,
        score=Score(score),
        confidence=Confidence(confidence),
        weight=1.0,
    )


def make_greeks_analysis(
    *,
    net_delta: float | None = 0.0,
    net_gamma: float | None = 0.0,
    average_delta: float | None = 0.0,
    average_gamma: float | None = 0.0,
    confidence: float = 0.8,
    bias: MarketBias = MarketBias.NEUTRAL,
    evidence_signal: EvidenceSignal = EvidenceSignal.NEUTRAL,
) -> GreeksAnalysis:
    analysis = GreeksAnalysis(
        net_delta=net_delta,
        net_gamma=net_gamma,
        net_theta=0.0,
        net_vega=0.0,
        average_delta=average_delta,
        average_gamma=average_gamma,
        average_theta=0.0,
        average_vega=0.0,
        overall_bias=bias,
        confidence=confidence,
    )
    evidence = make_evidence(
        source="Greeks",
        signal=evidence_signal,
        confidence=confidence,
    )
    object.__setattr__(analysis, "evidence", evidence)
    return analysis


def make_option_chain_analysis(
    *,
    bullish_score: float = 50.0,
    bearish_score: float = 50.0,
    neutral_score: float = 50.0,
    overall_bias: MarketBias = MarketBias.NEUTRAL,
    confidence: float = 0.8,
) -> OptionChainAnalysis:
    analysis = OptionChainAnalysis(
        overall_bias=overall_bias,
        confidence=confidence,
        support=None,
        resistance=None,
        pcr=1.0,
        highest_put_strike=None,
        highest_call_strike=None,
        bullish_score=bullish_score,
        bearish_score=bearish_score,
        neutral_score=neutral_score,
    )
    return analysis


def make_surface_analysis(
    *,
    health: SurfaceHealthLevel = SurfaceHealthLevel.HEALTHY,
    consistency: SurfaceConsistencyLevel = SurfaceConsistencyLevel.CONSISTENT,
    overall_bias: MarketBias = MarketBias.NEUTRAL,
    confidence: float = 0.8,
    component_scores: tuple | None = None,
) -> SurfaceIntelligenceAnalysis:
    if component_scores is None:
        component_scores = ()
    analysis = SurfaceIntelligenceAnalysis(
        health=health,
        consistency=consistency,
        overall_bias=overall_bias,
        institutional_confidence=confidence,
        component_scores=component_scores,
    )
    explanation = SurfaceExplanation(
        overall_surface="Surface is healthy.",
        health="All components available.",
        consistency="Signals consistent.",
        anomalies="No anomalies.",
        institutional_interpretation="Standard conditions.",
        risk_assessment="No elevated risk.",
    )
    object.__setattr__(analysis, "explanation", explanation)
    return analysis


def make_component_score(
    *,
    name: str = "Volatility",
    score: float = 50.0,
    confidence: float = 0.5,
    signal: EvidenceSignal = EvidenceSignal.NEUTRAL,
    available: bool = True,
) -> SurfaceComponentScore:
    return SurfaceComponentScore(
        name=name,
        score=score,
        confidence=confidence,
        signal=signal,
        available=available,
    )


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestDealerSide:
    def test_enum_values(self) -> None:
        assert DealerSide.LONG_GAMMA.value == "long_gamma"
        assert DealerSide.SHORT_GAMMA.value == "short_gamma"
        assert DealerSide.NEUTRAL.value == "neutral"
        assert DealerSide.UNKNOWN.value == "unknown"


class TestDealerBiasLevel:
    def test_enum_values(self) -> None:
        assert DealerBiasLevel.BULLISH.value == "bullish"
        assert DealerBiasLevel.BEARISH.value == "bearish"
        assert DealerBiasLevel.NEUTRAL.value == "neutral"
        assert DealerBiasLevel.UNKNOWN.value == "unknown"


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestDealerInventory:
    def test_creation(self) -> None:
        inv = DealerInventory(
            dealer_side=DealerSide.LONG_GAMMA,
            inventory_score=60.0,
            confidence=0.7,
            reasons=("Test reason",),
        )
        assert inv.dealer_side is DealerSide.LONG_GAMMA
        assert inv.inventory_score == 60.0
        assert inv.confidence == 0.7
        assert inv.reasons == ("Test reason",)
        assert inv.warnings == ()

    def test_frozen(self) -> None:
        inv = DealerInventory(
            dealer_side=DealerSide.NEUTRAL,
            inventory_score=0.0,
            confidence=0.0,
        )
        with pytest.raises(AttributeError):
            inv.dealer_side = DealerSide.LONG_GAMMA  # type: ignore[misc]

    def test_defaults(self) -> None:
        inv = DealerInventory(
            dealer_side=DealerSide.UNKNOWN,
            inventory_score=0.0,
            confidence=0.0,
        )
        assert inv.reasons == ()
        assert inv.warnings == ()


class TestDealerBias:
    def test_creation(self) -> None:
        bias = DealerBias(
            bias_level=DealerBiasLevel.BULLISH,
            bias_score=50.0,
            confidence=0.6,
            reasons=("Test reason",),
        )
        assert bias.bias_level is DealerBiasLevel.BULLISH
        assert bias.bias_score == 50.0

    def test_frozen(self) -> None:
        bias = DealerBias(
            bias_level=DealerBiasLevel.NEUTRAL,
            bias_score=0.0,
            confidence=0.0,
        )
        with pytest.raises(AttributeError):
            bias.bias_level = DealerBiasLevel.BULLISH  # type: ignore[misc]


class TestDealerPositioningInput:
    def test_creation(self) -> None:
        inp = DealerPositioningInput()
        assert inp.option_chain is None
        assert inp.greeks is None
        assert inp.liquidity is None
        assert inp.surface is None

    def test_frozen(self) -> None:
        inp = DealerPositioningInput()
        with pytest.raises(AttributeError):
            inp.option_chain = make_option_chain_analysis()  # type: ignore[misc]


class TestDealerPositioningExplanation:
    def test_creation(self) -> None:
        exp = DealerPositioningExplanation(
            dealer_inventory="Long gamma detected.",
            dealer_bias="Bullish bias.",
            hedging_pressure="Moderate pressure.",
            institutional_interpretation="Standard conditions.",
            risk_assessment="Low risk.",
        )
        assert "Long gamma" in exp.dealer_inventory
        assert "Bullish" in exp.dealer_bias

    def test_defaults(self) -> None:
        exp = DealerPositioningExplanation()
        assert exp.dealer_inventory == ""


class TestDealerPositioningAnalysis:
    def test_creation(self) -> None:
        analysis = DealerPositioningAnalysis(
            dealer_side=DealerSide.LONG_GAMMA,
            dealer_bias=DealerBiasLevel.BULLISH,
            hedging_pressure=0.6,
            confidence=0.7,
        )
        assert analysis.dealer_side is DealerSide.LONG_GAMMA
        assert analysis.dealer_bias is DealerBiasLevel.BULLISH
        assert analysis.hedging_pressure == 0.6
        assert analysis.confidence == 0.7
        assert analysis.evidence is None
        assert analysis.explanation is None

    def test_frozen(self) -> None:
        analysis = DealerPositioningAnalysis(
            dealer_side=DealerSide.UNKNOWN,
            dealer_bias=DealerBiasLevel.UNKNOWN,
            hedging_pressure=0.0,
            confidence=0.0,
        )
        with pytest.raises(AttributeError):
            analysis.dealer_side = DealerSide.LONG_GAMMA  # type: ignore[misc]

    def test_neutral_placeholder(self) -> None:
        placeholder = DealerPositioningAnalysis.neutral_placeholder()
        assert placeholder.dealer_side is DealerSide.UNKNOWN
        assert placeholder.dealer_bias is DealerBiasLevel.UNKNOWN
        assert placeholder.hedging_pressure == 0.0
        assert placeholder.confidence == 0.0
        assert "unavailable" in placeholder.warnings[0]

    def test_with_evidence(self) -> None:
        evidence = make_evidence()
        analysis = DealerPositioningAnalysis(
            dealer_side=DealerSide.SHORT_GAMMA,
            dealer_bias=DealerBiasLevel.BEARISH,
            hedging_pressure=0.8,
            confidence=0.75,
            evidence=evidence,
        )
        assert analysis.evidence is evidence


# ---------------------------------------------------------------------------
# DealerInventoryAnalyzer tests
# ---------------------------------------------------------------------------


class TestDealerInventoryAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = DealerInventoryAnalyzer()
        inp = DealerPositioningInput()
        result = analyzer.analyze(inp)
        assert result.dealer_side is DealerSide.UNKNOWN
        assert result.confidence == 0.0

    def test_short_gamma_from_greeks(self) -> None:
        analyzer = DealerInventoryAnalyzer()
        greeks = make_greeks_analysis(net_gamma=-0.01, confidence=0.8)
        inp = DealerPositioningInput(greeks=greeks)
        result = analyzer.analyze(inp)
        assert result.dealer_side is DealerSide.SHORT_GAMMA
        assert result.inventory_score < 0
        assert result.confidence > 0

    def test_long_gamma_from_greeks(self) -> None:
        analyzer = DealerInventoryAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.01, confidence=0.8)
        inp = DealerPositioningInput(greeks=greeks)
        result = analyzer.analyze(inp)
        assert result.dealer_side is DealerSide.LONG_GAMMA
        assert result.inventory_score > 0

    def test_neutral_greeks(self) -> None:
        analyzer = DealerInventoryAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.0, confidence=0.8)
        inp = DealerPositioningInput(greeks=greeks)
        result = analyzer.analyze(inp)
        assert result.dealer_side in (
            DealerSide.NEUTRAL,
            DealerSide.UNKNOWN,
        )

    def test_surface_bearish_contributes_short_gamma(self) -> None:
        analyzer = DealerInventoryAnalyzer()
        scores = (
            make_component_score(
                name="Smile",
                signal=EvidenceSignal.BULLISH,
                confidence=0.8,
            ),
            make_component_score(
                name="Skew",
                signal=EvidenceSignal.BULLISH,
                confidence=0.8,
            ),
        )
        surface = make_surface_analysis(component_scores=scores)
        inp = DealerPositioningInput(surface=surface)
        result = analyzer.analyze(inp)
        assert result.dealer_side is DealerSide.SHORT_GAMMA

    def test_surface_bullish_contributes_long_gamma(self) -> None:
        analyzer = DealerInventoryAnalyzer()
        scores = (
            make_component_score(
                name="Smile",
                signal=EvidenceSignal.BEARISH,
                confidence=0.8,
            ),
            make_component_score(
                name="Skew",
                signal=EvidenceSignal.BEARISH,
                confidence=0.8,
            ),
        )
        surface = make_surface_analysis(component_scores=scores)
        inp = DealerPositioningInput(surface=surface)
        result = analyzer.analyze(inp)
        assert result.dealer_side is DealerSide.LONG_GAMMA

    def test_option_chain_contributes(self) -> None:
        analyzer = DealerInventoryAnalyzer()
        chain = make_option_chain_analysis(bullish_score=80.0, bearish_score=20.0)
        inp = DealerPositioningInput(option_chain=chain)
        result = analyzer.analyze(inp)
        assert result.confidence > 0

    def test_all_sources_converge_short_gamma(self) -> None:
        analyzer = DealerInventoryAnalyzer()
        greeks = make_greeks_analysis(net_gamma=-0.02, confidence=0.8)
        scores = (
            make_component_score(
                name="Smile",
                signal=EvidenceSignal.BULLISH,
                confidence=0.8,
            ),
            make_component_score(
                name="Skew",
                signal=EvidenceSignal.BULLISH,
                confidence=0.8,
            ),
        )
        surface = make_surface_analysis(component_scores=scores)
        chain = make_option_chain_analysis(bullish_score=80.0, bearish_score=20.0)
        inp = DealerPositioningInput(greeks=greeks, surface=surface, option_chain=chain)
        result = analyzer.analyze(inp)
        assert result.dealer_side is DealerSide.SHORT_GAMMA
        assert result.confidence >= 0.4


# ---------------------------------------------------------------------------
# DealerBiasAnalyzer tests
# ---------------------------------------------------------------------------


class TestDealerBiasAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = DealerBiasAnalyzer()
        inp = DealerPositioningInput()
        result = analyzer.analyze(inp)
        assert result.bias_level is DealerBiasLevel.UNKNOWN
        assert result.confidence == 0.0

    def test_bullish_from_chain(self) -> None:
        analyzer = DealerBiasAnalyzer()
        chain = make_option_chain_analysis(bullish_score=80.0, bearish_score=10.0)
        inp = DealerPositioningInput(option_chain=chain)
        result = analyzer.analyze(inp)
        assert result.bias_level is DealerBiasLevel.BULLISH
        assert result.bias_score > 0

    def test_bearish_from_chain(self) -> None:
        analyzer = DealerBiasAnalyzer()
        chain = make_option_chain_analysis(bullish_score=10.0, bearish_score=80.0)
        inp = DealerPositioningInput(option_chain=chain)
        result = analyzer.analyze(inp)
        assert result.bias_level is DealerBiasLevel.BEARISH
        assert result.bias_score < 0

    def test_bullish_from_skew(self) -> None:
        analyzer = DealerBiasAnalyzer()
        scores = (
            make_component_score(
                name="Skew",
                signal=EvidenceSignal.BULLISH,
                confidence=0.8,
            ),
        )
        surface = make_surface_analysis(
            component_scores=scores,
            overall_bias=MarketBias.BULLISH,
        )
        inp = DealerPositioningInput(surface=surface)
        result = analyzer.analyze(inp)
        assert result.bias_level is DealerBiasLevel.BULLISH

    def test_bearish_from_skew(self) -> None:
        analyzer = DealerBiasAnalyzer()
        scores = (
            make_component_score(
                name="Skew",
                signal=EvidenceSignal.BEARISH,
                confidence=0.8,
            ),
        )
        surface = make_surface_analysis(
            component_scores=scores,
            overall_bias=MarketBias.BEARISH,
        )
        inp = DealerPositioningInput(surface=surface)
        result = analyzer.analyze(inp)
        assert result.bias_level is DealerBiasLevel.BEARISH

    def test_bullish_from_greeks(self) -> None:
        analyzer = DealerBiasAnalyzer()
        greeks = make_greeks_analysis(
            net_delta=0.5,
            average_delta=0.3,
            bias=MarketBias.BULLISH,
            confidence=0.8,
        )
        inp = DealerPositioningInput(greeks=greeks)
        result = analyzer.analyze(inp)
        assert result.bias_level is DealerBiasLevel.BULLISH

    def test_bearish_from_greeks(self) -> None:
        analyzer = DealerBiasAnalyzer()
        greeks = make_greeks_analysis(
            net_delta=-0.5,
            average_delta=-0.3,
            bias=MarketBias.BEARISH,
            confidence=0.8,
        )
        inp = DealerPositioningInput(greeks=greeks)
        result = analyzer.analyze(inp)
        assert result.bias_level is DealerBiasLevel.BEARISH

    def test_mixed_signals_result_in_neutral(self) -> None:
        analyzer = DealerBiasAnalyzer()
        chain = make_option_chain_analysis(bullish_score=50.0, bearish_score=50.0)
        greeks = make_greeks_analysis(net_delta=0.0, bias=MarketBias.NEUTRAL)
        inp = DealerPositioningInput(option_chain=chain, greeks=greeks)
        result = analyzer.analyze(inp)
        assert result.bias_level is DealerBiasLevel.NEUTRAL


# ---------------------------------------------------------------------------
# DealerPositioningAnalyzer tests
# ---------------------------------------------------------------------------


class TestDealerPositioningAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = DealerPositioningAnalyzer()
        result = analyzer.analyze()
        assert result.dealer_side is DealerSide.UNKNOWN
        assert result.dealer_bias is DealerBiasLevel.UNKNOWN
        assert result.hedging_pressure == 0.0
        assert result.confidence == 0.0
        assert result.explanation is not None

    def test_bullish_positioning(self) -> None:
        analyzer = DealerPositioningAnalyzer()
        greeks = make_greeks_analysis(
            net_gamma=0.02,
            net_delta=0.5,
            average_delta=0.3,
            bias=MarketBias.BULLISH,
            confidence=0.8,
            evidence_signal=EvidenceSignal.BULLISH,
        )
        chain = make_option_chain_analysis(bullish_score=80.0, bearish_score=10.0)
        result = analyzer.analyze(greeks=greeks, option_chain=chain)
        assert result.dealer_side is DealerSide.LONG_GAMMA
        assert result.dealer_bias is DealerBiasLevel.BULLISH
        assert result.confidence > 0
        assert result.evidence is not None
        assert result.explanation is not None

    def test_bearish_positioning(self) -> None:
        analyzer = DealerPositioningAnalyzer()
        greeks = make_greeks_analysis(
            net_gamma=-0.02,
            net_delta=-0.5,
            average_delta=-0.3,
            bias=MarketBias.BEARISH,
            confidence=0.8,
            evidence_signal=EvidenceSignal.BEARISH,
        )
        chain = make_option_chain_analysis(bullish_score=10.0, bearish_score=80.0)
        result = analyzer.analyze(greeks=greeks, option_chain=chain)
        assert result.dealer_side is DealerSide.SHORT_GAMMA
        assert result.dealer_bias is DealerBiasLevel.BEARISH

    def test_neutral_positioning(self) -> None:
        analyzer = DealerPositioningAnalyzer()
        greeks = make_greeks_analysis()
        chain = make_option_chain_analysis()
        result = analyzer.analyze(greeks=greeks, option_chain=chain)
        assert result.confidence >= 0

    def test_low_confidence_from_limited_data(self) -> None:
        analyzer = DealerPositioningAnalyzer()
        greeks = make_greeks_analysis(net_gamma=-0.01, confidence=0.8)
        result = analyzer.analyze(greeks=greeks)
        assert result.confidence > 0
        assert result.confidence < 0.5

    def test_evidence_generated(self) -> None:
        analyzer = DealerPositioningAnalyzer()
        greeks = make_greeks_analysis(
            net_gamma=0.02,
            net_delta=0.5,
            bias=MarketBias.BULLISH,
            confidence=0.8,
            evidence_signal=EvidenceSignal.BULLISH,
        )
        chain = make_option_chain_analysis(bullish_score=80.0, bearish_score=10.0)
        result = analyzer.analyze(greeks=greeks, option_chain=chain)
        evidence = result.evidence
        assert evidence is not None
        assert evidence.source == "Dealer Positioning"
        assert evidence.category is EvidenceCategory.OPTION_CHAIN
        assert evidence.signal in (
            EvidenceSignal.BULLISH,
            EvidenceSignal.NEUTRAL,
        )
        assert len(evidence.reasons) > 0

    def test_explanation_generated(self) -> None:
        analyzer = DealerPositioningAnalyzer()
        greeks = make_greeks_analysis(
            net_gamma=-0.02,
            net_delta=-0.5,
            bias=MarketBias.BEARISH,
            confidence=0.8,
            evidence_signal=EvidenceSignal.BEARISH,
        )
        result = analyzer.analyze(greeks=greeks)
        explanation = result.explanation
        assert explanation is not None
        assert isinstance(explanation, DealerPositioningExplanation)
        assert "Dealer Inventory" in explanation.dealer_inventory
        assert "Dealer Bias" in explanation.dealer_bias
        assert "Hedging" in explanation.hedging_pressure
        assert "Interpretation" in explanation.institutional_interpretation
        assert "Risk" in explanation.risk_assessment

    def test_serialization_round_trip(self) -> None:
        analyzer = DealerPositioningAnalyzer()
        greeks = make_greeks_analysis(
            net_gamma=0.01,
            net_delta=0.3,
            bias=MarketBias.BULLISH,
            confidence=0.7,
        )
        result = analyzer.analyze(greeks=greeks)
        data = {
            "dealer_side": result.dealer_side.value,
            "dealer_bias": result.dealer_bias.value,
            "hedging_pressure": result.hedging_pressure,
            "confidence": result.confidence,
        }
        assert data["dealer_side"] in (
            "long_gamma",
            "short_gamma",
            "neutral",
            "unknown",
        )
        assert data["dealer_bias"] in (
            "bullish",
            "bearish",
            "neutral",
            "unknown",
        )
        assert 0.0 <= data["hedging_pressure"] <= 1.0
        assert 0.0 <= data["confidence"] <= 1.0

    def test_partial_inputs_surface_only(self) -> None:
        analyzer = DealerPositioningAnalyzer()
        surface = make_surface_analysis()
        result = analyzer.analyze(surface=surface)
        assert result.confidence > 0
        assert result.explanation is not None

    def test_short_gamma_bearish_bias_combined(self) -> None:
        analyzer = DealerPositioningAnalyzer()
        greeks = make_greeks_analysis(
            net_gamma=-0.02,
            net_delta=-0.5,
            average_delta=-0.3,
            bias=MarketBias.BEARISH,
            confidence=0.8,
        )
        chain = make_option_chain_analysis(bullish_score=10.0, bearish_score=80.0)
        scores = (
            make_component_score(
                name="Smile",
                signal=EvidenceSignal.BULLISH,
                confidence=0.8,
            ),
            make_component_score(
                name="Skew",
                signal=EvidenceSignal.BULLISH,
                confidence=0.8,
            ),
        )
        surface = make_surface_analysis(component_scores=scores)
        result = analyzer.analyze(greeks=greeks, option_chain=chain, surface=surface)
        assert result.dealer_side is DealerSide.SHORT_GAMMA
        assert result.dealer_bias is DealerBiasLevel.BEARISH
        assert result.hedging_pressure > 0.3
