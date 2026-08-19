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
    GammaExposureAnalyzer,
    GammaExposureExplanation,
    GammaExposureInput,
    GammaRegime,
    GammaWall,
    GammaWallsAnalyzer,
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
    WallType,
    ZeroGammaAnalyzer,
    ZeroGammaLevel,
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
    dealer_bias: DealerBiasLevel = DealerBiasLevel.NEUTRAL,
    hedging_pressure: float = 0.0,
    confidence: float = 0.7,
) -> DealerPositioningAnalysis:
    return DealerPositioningAnalysis(
        dealer_side=dealer_side,
        dealer_bias=dealer_bias,
        hedging_pressure=hedging_pressure,
        confidence=confidence,
    )


def make_option_chain_analysis(
    *,
    overall_bias: MarketBias = MarketBias.NEUTRAL,
    confidence: float = 0.8,
) -> OptionChainAnalysis:
    return OptionChainAnalysis(
        overall_bias=overall_bias,
        confidence=confidence,
        support=None,
        resistance=None,
        pcr=1.0,
        highest_put_strike=None,
        highest_call_strike=None,
        bullish_score=50.0,
        bearish_score=50.0,
        neutral_score=50.0,
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


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestGammaRegime:
    def test_enum_values(self) -> None:
        assert GammaRegime.POSITIVE.value == "positive"
        assert GammaRegime.NEGATIVE.value == "negative"
        assert GammaRegime.NEUTRAL.value == "neutral"
        assert GammaRegime.UNKNOWN.value == "unknown"


class TestWallType:
    def test_enum_values(self) -> None:
        assert WallType.CALL_WALL.value == "call_wall"
        assert WallType.PUT_WALL.value == "put_wall"
        assert WallType.NONE.value == "none"
        assert WallType.UNKNOWN.value == "unknown"


class TestPinningProbability:
    def test_enum_values(self) -> None:
        assert PinningProbability.LOW.value == "low"
        assert PinningProbability.MEDIUM.value == "medium"
        assert PinningProbability.HIGH.value == "high"
        assert PinningProbability.EXTREME.value == "extreme"
        assert PinningProbability.UNKNOWN.value == "unknown"


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestZeroGammaLevel:
    def test_creation(self) -> None:
        level = ZeroGammaLevel(
            strike=100.0,
            underlying_price=100.0,
            distance_percent=0.0,
            confidence=0.8,
        )
        assert level.strike == 100.0
        assert level.underlying_price == 100.0
        assert level.distance_percent == 0.0
        assert level.confidence == 0.8

    def test_frozen(self) -> None:
        level = ZeroGammaLevel(strike=100.0)
        with pytest.raises(AttributeError):
            level.strike = 200.0  # type: ignore[misc]

    def test_defaults(self) -> None:
        level = ZeroGammaLevel(strike=None)
        assert level.underlying_price is None
        assert level.distance_percent is None
        assert level.confidence == 0.0


class TestGammaWall:
    def test_creation(self) -> None:
        wall = GammaWall(
            strike=105.0,
            wall_type=WallType.CALL_WALL,
            gamma_concentration=0.45,
            open_interest=5000,
            confidence=0.7,
        )
        assert wall.strike == 105.0
        assert wall.wall_type is WallType.CALL_WALL
        assert wall.gamma_concentration == 0.45
        assert wall.open_interest == 5000
        assert wall.confidence == 0.7

    def test_frozen(self) -> None:
        wall = GammaWall(strike=100.0, wall_type=WallType.CALL_WALL)
        with pytest.raises(AttributeError):
            wall.strike = 200.0  # type: ignore[misc]

    def test_defaults(self) -> None:
        wall = GammaWall(strike=None, wall_type=WallType.UNKNOWN)
        assert wall.gamma_concentration is None
        assert wall.open_interest == 0
        assert wall.confidence == 0.0


class TestGammaExposureInput:
    def test_creation(self) -> None:
        inp = GammaExposureInput()
        assert inp.dealer_positioning is None
        assert inp.greeks is None
        assert inp.option_chain is None
        assert inp.surface is None
        assert inp.option_chain_snapshot is None

    def test_frozen(self) -> None:
        inp = GammaExposureInput()
        with pytest.raises(AttributeError):
            inp.greeks = make_greeks_analysis()  # type: ignore[misc]


class TestGammaExposureExplanation:
    def test_creation(self) -> None:
        exp = GammaExposureExplanation(
            gamma_regime="Positive gamma regime.",
            zero_gamma="Zero gamma at 100.",
            gamma_walls="Call wall at 105.",
            pinning_risk="High pinning.",
            volatility_implications="Low vol expansion.",
            institutional_interpretation="Standard conditions.",
        )
        assert "Positive" in exp.gamma_regime
        assert "Zero gamma" in exp.zero_gamma
        assert "Call wall" in exp.gamma_walls

    def test_defaults(self) -> None:
        exp = GammaExposureExplanation()
        assert exp.gamma_regime == ""


class TestGammaExposureAnalysis:
    def test_creation(self) -> None:
        analysis = GammaExposureAnalysis(
            net_gamma_exposure=0.0,
            gamma_regime=GammaRegime.NEUTRAL,
            zero_gamma_level=None,
            call_wall=None,
            put_wall=None,
            pinning_probability=PinningProbability.LOW,
            volatility_expansion_probability=0.3,
            confidence=0.7,
        )
        assert analysis.net_gamma_exposure == 0.0
        assert analysis.gamma_regime is GammaRegime.NEUTRAL
        assert analysis.pinning_probability is PinningProbability.LOW
        assert analysis.volatility_expansion_probability == 0.3
        assert analysis.confidence == 0.7
        assert analysis.evidence is None
        assert analysis.explanation is None

    def test_frozen(self) -> None:
        analysis = GammaExposureAnalysis(
            net_gamma_exposure=None,
            gamma_regime=GammaRegime.UNKNOWN,
            zero_gamma_level=None,
            call_wall=None,
            put_wall=None,
            pinning_probability=PinningProbability.UNKNOWN,
            volatility_expansion_probability=0.0,
            confidence=0.0,
        )
        with pytest.raises(AttributeError):
            analysis.gamma_regime = GammaRegime.POSITIVE  # type: ignore[misc]

    def test_neutral_placeholder(self) -> None:
        placeholder = GammaExposureAnalysis.neutral_placeholder()
        assert placeholder.net_gamma_exposure is None
        assert placeholder.gamma_regime is GammaRegime.UNKNOWN
        assert placeholder.zero_gamma_level is None
        assert placeholder.call_wall is None
        assert placeholder.put_wall is None
        assert placeholder.pinning_probability is PinningProbability.UNKNOWN
        assert placeholder.volatility_expansion_probability == 0.0
        assert placeholder.confidence == 0.0
        assert "unavailable" in placeholder.warnings[0]

    def test_with_evidence(self) -> None:
        evidence = make_evidence()
        analysis = GammaExposureAnalysis(
            net_gamma_exposure=0.0,
            gamma_regime=GammaRegime.POSITIVE,
            zero_gamma_level=None,
            call_wall=None,
            put_wall=None,
            pinning_probability=PinningProbability.HIGH,
            volatility_expansion_probability=0.2,
            confidence=0.8,
            evidence=evidence,
        )
        assert analysis.evidence is evidence


# ---------------------------------------------------------------------------
# ZeroGammaAnalyzer tests
# ---------------------------------------------------------------------------


class TestZeroGammaAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = ZeroGammaAnalyzer()
        inp = GammaExposureInput()
        result = analyzer.analyze(inp)
        assert result is not None
        assert result.strike is None
        assert result.confidence == 0.0

    def test_greeks_positive_regime(self) -> None:
        analyzer = ZeroGammaAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.01)
        inp = GammaExposureInput(greeks=greeks)
        result = analyzer.analyze(inp)
        assert result is not None
        assert result.confidence > 0

    def test_greeks_negative_regime(self) -> None:
        analyzer = ZeroGammaAnalyzer()
        greeks = make_greeks_analysis(net_gamma=-0.01)
        inp = GammaExposureInput(greeks=greeks)
        result = analyzer.analyze(inp)
        assert result is not None
        assert result.confidence > 0

    def test_snapshot_with_flip(self) -> None:
        analyzer = ZeroGammaAnalyzer()
        strikes = (
            make_strike(95.0, call_gamma=0.01, call_oi=1000),
            make_strike(
                100.0, call_gamma=0.02, call_oi=500, put_gamma=0.01, put_oi=500
            ),
            make_strike(105.0, put_gamma=0.03, put_oi=2000),
        )
        snapshot = make_snapshot(strikes, underlying_price=100.0)
        inp = GammaExposureInput(option_chain_snapshot=snapshot)
        result = analyzer.analyze(inp)
        assert result is not None
        assert result.strike is not None

    def test_missing_greeks_and_snapshot(self) -> None:
        analyzer = ZeroGammaAnalyzer()
        inp = GammaExposureInput()
        result = analyzer.analyze(inp)
        assert result is not None
        assert result.strike is None

    def test_confidence_with_greeks_only(self) -> None:
        analyzer = ZeroGammaAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.005, confidence=0.9)
        inp = GammaExposureInput(greeks=greeks)
        result = analyzer.analyze(inp)
        assert result is not None
        assert result.confidence > 0


# ---------------------------------------------------------------------------
# GammaWallsAnalyzer tests
# ---------------------------------------------------------------------------


class TestGammaWallsAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = GammaWallsAnalyzer()
        inp = GammaExposureInput()
        call, put = analyzer.analyze(inp)
        assert call is None
        assert put is None

    def test_no_strikes(self) -> None:
        analyzer = GammaWallsAnalyzer()
        snapshot = make_snapshot(strikes=())
        inp = GammaExposureInput(option_chain_snapshot=snapshot)
        call, put = analyzer.analyze(inp)
        assert call is None
        assert put is None

    def test_call_wall_identified(self) -> None:
        analyzer = GammaWallsAnalyzer()
        strikes = (
            make_strike(95.0, call_gamma=0.01, call_oi=100),
            make_strike(100.0, call_gamma=0.02, call_oi=500),
            make_strike(105.0, call_gamma=0.05, call_oi=3000),
            make_strike(110.0, call_gamma=0.01, call_oi=50),
        )
        snapshot = make_snapshot(strikes)
        inp = GammaExposureInput(option_chain_snapshot=snapshot)
        call, _put = analyzer.analyze(inp)
        assert call is not None
        assert call.wall_type is WallType.CALL_WALL
        assert call.strike == 105.0
        assert call.confidence > 0

    def test_put_wall_identified(self) -> None:
        analyzer = GammaWallsAnalyzer()
        strikes = (
            make_strike(90.0, put_gamma=0.04, put_oi=2000),
            make_strike(95.0, put_gamma=0.02, put_oi=500),
            make_strike(100.0, put_gamma=0.01, put_oi=100),
        )
        snapshot = make_snapshot(strikes)
        inp = GammaExposureInput(option_chain_snapshot=snapshot)
        _call, put = analyzer.analyze(inp)
        assert put is not None
        assert put.wall_type is WallType.PUT_WALL
        assert put.strike == 90.0
        assert put.confidence > 0

    def test_fallback_to_oi_when_gamma_missing(self) -> None:
        analyzer = GammaWallsAnalyzer()
        strikes = (
            make_strike(95.0, call_gamma=None, call_oi=100),
            make_strike(100.0, call_gamma=None, call_oi=5000),
            make_strike(105.0, call_gamma=None, call_oi=300),
        )
        snapshot = make_snapshot(strikes)
        inp = GammaExposureInput(option_chain_snapshot=snapshot)
        call, _put = analyzer.analyze(inp)
        assert call is not None
        assert call.strike == 100.0


# ---------------------------------------------------------------------------
# GammaExposureAnalyzer tests
# ---------------------------------------------------------------------------


class TestGammaExposureAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = GammaExposureAnalyzer()
        result = analyzer.analyze()
        assert result.gamma_regime is GammaRegime.UNKNOWN
        assert result.confidence == 0.0
        assert result.explanation is not None
        assert "No gamma exposure inputs provided." in result.warnings[0]

    def test_positive_gamma_regime(self) -> None:
        analyzer = GammaExposureAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.02, confidence=0.8)
        result = analyzer.analyze(greeks=greeks)
        assert result.gamma_regime is GammaRegime.POSITIVE
        assert result.net_gamma_exposure is not None
        assert result.confidence > 0

    def test_negative_gamma_regime(self) -> None:
        analyzer = GammaExposureAnalyzer()
        greeks = make_greeks_analysis(net_gamma=-0.02, confidence=0.8)
        result = analyzer.analyze(greeks=greeks)
        assert result.gamma_regime is GammaRegime.NEGATIVE
        assert result.net_gamma_exposure is not None

    def test_neutral_gamma_regime(self) -> None:
        analyzer = GammaExposureAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.0, confidence=0.8)
        result = analyzer.analyze(greeks=greeks)
        assert result.gamma_regime is GammaRegime.NEUTRAL

    def test_regime_from_dealer_positioning(self) -> None:
        analyzer = GammaExposureAnalyzer()
        dp = make_dealer_positioning(dealer_side=DealerSide.LONG_GAMMA, confidence=0.7)
        result = analyzer.analyze(dealer_positioning=dp)
        assert result.gamma_regime is GammaRegime.POSITIVE

    def test_regime_from_short_gamma_dealer(self) -> None:
        analyzer = GammaExposureAnalyzer()
        dp = make_dealer_positioning(dealer_side=DealerSide.SHORT_GAMMA, confidence=0.7)
        result = analyzer.analyze(dealer_positioning=dp)
        assert result.gamma_regime is GammaRegime.NEGATIVE

    def test_zero_gamma_with_snapshot(self) -> None:
        analyzer = GammaExposureAnalyzer()
        strikes = (
            make_strike(95.0, call_gamma=0.01, call_oi=1000),
            make_strike(
                100.0, call_gamma=0.02, call_oi=500, put_gamma=0.01, put_oi=500
            ),
            make_strike(105.0, put_gamma=0.03, put_oi=2000),
        )
        snapshot = make_snapshot(strikes, underlying_price=100.0)
        greeks = make_greeks_analysis(net_gamma=0.0, confidence=0.8)
        result = analyzer.analyze(greeks=greeks, option_chain_snapshot=snapshot)
        assert result.zero_gamma_level is not None

    def test_gamma_walls_with_snapshot(self) -> None:
        analyzer = GammaExposureAnalyzer()
        strikes = (
            make_strike(95.0, call_gamma=0.01, call_oi=100),
            make_strike(100.0, call_gamma=0.02, call_oi=500),
            make_strike(105.0, call_gamma=0.05, call_oi=3000),
            make_strike(95.0, put_gamma=0.04, put_oi=2000),
            make_strike(100.0, put_gamma=0.02, put_oi=500),
        )
        snapshot = make_snapshot(strikes, underlying_price=100.0)
        result = analyzer.analyze(option_chain_snapshot=snapshot)
        assert result.call_wall is not None
        assert result.put_wall is not None

    def test_pinning_long_gamma(self) -> None:
        analyzer = GammaExposureAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.02, confidence=0.8)
        result = analyzer.analyze(greeks=greeks)
        assert result.pinning_probability in (
            PinningProbability.MEDIUM,
            PinningProbability.HIGH,
            PinningProbability.LOW,
        )

    def test_volatility_expansion_short_gamma(self) -> None:
        analyzer = GammaExposureAnalyzer()
        greeks = make_greeks_analysis(net_gamma=-0.02, confidence=0.8)
        result = analyzer.analyze(greeks=greeks)
        assert result.volatility_expansion_probability > 0.3

    def test_evidence_generated(self) -> None:
        analyzer = GammaExposureAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.02, confidence=0.8)
        result = analyzer.analyze(greeks=greeks)
        evidence = result.evidence
        assert evidence is not None
        assert evidence.source == "Gamma Exposure"
        assert evidence.category is EvidenceCategory.OPTION_CHAIN
        assert evidence.signal is EvidenceSignal.BULLISH
        assert len(evidence.reasons) > 0

    def test_evidence_negative_signal(self) -> None:
        analyzer = GammaExposureAnalyzer()
        greeks = make_greeks_analysis(net_gamma=-0.02, confidence=0.8)
        result = analyzer.analyze(greeks=greeks)
        evidence = result.evidence
        assert evidence is not None
        assert evidence.signal is EvidenceSignal.BEARISH

    def test_explanation_generated(self) -> None:
        analyzer = GammaExposureAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.02, confidence=0.8)
        result = analyzer.analyze(greeks=greeks)
        explanation = result.explanation
        assert explanation is not None
        assert isinstance(explanation, GammaExposureExplanation)
        assert "Gamma Regime" in explanation.gamma_regime
        assert "Zero Gamma" in explanation.zero_gamma
        assert "Gamma Walls" in explanation.gamma_walls
        assert "Pinning" in explanation.pinning_risk
        assert "Volatility" in explanation.volatility_implications
        assert "Interpretation" in explanation.institutional_interpretation

    def test_serialization_round_trip(self) -> None:
        analyzer = GammaExposureAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.01, confidence=0.7)
        result = analyzer.analyze(greeks=greeks)
        regime_val: str = result.gamma_regime.value
        pinning_val: str = result.pinning_probability.value
        ve_prob: float = result.volatility_expansion_probability
        assert regime_val in (
            "positive",
            "negative",
            "neutral",
            "unknown",
        )
        assert pinning_val in (
            "low",
            "medium",
            "high",
            "extreme",
            "unknown",
        )
        assert 0.0 <= ve_prob <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    def test_partial_inputs_greeks_only(self) -> None:
        analyzer = GammaExposureAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.01, confidence=0.8)
        result = analyzer.analyze(greeks=greeks)
        assert result.gamma_regime is GammaRegime.POSITIVE
        assert result.confidence > 0
        assert result.explanation is not None

    def test_partial_inputs_dealer_only(self) -> None:
        analyzer = GammaExposureAnalyzer()
        dp = make_dealer_positioning(dealer_side=DealerSide.LONG_GAMMA, confidence=0.6)
        result = analyzer.analyze(dealer_positioning=dp)
        assert result.gamma_regime is GammaRegime.POSITIVE
        assert result.confidence > 0

    def test_all_inputs_converge(self) -> None:
        analyzer = GammaExposureAnalyzer()
        greeks = make_greeks_analysis(net_gamma=0.02, confidence=0.8)
        dp = make_dealer_positioning(dealer_side=DealerSide.LONG_GAMMA, confidence=0.7)
        chain = make_option_chain_analysis()
        surface = make_surface_analysis()
        strikes = (
            make_strike(95.0, call_gamma=0.01, call_oi=1000),
            make_strike(100.0, call_gamma=0.02, call_oi=500),
            make_strike(105.0, put_gamma=0.03, put_oi=2000),
        )
        snapshot = make_snapshot(strikes, underlying_price=100.0)
        result = analyzer.analyze(
            dealer_positioning=dp,
            greeks=greeks,
            option_chain=chain,
            surface=surface,
            option_chain_snapshot=snapshot,
        )
        assert result.gamma_regime is GammaRegime.POSITIVE
        assert result.zero_gamma_level is not None
        assert result.call_wall is not None
        assert result.put_wall is not None
        assert result.confidence > 0.3
        assert result.evidence is not None
        assert result.explanation is not None
