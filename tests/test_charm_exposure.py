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
    CharmExposureAnalysis,
    CharmExposureAnalyzer,
    CharmExposureInput,
    CharmExplanation,
    CharmPressure,
    CharmPressureAnalyzer,
    CharmPressureLevel,
    CharmRegime,
    CharmRegimeAnalyzer,
    CharmRegimeType,
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
    VannaExposureAnalysis,
    VannaPressure,
    VannaPressureLevel,
    VannaRegime,
    VannaRegimeType,
)

NOW = datetime(2026, 7, 2, 9, 30)
FAR_EXPIRY = datetime(2026, 7, 17)
NEAR_EXPIRY = datetime(2026, 7, 5)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_strike(
    strike_price: float,
    *,
    call_charm: float | None = 0.0,
    put_charm: float | None = 0.0,
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
        call_charm=call_charm,
        put_charm=put_charm,
    )


def make_snapshot(
    strikes: tuple[OptionStrikeSnapshot, ...] | None = None,
    underlying_price: float = 100.0,
    expiry: datetime = FAR_EXPIRY,
    timestamp: datetime = NOW,
) -> OptionChainSnapshot:
    if strikes is None:
        strikes = ()
    return OptionChainSnapshot(
        underlying="TEST",
        expiry=expiry,
        timestamp=timestamp,
        strikes=strikes,
        underlying_price=underlying_price,
    )


def make_greeks(
    net_gamma: float | None = 0.0, confidence: float = 0.8
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
    confidence: float = 0.7,
    hedging_pressure: float = 0.0,
) -> DealerPositioningAnalysis:
    return DealerPositioningAnalysis(
        dealer_side=DealerSide.NEUTRAL,
        dealer_bias=DealerBiasLevel.NEUTRAL,
        hedging_pressure=hedging_pressure,
        confidence=confidence,
    )


def make_gamma_exposure(
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


def make_vanna_exposure(
    regime: VannaRegimeType = VannaRegimeType.UNKNOWN,
    confidence: float = 0.7,
) -> VannaExposureAnalysis:
    return VannaExposureAnalysis(
        net_vanna=0.0,
        regime=VannaRegime(
            regime_type=regime,
            net_vanna=None,
            confidence=confidence * 0.8,
        ),
        pressure=VannaPressure(
            pressure_level=VannaPressureLevel.UNKNOWN,
            dealer_response="",
            iv_sensitivity=0.0,
            price_sensitivity=0.0,
            confidence=confidence * 0.6,
        ),
        confidence=confidence,
    )


def make_chain_analysis() -> OptionChainAnalysis:
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


class TestCharmRegimeType:
    def test_enum_values(self) -> None:
        assert CharmRegimeType.POSITIVE.value == "positive"
        assert CharmRegimeType.NEGATIVE.value == "negative"
        assert CharmRegimeType.BALANCED.value == "balanced"
        assert CharmRegimeType.UNKNOWN.value == "unknown"


class TestCharmPressureLevel:
    def test_enum_values(self) -> None:
        assert CharmPressureLevel.LOW.value == "low"
        assert CharmPressureLevel.MEDIUM.value == "medium"
        assert CharmPressureLevel.HIGH.value == "high"
        assert CharmPressureLevel.EXTREME.value == "extreme"
        assert CharmPressureLevel.UNKNOWN.value == "unknown"


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestCharmRegime:
    def test_creation(self) -> None:
        regime = CharmRegime(
            regime_type=CharmRegimeType.POSITIVE,
            net_charm=0.05,
            confidence=0.8,
            reasons=("Net charm is positive.",),
        )
        assert regime.regime_type is CharmRegimeType.POSITIVE
        assert regime.net_charm == 0.05
        assert regime.confidence == 0.8
        assert regime.reasons == ("Net charm is positive.",)

    def test_frozen(self) -> None:
        regime = CharmRegime(
            regime_type=CharmRegimeType.UNKNOWN,
            net_charm=None,
            confidence=0.0,
        )
        with pytest.raises(AttributeError):
            regime.regime_type = CharmRegimeType.POSITIVE  # type: ignore[misc]

    def test_defaults(self) -> None:
        regime = CharmRegime(
            regime_type=CharmRegimeType.UNKNOWN,
            net_charm=None,
            confidence=0.0,
        )
        assert regime.reasons == ()


class TestCharmPressure:
    def test_creation(self) -> None:
        pressure = CharmPressure(
            pressure_level=CharmPressureLevel.HIGH,
            dealer_response="Elevated charm pressure.",
            time_sensitivity=0.7,
            near_expiry_risk=True,
            confidence=0.7,
            reasons=("Positive charm regime.",),
        )
        assert pressure.pressure_level is CharmPressureLevel.HIGH
        assert pressure.time_sensitivity == 0.7
        assert pressure.near_expiry_risk is True
        assert pressure.confidence == 0.7
        assert "Elevated" in pressure.dealer_response

    def test_frozen(self) -> None:
        pressure = CharmPressure(
            pressure_level=CharmPressureLevel.UNKNOWN,
            dealer_response="Unknown.",
            time_sensitivity=0.0,
            near_expiry_risk=False,
            confidence=0.0,
        )
        with pytest.raises(AttributeError):
            pressure.pressure_level = CharmPressureLevel.HIGH  # type: ignore[misc]

    def test_defaults(self) -> None:
        pressure = CharmPressure(
            pressure_level=CharmPressureLevel.UNKNOWN,
            dealer_response="",
            time_sensitivity=0.0,
            near_expiry_risk=False,
            confidence=0.0,
        )
        assert pressure.reasons == ()


class TestCharmExplanation:
    def test_creation(self) -> None:
        exp = CharmExplanation(
            overall_charm="Positive charm.",
            dealer_delta_decay="High decay.",
            time_decay_impact="Systematic buy pressure.",
            near_expiry_risk="Near-expiry elevated.",
            institutional_interpretation="Standard conditions.",
            risk_assessment="No elevated risk.",
        )
        assert "Positive" in exp.overall_charm
        assert "High decay" in exp.dealer_delta_decay
        assert "buy pressure" in exp.time_decay_impact

    def test_defaults(self) -> None:
        exp = CharmExplanation()
        assert exp.overall_charm == ""


class TestCharmExposureInput:
    def test_creation(self) -> None:
        inp = CharmExposureInput()
        assert inp.dealer_positioning is None
        assert inp.gamma_exposure is None
        assert inp.vanna_exposure is None
        assert inp.greeks is None
        assert inp.surface is None
        assert inp.option_chain is None
        assert inp.option_chain_snapshot is None

    def test_frozen(self) -> None:
        inp = CharmExposureInput()
        with pytest.raises(AttributeError):
            inp.greeks = make_greeks()  # type: ignore[misc]


class TestCharmExposureAnalysis:
    def test_creation(self) -> None:
        regime = CharmRegime(
            regime_type=CharmRegimeType.POSITIVE,
            net_charm=0.05,
            confidence=0.8,
        )
        pressure = CharmPressure(
            pressure_level=CharmPressureLevel.MEDIUM,
            dealer_response="Moderate pressure.",
            time_sensitivity=0.5,
            near_expiry_risk=False,
            confidence=0.7,
        )
        analysis = CharmExposureAnalysis(
            net_charm=0.05,
            regime=regime,
            pressure=pressure,
            dealer_delta_decay=0.5,
            near_expiry_risk=False,
            confidence=0.75,
        )
        assert analysis.net_charm == 0.05
        assert analysis.regime.regime_type is CharmRegimeType.POSITIVE
        assert analysis.pressure.pressure_level is CharmPressureLevel.MEDIUM
        assert analysis.confidence == 0.75
        assert analysis.dealer_delta_decay == 0.5
        assert analysis.near_expiry_risk is False
        assert analysis.evidence is None
        assert analysis.explanation is None

    def test_frozen(self) -> None:
        regime = CharmRegime(
            regime_type=CharmRegimeType.UNKNOWN,
            net_charm=None,
            confidence=0.0,
        )
        pressure = CharmPressure(
            pressure_level=CharmPressureLevel.UNKNOWN,
            dealer_response="",
            time_sensitivity=0.0,
            near_expiry_risk=False,
            confidence=0.0,
        )
        analysis = CharmExposureAnalysis(
            net_charm=None,
            regime=regime,
            pressure=pressure,
            dealer_delta_decay=0.0,
            near_expiry_risk=False,
            confidence=0.0,
        )
        with pytest.raises(AttributeError):
            analysis.net_charm = 0.05  # type: ignore[misc]

    def test_neutral_placeholder(self) -> None:
        placeholder = CharmExposureAnalysis.neutral_placeholder()
        assert placeholder.net_charm is None
        assert placeholder.regime.regime_type is CharmRegimeType.UNKNOWN
        assert placeholder.pressure.pressure_level is CharmPressureLevel.UNKNOWN
        assert placeholder.dealer_delta_decay == 0.0
        assert placeholder.near_expiry_risk is False
        assert placeholder.confidence == 0.0
        assert "unavailable" in placeholder.warnings[0]

    def test_with_evidence(self) -> None:
        evidence = Evidence(
            source="test",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=EvidenceSignal.NEUTRAL,
            score=Score(50.0),
            confidence=Confidence(0.5),
            weight=1.0,
        )
        regime = CharmRegime(
            regime_type=CharmRegimeType.POSITIVE,
            net_charm=0.02,
            confidence=0.7,
        )
        pressure = CharmPressure(
            pressure_level=CharmPressureLevel.LOW,
            dealer_response="Low pressure.",
            time_sensitivity=0.2,
            near_expiry_risk=False,
            confidence=0.6,
        )
        analysis = CharmExposureAnalysis(
            net_charm=0.02,
            regime=regime,
            pressure=pressure,
            dealer_delta_decay=0.2,
            near_expiry_risk=False,
            confidence=0.65,
            evidence=evidence,
        )
        assert analysis.evidence is evidence


# ---------------------------------------------------------------------------
# CharmRegimeAnalyzer tests
# ---------------------------------------------------------------------------


class TestCharmRegimeAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = CharmRegimeAnalyzer()
        inp = CharmExposureInput()
        result = analyzer.analyze(inp)
        assert result.regime_type is CharmRegimeType.UNKNOWN
        assert result.net_charm is None
        assert result.confidence == 0.0

    def test_positive_charm_from_snapshot(self) -> None:
        analyzer = CharmRegimeAnalyzer()
        strikes = (
            make_strike(100.0, call_charm=0.001, call_oi=5000),
            make_strike(105.0, call_charm=0.0005, call_oi=2000),
        )
        snapshot = make_snapshot(strikes)
        inp = CharmExposureInput(option_chain_snapshot=snapshot)
        result = analyzer.analyze(inp)
        assert result.regime_type is CharmRegimeType.POSITIVE
        assert result.net_charm is not None
        assert result.net_charm > 0
        assert result.confidence > 0

    def test_negative_charm_from_snapshot(self) -> None:
        analyzer = CharmRegimeAnalyzer()
        strikes = (
            make_strike(100.0, put_charm=-0.001, put_oi=5000),
            make_strike(95.0, put_charm=-0.0005, put_oi=3000),
        )
        snapshot = make_snapshot(strikes)
        inp = CharmExposureInput(option_chain_snapshot=snapshot)
        result = analyzer.analyze(inp)
        assert result.regime_type is CharmRegimeType.NEGATIVE
        assert result.net_charm is not None
        assert result.net_charm < 0
        assert result.confidence > 0

    def test_balanced_charm(self) -> None:
        analyzer = CharmRegimeAnalyzer()
        strikes = (
            make_strike(
                100.0, call_charm=0.001, call_oi=1000, put_charm=-0.001, put_oi=1000
            ),
        )
        snapshot = make_snapshot(strikes)
        inp = CharmExposureInput(option_chain_snapshot=snapshot)
        result = analyzer.analyze(inp)
        assert result.regime_type is CharmRegimeType.BALANCED

    def test_missing_charm_in_snapshot(self) -> None:
        analyzer = CharmRegimeAnalyzer()
        strikes = (make_strike(100.0, call_charm=None, put_charm=None, call_oi=1000),)
        snapshot = make_snapshot(strikes)
        inp = CharmExposureInput(option_chain_snapshot=snapshot)
        result = analyzer.analyze(inp)
        assert result.regime_type is CharmRegimeType.UNKNOWN
        assert result.net_charm is None

    def test_fallback_confidence_from_greeks(self) -> None:
        analyzer = CharmRegimeAnalyzer()
        greeks = make_greeks(net_gamma=0.01, confidence=0.8)
        inp = CharmExposureInput(greeks=greeks)
        result = analyzer.analyze(inp)
        assert result.regime_type is CharmRegimeType.UNKNOWN
        assert result.confidence == pytest.approx(0.24, rel=1e-3)

    def test_fallback_confidence_from_vanna(self) -> None:
        analyzer = CharmRegimeAnalyzer()
        vex = make_vanna_exposure(confidence=0.7)
        inp = CharmExposureInput(vanna_exposure=vex)
        result = analyzer.analyze(inp)
        assert result.regime_type is CharmRegimeType.UNKNOWN
        assert result.confidence == pytest.approx(0.21, rel=1e-3)


# ---------------------------------------------------------------------------
# CharmPressureAnalyzer tests
# ---------------------------------------------------------------------------


class TestCharmPressureAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = CharmPressureAnalyzer()
        regime = CharmRegime(
            regime_type=CharmRegimeType.UNKNOWN,
            net_charm=None,
            confidence=0.0,
        )
        inp = CharmExposureInput()
        result = analyzer.analyze(inp, regime)
        assert result.pressure_level is CharmPressureLevel.LOW
        assert result.time_sensitivity == 0.0
        assert result.near_expiry_risk is False
        assert result.confidence == 0.0

    def test_positive_regime_elevates_time_sensitivity(self) -> None:
        analyzer = CharmPressureAnalyzer()
        regime = CharmRegime(
            regime_type=CharmRegimeType.POSITIVE,
            net_charm=0.05,
            confidence=0.8,
        )
        inp = CharmExposureInput()
        result = analyzer.analyze(inp, regime)
        assert result.time_sensitivity >= 0.3
        assert result.confidence > 0

    def test_near_expiry_risk_true_within_7_days(self) -> None:
        analyzer = CharmPressureAnalyzer()
        regime = CharmRegime(
            regime_type=CharmRegimeType.POSITIVE,
            net_charm=0.02,
            confidence=0.7,
        )
        snapshot = make_snapshot(expiry=NEAR_EXPIRY, timestamp=NOW)
        inp = CharmExposureInput(option_chain_snapshot=snapshot)
        result = analyzer.analyze(inp, regime)
        assert result.near_expiry_risk is True

    def test_near_expiry_risk_false_far_expiry(self) -> None:
        analyzer = CharmPressureAnalyzer()
        regime = CharmRegime(
            regime_type=CharmRegimeType.POSITIVE,
            net_charm=0.02,
            confidence=0.7,
        )
        inp = CharmExposureInput()
        result = analyzer.analyze(inp, regime)
        assert result.near_expiry_risk is False

    def test_short_gamma_amplifies_time_sensitivity(self) -> None:
        analyzer = CharmPressureAnalyzer()
        regime = CharmRegime(
            regime_type=CharmRegimeType.POSITIVE,
            net_charm=0.02,
            confidence=0.7,
        )
        gex = make_gamma_exposure(regime=GammaRegime.NEGATIVE, confidence=0.7)
        inp = CharmExposureInput(gamma_exposure=gex)
        result = analyzer.analyze(inp, regime)
        assert result.time_sensitivity > 0.25

    def test_vanna_context_increases_confidence(self) -> None:
        analyzer = CharmPressureAnalyzer()
        regime = CharmRegime(
            regime_type=CharmRegimeType.POSITIVE,
            net_charm=0.02,
            confidence=0.7,
        )
        vex = make_vanna_exposure(confidence=0.7)
        inp = CharmExposureInput(vanna_exposure=vex)
        result = analyzer.analyze(inp, regime)
        assert result.confidence > 0

    def test_pressure_levels_by_sensitivity(self) -> None:
        analyzer = CharmPressureAnalyzer()
        regime = CharmRegime(
            regime_type=CharmRegimeType.POSITIVE,
            net_charm=0.05,
            confidence=0.9,
        )
        inp = CharmExposureInput()
        result = analyzer.analyze(inp, regime)
        assert result.pressure_level is CharmPressureLevel.MEDIUM

    def test_dealer_response_string_positive(self) -> None:
        analyzer = CharmPressureAnalyzer()
        regime = CharmRegime(
            regime_type=CharmRegimeType.POSITIVE,
            net_charm=0.05,
            confidence=0.8,
        )
        inp = CharmExposureInput()
        result = analyzer.analyze(inp, regime)
        assert "Positive charm" in result.dealer_response


# ---------------------------------------------------------------------------
# CharmExposureAnalyzer tests
# ---------------------------------------------------------------------------


class TestCharmExposureAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = CharmExposureAnalyzer()
        result = analyzer.analyze()
        assert result.regime.regime_type is CharmRegimeType.UNKNOWN
        assert result.confidence == 0.0
        assert result.explanation is not None
        assert "No charm exposure inputs provided." in result.warnings[0]

    def test_positive_charm(self) -> None:
        analyzer = CharmExposureAnalyzer()
        strikes = (make_strike(100.0, call_charm=0.001, call_oi=5000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        assert result.regime.regime_type is CharmRegimeType.POSITIVE
        assert result.net_charm is not None
        assert result.net_charm > 0
        assert result.confidence > 0

    def test_negative_charm(self) -> None:
        analyzer = CharmExposureAnalyzer()
        strikes = (make_strike(100.0, put_charm=-0.001, put_oi=5000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        assert result.regime.regime_type is CharmRegimeType.NEGATIVE
        assert result.net_charm is not None
        assert result.net_charm < 0

    def test_balanced_charm(self) -> None:
        analyzer = CharmExposureAnalyzer()
        strikes = (
            make_strike(
                100.0, call_charm=0.001, call_oi=1000, put_charm=-0.001, put_oi=1000
            ),
        )
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        assert result.regime.regime_type is CharmRegimeType.BALANCED

    def test_missing_charm(self) -> None:
        analyzer = CharmExposureAnalyzer()
        result = analyzer.analyze(greeks=make_greeks(net_gamma=0.01, confidence=0.8))
        assert result.regime.regime_type is CharmRegimeType.UNKNOWN
        assert result.net_charm is None

    def test_with_gamma_exposure_context(self) -> None:
        analyzer = CharmExposureAnalyzer()
        gex = make_gamma_exposure(regime=GammaRegime.NEGATIVE, confidence=0.7)
        strikes = (make_strike(100.0, call_charm=0.001, call_oi=5000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(
            gamma_exposure=gex,
            option_chain_snapshot=snapshot,
        )
        assert result.regime.regime_type is CharmRegimeType.POSITIVE
        assert result.confidence > 0
        assert result.dealer_delta_decay > 0.3

    def test_with_vanna_exposure(self) -> None:
        analyzer = CharmExposureAnalyzer()
        vex = make_vanna_exposure(confidence=0.7)
        strikes = (make_strike(100.0, call_charm=0.001, call_oi=3000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(
            vanna_exposure=vex,
            option_chain_snapshot=snapshot,
        )
        assert result.confidence > 0
        assert result.pressure.confidence > 0

    def test_near_expiry_detected(self) -> None:
        analyzer = CharmExposureAnalyzer()
        strikes = (make_strike(100.0, call_charm=0.001, call_oi=5000),)
        snapshot = make_snapshot(strikes, expiry=NEAR_EXPIRY, timestamp=NOW)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        assert result.near_expiry_risk is True
        assert result.dealer_delta_decay > 0.3

    def test_evidence_generated(self) -> None:
        analyzer = CharmExposureAnalyzer()
        strikes = (make_strike(100.0, call_charm=0.001, call_oi=5000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        evidence = result.evidence
        assert evidence is not None
        assert evidence.source == "Charm Exposure"
        assert evidence.category is EvidenceCategory.OPTION_CHAIN
        assert evidence.signal is EvidenceSignal.BULLISH
        assert len(evidence.reasons) > 0

    def test_evidence_negative_signal(self) -> None:
        analyzer = CharmExposureAnalyzer()
        strikes = (make_strike(100.0, put_charm=-0.001, put_oi=5000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        evidence = result.evidence
        assert evidence is not None
        assert evidence.signal is EvidenceSignal.BEARISH

    def test_explanation_generated(self) -> None:
        analyzer = CharmExposureAnalyzer()
        strikes = (make_strike(100.0, call_charm=0.001, call_oi=5000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        explanation = result.explanation
        assert explanation is not None
        assert isinstance(explanation, CharmExplanation)
        assert "Charm Exposure" in explanation.overall_charm
        assert "Delta Decay" in explanation.dealer_delta_decay
        assert "Time Decay" in explanation.time_decay_impact
        assert "Risk" in explanation.near_expiry_risk
        assert "Interpretation" in explanation.institutional_interpretation
        assert "Risk" in explanation.risk_assessment

    def test_serialization_round_trip(self) -> None:
        analyzer = CharmExposureAnalyzer()
        strikes = (make_strike(100.0, call_charm=0.001, call_oi=3000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        regime_val: str = result.regime.regime_type.value
        pressure_val: str = result.pressure.pressure_level.value
        assert regime_val in ("positive", "negative", "balanced", "unknown")
        assert pressure_val in ("low", "medium", "high", "extreme", "unknown")
        assert 0.0 <= result.confidence <= 1.0
        assert 0.0 <= result.dealer_delta_decay <= 1.0
        assert isinstance(result.near_expiry_risk, bool)

    def test_partial_inputs_snapshot_only(self) -> None:
        analyzer = CharmExposureAnalyzer()
        strikes = (make_strike(100.0, call_charm=0.001, call_oi=3000),)
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        assert result.net_charm is not None
        assert result.confidence > 0
        assert result.explanation is not None

    def test_all_inputs_converge(self) -> None:
        analyzer = CharmExposureAnalyzer()
        greeks = make_greeks(net_gamma=0.02, confidence=0.8)
        dp = make_dealer_positioning(confidence=0.7)
        gex = make_gamma_exposure(regime=GammaRegime.POSITIVE, confidence=0.7)
        vex = make_vanna_exposure(confidence=0.7)
        chain = make_chain_analysis()
        strikes = (
            make_strike(
                100.0, call_charm=0.001, call_oi=5000, put_charm=-0.0002, put_oi=2000
            ),
        )
        snapshot = make_snapshot(strikes)
        result = analyzer.analyze(
            dealer_positioning=dp,
            gamma_exposure=gex,
            vanna_exposure=vex,
            greeks=greeks,
            option_chain=chain,
            option_chain_snapshot=snapshot,
        )
        assert result.regime.regime_type is CharmRegimeType.POSITIVE
        assert result.net_charm is not None
        assert result.confidence > 0.3
        assert result.evidence is not None
        assert result.explanation is not None
