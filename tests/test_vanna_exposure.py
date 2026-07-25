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
    DealerBiasLevel,
    DealerPositioningAnalysis,
    DealerSide,
    GammaExposureAnalysis,
    GammaRegime,
    GreeksAnalysis,
    MarketBias,
    OptionChainAnalysis,
    OptionChainSnapshot,
    OptionStrikeSnapshot,
    PinningProbability,
    SurfaceConsistencyLevel,
    SurfaceExplanation,
    SurfaceHealthLevel,
    SurfaceIntelligenceAnalysis,
    VannaExposureAnalysis,
    VannaExposureAnalyzer,
    VannaExposureInput,
    VannaExplanation,
    VannaPressure,
    VannaPressureAnalyzer,
    VannaPressureLevel,
    VannaRegime,
    VannaRegimeAnalyzer,
    VannaRegimeType,
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
    net_gamma: float | None = 0.0,
    confidence: float = 0.8,
) -> GreeksAnalysis:
    return GreeksAnalysis(
        net_delta=0.0,
        net_gamma=net_gamma,
        net_theta=0.0,
        net_vega=0.0,
        average_delta=0.0,
        average_gamma=0.0,
        average_theta=0.0,
        average_vega=0.0,
        overall_bias=MarketBias.NEUTRAL,
        confidence=confidence,
    )


def make_dealer_positioning(
    *,
    dealer_side: DealerSide = DealerSide.NEUTRAL,
    confidence: float = 0.7,
) -> DealerPositioningAnalysis:
    return DealerPositioningAnalysis(
        dealer_side=dealer_side,
        dealer_bias=DealerBiasLevel.NEUTRAL,
        hedging_pressure=0.0,
        confidence=confidence,
    )


def make_gamma_exposure(
    *,
    regime: GammaRegime = GammaRegime.NEUTRAL,
    confidence: float = 0.7,
) -> GammaExposureAnalysis:
    return GammaExposureAnalysis(
        net_gamma_exposure=0.0,
        gamma_regime=regime,
        zero_gamma_level=None,
        call_wall=None,
        put_wall=None,
        pinning_probability=PinningProbability.UNKNOWN,
        volatility_expansion_probability=0.0,
        confidence=confidence,
    )


def make_surface_analysis(
    *,
    confidence: float = 0.8,
) -> SurfaceIntelligenceAnalysis:
    analysis = SurfaceIntelligenceAnalysis(
        health=SurfaceHealthLevel.HEALTHY,
        consistency=SurfaceConsistencyLevel.CONSISTENT,
        overall_bias=MarketBias.NEUTRAL,
        institutional_confidence=confidence,
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


def make_strike(
    strike_price: float,
    *,
    call_vanna: float | None = 0.0,
    put_vanna: float | None = 0.0,
    call_gamma: float | None = 0.0,
    put_gamma: float | None = 0.0,
    call_oi: int = 0,
    put_oi: int = 0,
) -> OptionStrikeSnapshot:
    return OptionStrikeSnapshot(
        strike_price=strike_price,
        call_open_interest=call_oi,
        put_open_interest=put_oi,
        call_gamma=call_gamma,
        put_gamma=put_gamma,
        call_vanna=call_vanna,
        put_vanna=put_vanna,
    )


def make_snapshot(
    strikes: tuple[OptionStrikeSnapshot, ...] | None = None,
    underlying_price: float = 100.0,
) -> OptionChainSnapshot:
    if strikes is None:
        strikes = ()
    return OptionChainSnapshot(
        underlying="TEST",
        expiry=datetime(2026, 7, 17),
        timestamp=NOW,
        strikes=strikes,
        underlying_price=underlying_price,
    )


def make_option_chain_analysis() -> OptionChainAnalysis:
    return OptionChainAnalysis(
        overall_bias=MarketBias.NEUTRAL,
        confidence=0.8,
        support=None,
        resistance=None,
        pcr=1.0,
        highest_put_strike=None,
        highest_call_strike=None,
        bullish_score=50.0,
        bearish_score=50.0,
        neutral_score=50.0,
    )


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestVannaRegimeType:
    def test_enum_values(self) -> None:
        assert VannaRegimeType.POSITIVE.value == "positive"
        assert VannaRegimeType.NEGATIVE.value == "negative"
        assert VannaRegimeType.BALANCED.value == "balanced"
        assert VannaRegimeType.UNKNOWN.value == "unknown"


class TestVannaPressureLevel:
    def test_enum_values(self) -> None:
        assert VannaPressureLevel.LOW.value == "low"
        assert VannaPressureLevel.MEDIUM.value == "medium"
        assert VannaPressureLevel.HIGH.value == "high"
        assert VannaPressureLevel.EXTREME.value == "extreme"
        assert VannaPressureLevel.UNKNOWN.value == "unknown"


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestVannaRegime:
    def test_creation(self) -> None:
        regime = VannaRegime(
            regime_type=VannaRegimeType.POSITIVE,
            net_vanna=0.05,
            confidence=0.8,
            reasons=("Net vanna is positive.",),
        )
        assert regime.regime_type is VannaRegimeType.POSITIVE
        assert regime.net_vanna == 0.05
        assert regime.confidence == 0.8
        assert regime.reasons == ("Net vanna is positive.",)

    def test_frozen(self) -> None:
        regime = VannaRegime(
            regime_type=VannaRegimeType.UNKNOWN,
            net_vanna=None,
            confidence=0.0,
        )
        with pytest.raises(AttributeError):
            regime.regime_type = VannaRegimeType.POSITIVE  # type: ignore[misc]

    def test_defaults(self) -> None:
        regime = VannaRegime(
            regime_type=VannaRegimeType.UNKNOWN,
            net_vanna=None,
            confidence=0.0,
        )
        assert regime.reasons == ()


class TestVannaPressure:
    def test_creation(self) -> None:
        pressure = VannaPressure(
            pressure_level=VannaPressureLevel.HIGH,
            dealer_response="Elevated vanna pressure.",
            iv_sensitivity=0.7,
            price_sensitivity=0.5,
            confidence=0.7,
            reasons=("Positive vanna regime.",),
        )
        assert pressure.pressure_level is VannaPressureLevel.HIGH
        assert pressure.iv_sensitivity == 0.7
        assert pressure.price_sensitivity == 0.5
        assert pressure.confidence == 0.7
        assert "Elevated" in pressure.dealer_response

    def test_frozen(self) -> None:
        pressure = VannaPressure(
            pressure_level=VannaPressureLevel.UNKNOWN,
            dealer_response="Unknown.",
            iv_sensitivity=0.0,
            price_sensitivity=0.0,
            confidence=0.0,
        )
        with pytest.raises(AttributeError):
            pressure.pressure_level = VannaPressureLevel.HIGH  # type: ignore[misc]

    def test_defaults(self) -> None:
        pressure = VannaPressure(
            pressure_level=VannaPressureLevel.UNKNOWN,
            dealer_response="",
            iv_sensitivity=0.0,
            price_sensitivity=0.0,
            confidence=0.0,
        )
        assert pressure.reasons == ()


class TestVannaExplanation:
    def test_creation(self) -> None:
        exp = VannaExplanation(
            overall_vanna="Positive vanna.",
            dealer_sensitivity="High sensitivity.",
            iv_impact="IV spikes create sell pressure.",
            price_impact="Price drops reduce pressure.",
            institutional_interpretation="Standard conditions.",
            risk_assessment="No elevated risk.",
        )
        assert "Positive" in exp.overall_vanna
        assert "High sensitivity" in exp.dealer_sensitivity
        assert "sell pressure" in exp.iv_impact

    def test_defaults(self) -> None:
        exp = VannaExplanation()
        assert exp.overall_vanna == ""


class TestVannaExposureInput:
    def test_creation(self) -> None:
        inp = VannaExposureInput()
        assert inp.dealer_positioning is None
        assert inp.gamma_exposure is None
        assert inp.greeks is None
        assert inp.surface is None
        assert inp.option_chain is None
        assert inp.option_chain_snapshot is None

    def test_frozen(self) -> None:
        inp = VannaExposureInput()
        with pytest.raises(AttributeError):
            inp.greeks = make_greeks_analysis()  # type: ignore[misc]


class TestVannaExposureAnalysis:
    def test_creation(self) -> None:
        regime = VannaRegime(
            regime_type=VannaRegimeType.POSITIVE,
            net_vanna=0.05,
            confidence=0.8,
        )
        pressure = VannaPressure(
            pressure_level=VannaPressureLevel.MEDIUM,
            dealer_response="Moderate pressure.",
            iv_sensitivity=0.5,
            price_sensitivity=0.3,
            confidence=0.7,
        )
        analysis = VannaExposureAnalysis(
            net_vanna=0.05,
            regime=regime,
            pressure=pressure,
            confidence=0.75,
        )
        assert analysis.net_vanna == 0.05
        assert analysis.regime.regime_type is VannaRegimeType.POSITIVE
        assert analysis.pressure.pressure_level is VannaPressureLevel.MEDIUM
        assert analysis.confidence == 0.75
        assert analysis.evidence is None
        assert analysis.explanation is None

    def test_frozen(self) -> None:
        regime = VannaRegime(
            regime_type=VannaRegimeType.UNKNOWN,
            net_vanna=None,
            confidence=0.0,
        )
        pressure = VannaPressure(
            pressure_level=VannaPressureLevel.UNKNOWN,
            dealer_response="",
            iv_sensitivity=0.0,
            price_sensitivity=0.0,
            confidence=0.0,
        )
        analysis = VannaExposureAnalysis(
            net_vanna=None,
            regime=regime,
            pressure=pressure,
            confidence=0.0,
        )
        with pytest.raises(AttributeError):
            analysis.net_vanna = 0.05  # type: ignore[misc]

    def test_neutral_placeholder(self) -> None:
        placeholder = VannaExposureAnalysis.neutral_placeholder()
        assert placeholder.net_vanna is None
        assert placeholder.regime.regime_type is VannaRegimeType.UNKNOWN
        assert placeholder.pressure.pressure_level is VannaPressureLevel.UNKNOWN
        assert placeholder.confidence == 0.0
        assert "unavailable" in placeholder.warnings[0]

    def test_with_evidence(self) -> None:
        evidence = make_evidence()
        regime = VannaRegime(
            regime_type=VannaRegimeType.POSITIVE,
            net_vanna=0.02,
            confidence=0.7,
        )
        pressure = VannaPressure(
            pressure_level=VannaPressureLevel.LOW,
            dealer_response="Low pressure.",
            iv_sensitivity=0.2,
            price_sensitivity=0.1,
            confidence=0.6,
        )
        analysis = VannaExposureAnalysis(
            net_vanna=0.02,
            regime=regime,
            pressure=pressure,
            confidence=0.65,
            evidence=evidence,
        )
        assert analysis.evidence is evidence


# ---------------------------------------------------------------------------
# VannaRegimeAnalyzer tests
# ---------------------------------------------------------------------------


class TestVannaRegimeAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = VannaRegimeAnalyzer()
        inp = VannaExposureInput()
        result = analyzer.analyze(inp)
        assert result.regime_type is VannaRegimeType.UNKNOWN
        assert result.net_vanna is None
        assert result.confidence == 0.0

    def test_positive_vanna_from_snapshot(self) -> None:
        analyzer = VannaRegimeAnalyzer()
        strikes = (
            make_strike(100.0, call_vanna=0.001, call_oi=5000),
            make_strike(105.0, call_vanna=0.0005, call_oi=2000),
        )
        snapshot = make_snapshot(strikes)
        inp = VannaExposureInput(option_chain_snapshot=snapshot)
        result = analyzer.analyze(inp)
        assert result.regime_type is VannaRegimeType.POSITIVE
        assert result.net_vanna is not None
        assert result.net_vanna > 0
        assert result.confidence > 0

    def test_negative_vanna_from_snapshot(self) -> None:
        analyzer = VannaRegimeAnalyzer()
        strikes = (
            make_strike(100.0, put_vanna=-0.001, put_oi=5000),
            make_strike(95.0, put_vanna=-0.0005, put_oi=3000),
        )
        snapshot = make_snapshot(strikes)
        inp = VannaExposureInput(option_chain_snapshot=snapshot)
        result = analyzer.analyze(inp)
        assert result.regime_type is VannaRegimeType.NEGATIVE
        assert result.net_vanna is not None
        assert result.net_vanna < 0
        assert result.confidence > 0

    def test_balanced_vanna(self) -> None:
        analyzer = VannaRegimeAnalyzer()
        strikes = (
            make_strike(
                100.0, call_vanna=0.001, call_oi=1000, put_vanna=-0.001, put_oi=1000
            ),
        )
        snapshot = make_snapshot(strikes)
        inp = VannaExposureInput(option_chain_snapshot=snapshot)
        result = analyzer.analyze(inp)
        assert result.regime_type is VannaRegimeType.BALANCED

    def test_missing_vanna_in_snapshot(self) -> None:
        analyzer = VannaRegimeAnalyzer()
        strikes = (make_strike(100.0, call_vanna=None, put_vanna=None, call_oi=1000),)
        snapshot = make_snapshot(strikes)
        inp = VannaExposureInput(option_chain_snapshot=snapshot)
        result = analyzer.analyze(inp)
        assert result.regime_type is VannaRegimeType.UNKNOWN
        assert result.net_vanna is None

    def test_fallback_confidence_from_greeks(self) -> None:
        analyzer = VannaRegimeAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.01, confidence=0.8)
        inp = VannaExposureInput(greeks=greeks)
        result = analyzer.analyze(inp)
        assert result.regime_type is VannaRegimeType.UNKNOWN
        assert result.confidence == pytest.approx(0.24, rel=1e-3)

    def test_vanna_with_gamma_exposure_context(self) -> None:
        analyzer = VannaRegimeAnalyzer()
        gex = make_gamma_exposure(regime=GammaRegime.POSITIVE, confidence=0.7)
        inp = VannaExposureInput(gamma_exposure=gex)
        result = analyzer.analyze(inp)
        assert result.regime_type is VannaRegimeType.UNKNOWN
        assert result.confidence == pytest.approx(0.21, rel=1e-3)


# ---------------------------------------------------------------------------
# VannaPressureAnalyzer tests
# ---------------------------------------------------------------------------


class TestVannaPressureAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = VannaPressureAnalyzer()
        regime = VannaRegime(
            regime_type=VannaRegimeType.UNKNOWN,
            net_vanna=None,
            confidence=0.0,
        )
        inp = VannaExposureInput()
        result = analyzer.analyze(inp, regime)
        assert result.pressure_level is VannaPressureLevel.LOW
        assert result.iv_sensitivity == 0.0
        assert result.price_sensitivity == 0.0
        assert result.confidence == 0.0

    def test_positive_regime_elevates_iv_sensitivity(self) -> None:
        analyzer = VannaPressureAnalyzer()
        regime = VannaRegime(
            regime_type=VannaRegimeType.POSITIVE,
            net_vanna=0.05,
            confidence=0.8,
        )
        inp = VannaExposureInput()
        result = analyzer.analyze(inp, regime)
        assert result.iv_sensitivity > 0.3
        assert result.confidence > 0

    def test_short_gamma_amplifies_price_sensitivity(self) -> None:
        analyzer = VannaPressureAnalyzer()
        regime = VannaRegime(
            regime_type=VannaRegimeType.POSITIVE,
            net_vanna=0.02,
            confidence=0.7,
        )
        gex = make_gamma_exposure(regime=GammaRegime.NEGATIVE, confidence=0.7)
        inp = VannaExposureInput(gamma_exposure=gex)
        result = analyzer.analyze(inp, regime)
        assert result.price_sensitivity > 0.3

    def test_high_hedging_pressure_amplifies(self) -> None:
        analyzer = VannaPressureAnalyzer()
        regime = VannaRegime(
            regime_type=VannaRegimeType.POSITIVE,
            net_vanna=0.02,
            confidence=0.7,
        )
        dp = make_dealer_positioning(confidence=0.7)
        object.__setattr__(dp, "hedging_pressure", 0.8)
        inp = VannaExposureInput(dealer_positioning=dp)
        result = analyzer.analyze(inp, regime)
        assert result.confidence > 0

    def test_pressure_levels_by_sensitivity(self) -> None:
        analyzer = VannaPressureAnalyzer()
        regime = VannaRegime(
            regime_type=VannaRegimeType.POSITIVE,
            net_vanna=0.05,
            confidence=0.9,
        )
        inp = VannaExposureInput()
        result = analyzer.analyze(inp, regime)
        assert result.pressure_level is VannaPressureLevel.MEDIUM

    def test_dealer_response_string_positive(self) -> None:
        analyzer = VannaPressureAnalyzer()
        regime = VannaRegime(
            regime_type=VannaRegimeType.POSITIVE,
            net_vanna=0.05,
            confidence=0.8,
        )
        inp = VannaExposureInput()
        result = analyzer.analyze(inp, regime)
        assert "Positive vanna" in result.dealer_response


# ---------------------------------------------------------------------------
# VannaExposureAnalyzer tests
# ---------------------------------------------------------------------------


class TestVannaExposureAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = VannaExposureAnalyzer()
        result = analyzer.analyze()
        assert result.regime.regime_type is VannaRegimeType.UNKNOWN
        assert result.confidence == 0.0
        assert result.explanation is not None
        assert "No vanna exposure inputs provided." in result.warnings[0]

    def test_positive_vanna(self) -> None:
        analyzer = VannaExposureAnalyzer()
        strikes = (make_strike(100.0, call_vanna=0.001, call_oi=5000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        assert result.regime.regime_type is VannaRegimeType.POSITIVE
        assert result.net_vanna is not None
        assert result.net_vanna > 0
        assert result.confidence > 0

    def test_negative_vanna(self) -> None:
        analyzer = VannaExposureAnalyzer()
        strikes = (make_strike(100.0, put_vanna=-0.001, put_oi=5000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        assert result.regime.regime_type is VannaRegimeType.NEGATIVE
        assert result.net_vanna is not None
        assert result.net_vanna < 0

    def test_balanced_vanna(self) -> None:
        analyzer = VannaExposureAnalyzer()
        strikes = (
            make_strike(
                100.0, call_vanna=0.001, call_oi=1000, put_vanna=-0.001, put_oi=1000
            ),
        )
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        assert result.regime.regime_type is VannaRegimeType.BALANCED

    def test_missing_vanna(self) -> None:
        analyzer = VannaExposureAnalyzer()
        result = analyzer.analyze(
            greeks=make_greeks_analysis(net_gamma=0.01, confidence=0.8)
        )
        assert result.regime.regime_type is VannaRegimeType.UNKNOWN
        assert result.net_vanna is None

    def test_with_gamma_exposure_context(self) -> None:
        analyzer = VannaExposureAnalyzer()
        gex = make_gamma_exposure(regime=GammaRegime.NEGATIVE, confidence=0.7)
        strikes = (make_strike(100.0, call_vanna=0.001, call_oi=5000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(
            gamma_exposure=gex,
            option_chain_snapshot=snapshot,
        )
        assert result.regime.regime_type is VannaRegimeType.POSITIVE
        assert result.confidence > 0
        assert result.pressure.price_sensitivity > 0.3

    def test_with_dealer_positioning(self) -> None:
        analyzer = VannaExposureAnalyzer()
        dp = make_dealer_positioning(confidence=0.7)
        strikes = (make_strike(100.0, call_vanna=0.001, call_oi=3000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(
            dealer_positioning=dp,
            option_chain_snapshot=snapshot,
        )
        assert result.confidence > 0
        assert result.pressure.confidence > 0

    def test_evidence_generated(self) -> None:
        analyzer = VannaExposureAnalyzer()
        strikes = (make_strike(100.0, call_vanna=0.001, call_oi=5000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        evidence = result.evidence
        assert evidence is not None
        assert evidence.source == "Vanna Exposure"
        assert evidence.category is EvidenceCategory.OPTION_CHAIN
        assert evidence.signal is EvidenceSignal.BULLISH
        assert len(evidence.reasons) > 0

    def test_evidence_negative_signal(self) -> None:
        analyzer = VannaExposureAnalyzer()
        strikes = (make_strike(100.0, put_vanna=-0.001, put_oi=5000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        evidence = result.evidence
        assert evidence is not None
        assert evidence.signal is EvidenceSignal.BEARISH

    def test_explanation_generated(self) -> None:
        analyzer = VannaExposureAnalyzer()
        strikes = (make_strike(100.0, call_vanna=0.001, call_oi=5000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        explanation = result.explanation
        assert explanation is not None
        assert isinstance(explanation, VannaExplanation)
        assert "Overall Vanna" in explanation.overall_vanna
        assert "Dealer Sensitivity" in explanation.dealer_sensitivity
        assert "IV Impact" in explanation.iv_impact
        assert "Price Impact" in explanation.price_impact
        assert "Interpretation" in explanation.institutional_interpretation
        assert "Risk" in explanation.risk_assessment

    def test_serialization_round_trip(self) -> None:
        analyzer = VannaExposureAnalyzer()
        strikes = (make_strike(100.0, call_vanna=0.001, call_oi=3000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        regime_val: str = result.regime.regime_type.value
        pressure_val: str = result.pressure.pressure_level.value
        assert regime_val in ("positive", "negative", "balanced", "unknown")
        assert pressure_val in (
            "low",
            "medium",
            "high",
            "extreme",
            "unknown",
        )
        assert 0.0 <= result.confidence <= 1.0
        assert 0.0 <= result.pressure.iv_sensitivity <= 1.0
        assert 0.0 <= result.pressure.price_sensitivity <= 1.0

    def test_partial_inputs_snapshot_only(self) -> None:
        analyzer = VannaExposureAnalyzer()
        strikes = (make_strike(100.0, call_vanna=0.001, call_oi=3000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        assert result.net_vanna is not None
        assert result.confidence > 0
        assert result.explanation is not None

    def test_all_inputs_converge(self) -> None:
        analyzer = VannaExposureAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.02, confidence=0.8)
        dp = make_dealer_positioning(confidence=0.7)
        gex = make_gamma_exposure(regime=GammaRegime.POSITIVE, confidence=0.7)
        surface = make_surface_analysis()
        chain = make_option_chain_analysis()
        strikes = (
            make_strike(
                100.0, call_vanna=0.001, call_oi=5000, put_vanna=-0.0002, put_oi=2000
            ),
        )
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(
            dealer_positioning=dp,
            gamma_exposure=gex,
            greeks=greeks,
            surface=surface,
            option_chain=chain,
            option_chain_snapshot=snapshot,
        )
        assert result.regime.regime_type is VannaRegimeType.POSITIVE
        assert result.net_vanna is not None
        assert result.confidence > 0.3
        assert result.evidence is not None
        assert result.explanation is not None
