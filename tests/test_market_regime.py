import pytest

from titan.core.evidence import EvidenceCategory, EvidenceSignal
from titan.market.intelligence.market_regime import (
    MarketRegimeAnalyzer,
)
from titan.market.intelligence.models import (
    BreadthAnalysis,
    BreadthBias,
    BreadthStrength,
    DecisionContext,
    MarketRegime,
    MarketRegimeAnalysis,
    MarketRegimeExplanation,
    MarketStructureAnalysis,
    ParticipationRegime,
    StrategySuitability,
    StrategyType,
    StructureState,
    TrendDirection,
    TrendRegime,
    VolumeAnalysis,
    VolumeBias,
    VWAPAnalysis,
    VWAPBias,
)
from titan.market.intelligence.participation_regime import (
    ParticipationRegimeAnalyzer,
)
from titan.market.intelligence.strategy_suitability import (
    StrategySuitabilityAnalyzer,
)
from titan.market.intelligence.trend_regime import (
    TrendRegimeAnalyzer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_ms(
    primary_trend: TrendDirection = TrendDirection.UNKNOWN,
    structure_state: StructureState = StructureState.UNKNOWN,
    trend_strength: float = 0.0,
    confidence: float = 0.0,
) -> MarketStructureAnalysis:
    return MarketStructureAnalysis(
        primary_trend=primary_trend,
        secondary_trend=TrendDirection.UNKNOWN,
        structure_state=structure_state,
        trend_strength=trend_strength,
        confidence=confidence,
    )


def make_vwap(
    bias: VWAPBias = VWAPBias.UNKNOWN,
    confidence: float = 0.0,
) -> VWAPAnalysis:
    return VWAPAnalysis(
        vwap=100.0,
        current_price=100.0,
        bias=bias,
        confidence=confidence,
    )


def make_volume(
    bias: VolumeBias = VolumeBias.UNKNOWN,
    rvol: float = 1.0,
    confidence: float = 0.0,
) -> VolumeAnalysis:
    return VolumeAnalysis(
        current_volume=1_000_000,
        average_volume=1_000_000.0,
        relative_volume=rvol,
        volume_bias=bias,
        confidence=confidence,
    )


def make_breadth(
    bias: BreadthBias = BreadthBias.UNKNOWN,
    strength: BreadthStrength = BreadthStrength.NEUTRAL,
    divergence: bool = False,
    confidence: float = 0.0,
) -> BreadthAnalysis:
    return BreadthAnalysis(
        advance_decline_ratio=1.0,
        breadth_strength=strength,
        breadth_bias=bias,
        divergence_detected=divergence,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# TrendRegimeAnalyzer unit tests
# ---------------------------------------------------------------------------


class TestTrendRegimeAnalyzer:
    def test_none_inputs(self) -> None:
        result = TrendRegimeAnalyzer().analyze(None, None)
        assert result.confidence == 0.0
        assert "Insufficient intelligence" in result.reasons[0]

    def test_low_confidence_inputs(self) -> None:
        ms = make_ms(confidence=0.1)
        vwap = make_vwap(confidence=0.1)
        result = TrendRegimeAnalyzer().analyze(ms, vwap)
        assert result.confidence == 0.0

    def test_bullish_trend(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.7,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        result = TrendRegimeAnalyzer().analyze(ms, vwap)
        assert result.direction is TrendDirection.BULLISH
        assert result.aligned is True
        assert result.momentum_environment is True

    def test_bearish_trend(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BEARISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.7,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BEARISH, confidence=0.7)
        result = TrendRegimeAnalyzer().analyze(ms, vwap)
        assert result.direction is TrendDirection.BEARISH
        assert result.aligned is True

    def test_sideways_trend(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.SIDEWAYS,
            structure_state=StructureState.RANGING,
            trend_strength=0.3,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.NEUTRAL, confidence=0.7)
        result = TrendRegimeAnalyzer().analyze(ms, vwap)
        assert result.direction is TrendDirection.SIDEWAYS

    def test_not_aligned(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.5,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BEARISH, confidence=0.7)
        result = TrendRegimeAnalyzer().analyze(ms, vwap)
        assert result.aligned is False

    def test_mean_reversion_in_ranging(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.SIDEWAYS,
            structure_state=StructureState.RANGING,
            confidence=0.8,
        )
        vwap = make_vwap(confidence=0.7)
        result = TrendRegimeAnalyzer().analyze(ms, vwap)
        assert result.mean_reversion_environment is True

    def test_confidence_weighted(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.6)
        result = TrendRegimeAnalyzer().analyze(ms, vwap)
        assert result.confidence > 0.0

    def test_reasons_included(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.7,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        result = TrendRegimeAnalyzer().analyze(ms, vwap)
        assert len(result.reasons) > 0


# ---------------------------------------------------------------------------
# ParticipationRegimeAnalyzer unit tests
# ---------------------------------------------------------------------------


class TestParticipationRegimeAnalyzer:
    def test_none_inputs(self) -> None:
        result = ParticipationRegimeAnalyzer().analyze(None, None)
        assert result.confidence == 0.0

    def test_institutional_confirmation(self) -> None:
        vol = make_volume(bias=VolumeBias.BULLISH, confidence=0.6)
        breadth = make_breadth(bias=BreadthBias.BULLISH, confidence=0.6)
        result = ParticipationRegimeAnalyzer().analyze(vol, breadth)
        assert result.institutional_confirmation is True

    def test_compressed_market(self) -> None:
        vol = make_volume(rvol=0.5, confidence=0.6)
        breadth = make_breadth(bias=BreadthBias.NEUTRAL, confidence=0.6)
        result = ParticipationRegimeAnalyzer().analyze(vol, breadth)
        assert result.compressed is True
        assert result.quality == "low"

    def test_expanding_market(self) -> None:
        vol = make_volume(
            bias=VolumeBias.BULLISH,
            rvol=2.0,
            confidence=0.6,
        )
        breadth = make_breadth(
            bias=BreadthBias.BULLISH,
            confidence=0.6,
        )
        result = ParticipationRegimeAnalyzer().analyze(vol, breadth)
        assert result.expanding is True
        assert result.quality == "strong"

    def test_moderate_quality(self) -> None:
        vol = make_volume(bias=VolumeBias.BULLISH, confidence=0.6)
        breadth = make_breadth(confidence=0.6)
        result = ParticipationRegimeAnalyzer().analyze(vol, breadth)
        assert result.quality == "moderate"

    def test_neutral_quality(self) -> None:
        vol = make_volume(confidence=0.6)
        breadth = make_breadth(confidence=0.6)
        result = ParticipationRegimeAnalyzer().analyze(vol, breadth)
        assert result.quality == "neutral"

    def test_reasons_included(self) -> None:
        vol = make_volume(bias=VolumeBias.BULLISH, confidence=0.6)
        breadth = make_breadth(confidence=0.6)
        result = ParticipationRegimeAnalyzer().analyze(vol, breadth)
        assert len(result.reasons) > 0


# ---------------------------------------------------------------------------
# StrategySuitabilityAnalyzer unit tests
# ---------------------------------------------------------------------------


class TestStrategySuitabilityAnalyzer:
    def test_none_inputs(self) -> None:
        result = StrategySuitabilityAnalyzer().analyze(
            None, None, MarketRegime.UNKNOWN, None
        )
        assert result.confidence == 0.0
        assert "Insufficient intelligence" in result.reasons[0]

    def test_trend_following_regime(self) -> None:
        trend = TrendRegime(
            direction=TrendDirection.BULLISH,
            strength=0.7,
            confidence=0.8,
        )
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            confidence=0.8,
        )
        result = StrategySuitabilityAnalyzer().analyze(
            trend, None, MarketRegime.TRENDING_BULLISH, ms
        )
        assert result.preferred is StrategyType.TREND_FOLLOWING
        assert result.avoid_mean_reversion is True

    def test_breakout_regime(self) -> None:
        trend = TrendRegime(direction=TrendDirection.BULLISH, confidence=0.8)
        ms = make_ms(confidence=0.8)
        result = StrategySuitabilityAnalyzer().analyze(
            trend, None, MarketRegime.BREAKOUT, ms
        )
        assert result.preferred is StrategyType.BREAKOUT

    def test_range_trading_regime(self) -> None:
        trend = TrendRegime(direction=TrendDirection.SIDEWAYS, confidence=0.8)
        ms = make_ms(
            primary_trend=TrendDirection.SIDEWAYS,
            structure_state=StructureState.RANGING,
            confidence=0.8,
        )
        result = StrategySuitabilityAnalyzer().analyze(
            trend, None, MarketRegime.RANGING, ms
        )
        assert result.preferred is StrategyType.RANGE_TRADING
        assert result.avoid_breakouts is True

    def test_no_trade_mixed(self) -> None:
        trend = TrendRegime(confidence=0.8)
        ms = make_ms(confidence=0.8)
        result = StrategySuitabilityAnalyzer().analyze(
            trend, None, MarketRegime.MIXED, ms
        )
        assert result.preferred is StrategyType.NO_TRADE

    def test_volatility_contraction(self) -> None:
        trend = TrendRegime(confidence=0.8)
        ms = make_ms(confidence=0.8)
        result = StrategySuitabilityAnalyzer().analyze(
            trend, None, MarketRegime.COMPRESSION, ms
        )
        assert result.preferred is StrategyType.VOLATILITY_CONTRACTION

    def test_mean_reversion_override(self) -> None:
        trend = TrendRegime(
            direction=TrendDirection.BULLISH,
            strength=0.7,
            mean_reversion_environment=True,
            confidence=0.8,
        )
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            confidence=0.8,
        )
        result = StrategySuitabilityAnalyzer().analyze(
            trend, None, MarketRegime.TRENDING_BULLISH, ms
        )
        assert result.preferred is StrategyType.MEAN_REVERSION


# ---------------------------------------------------------------------------
# MarketRegimeAnalyzer orchestrator tests
# ---------------------------------------------------------------------------


class TestMarketRegimeAnalyzer:
    def test_no_inputs(self) -> None:
        result = MarketRegimeAnalyzer().analyze()
        assert result.confidence == 0.0
        assert "No intelligence inputs" in result.warnings[0]

    def test_bullish_trending_regime(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.8,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        vol = make_volume(bias=VolumeBias.BULLISH, rvol=1.2, confidence=0.6)
        breadth = make_breadth(
            bias=BreadthBias.BULLISH,
            strength=BreadthStrength.STRONG,
            confidence=0.6,
        )
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms,
            vwap=vwap,
            volume=vol,
            breadth=breadth,
        )
        assert result.market_regime is MarketRegime.TRENDING_BULLISH
        assert result.institutional_confirmation is True
        assert result.preferred_strategy is StrategyType.TREND_FOLLOWING

    def test_bearish_trending_regime(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BEARISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.7,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BEARISH, confidence=0.7)
        vol = make_volume(bias=VolumeBias.BEARISH, rvol=1.2, confidence=0.6)
        breadth = make_breadth(
            bias=BreadthBias.BEARISH,
            strength=BreadthStrength.WEAK,
            confidence=0.6,
        )
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms,
            vwap=vwap,
            volume=vol,
            breadth=breadth,
        )
        assert result.market_regime is MarketRegime.TRENDING_BEARISH

    def test_ranging_regime(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.SIDEWAYS,
            structure_state=StructureState.RANGING,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.NEUTRAL, confidence=0.7)
        vol = make_volume(rvol=0.8, confidence=0.6)
        breadth = make_breadth(bias=BreadthBias.NEUTRAL, confidence=0.6)
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms,
            vwap=vwap,
            volume=vol,
            breadth=breadth,
        )
        assert result.market_regime is MarketRegime.RANGING
        assert result.market_health == "neutral"

    def test_compression_regime(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.SIDEWAYS,
            structure_state=StructureState.RANGING,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.NEUTRAL, confidence=0.7)
        vol = make_volume(rvol=0.5, confidence=0.6)
        breadth = make_breadth(bias=BreadthBias.NEUTRAL, confidence=0.6)
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms,
            vwap=vwap,
            volume=vol,
            breadth=breadth,
        )
        assert result.market_regime is MarketRegime.COMPRESSION

    def test_breakout_regime(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.7,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        vol = make_volume(bias=VolumeBias.BULLISH, rvol=2.0, confidence=0.6)
        breadth = make_breadth(bias=BreadthBias.BULLISH, confidence=0.6)
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms,
            vwap=vwap,
            volume=vol,
            breadth=breadth,
        )
        assert result.market_regime is MarketRegime.BREAKOUT

    def test_transition_regime(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.SIDEWAYS,
            structure_state=StructureState.TRANSITION,
            confidence=0.8,
        )
        vwap = make_vwap(confidence=0.7)
        vol = make_volume(confidence=0.6)
        breadth = make_breadth(confidence=0.6)
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms,
            vwap=vwap,
            volume=vol,
            breadth=breadth,
        )
        assert result.market_regime is MarketRegime.TRANSITION

    def test_decision_context_bullish(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.8,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms,
            vwap=vwap,
        )
        assert result.decision_context is not None
        assert result.decision_context.favorable_for_long is True
        assert result.decision_context.favorable_for_short is False

    def test_decision_context_bearish(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BEARISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.7,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BEARISH, confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms,
            vwap=vwap,
        )
        assert result.decision_context is not None
        assert result.decision_context.favorable_for_short is True
        assert result.decision_context.favorable_for_long is False

    def test_decision_context_option_buying(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.8,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        vol = make_volume(bias=VolumeBias.BULLISH, rvol=2.0, confidence=0.6)
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms, vwap=vwap, volume=vol
        )
        assert result.decision_context is not None
        assert result.decision_context.favorable_for_option_buying is True

    def test_decision_context_option_selling(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.SIDEWAYS,
            structure_state=StructureState.RANGING,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.NEUTRAL, confidence=0.7)
        vol = make_volume(rvol=0.5, confidence=0.6)
        breadth = make_breadth(bias=BreadthBias.NEUTRAL, confidence=0.6)
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms,
            vwap=vwap,
            volume=vol,
            breadth=breadth,
        )
        assert result.decision_context is not None
        assert result.decision_context.favorable_for_option_selling is True

    def test_evidence_generated(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.7,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        assert result.evidence is not None
        assert result.evidence.category is EvidenceCategory.MARKET_REGIME
        assert result.evidence.source == "Market Regime"

    def test_evidence_signal_bullish(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.7,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        assert result.evidence is not None
        assert result.evidence.signal is EvidenceSignal.BULLISH

    def test_evidence_signal_bearish(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BEARISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.7,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BEARISH, confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        assert result.evidence is not None
        assert result.evidence.signal is EvidenceSignal.BEARISH

    def test_evidence_score(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.7,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        assert result.evidence is not None
        assert result.evidence.score.value >= 50.0

    def test_explanation_generated(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            confidence=0.8,
        )
        vwap = make_vwap(confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        assert result.explanation is not None
        assert isinstance(result.explanation, MarketRegimeExplanation)

    def test_explanation_sections(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            confidence=0.8,
        )
        vwap = make_vwap(confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        exp = result.explanation
        assert exp.overall_regime != ""
        assert exp.trend_assessment != ""
        assert exp.risk_assessment != ""

    def test_warnings_low_confidence(self) -> None:
        ms = make_ms(confidence=0.1)
        vwap = make_vwap(confidence=0.1)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        assert any("Low" in w for w in result.warnings)

    def test_metadata_present(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            confidence=0.8,
        )
        vwap = make_vwap(confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        assert "analyzer" in result.metadata

    def test_neutral_placeholder(self) -> None:
        result = MarketRegimeAnalysis.neutral_placeholder()
        assert result.confidence == 0.0
        assert "Market regime data unavailable." in result.warnings

    def test_empty_analysis(self) -> None:
        result = MarketRegimeAnalyzer().analyze()
        assert result.confidence == 0.0

    def subresults_present(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            confidence=0.8,
        )
        vwap = make_vwap(confidence=0.7)
        vol = make_volume(confidence=0.6)
        breadth = make_breadth(confidence=0.6)
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms,
            vwap=vwap,
            volume=vol,
            breadth=breadth,
        )
        assert result.trend is not None
        assert isinstance(result.trend, TrendRegime)
        assert result.participation is not None
        assert isinstance(result.participation, ParticipationRegime)
        assert result.strategy is not None
        assert isinstance(result.strategy, StrategySuitability)

    def test_mixed_regime(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.UNKNOWN,
            structure_state=StructureState.UNKNOWN,
            confidence=0.1,
        )
        vwap = make_vwap(bias=VWAPBias.UNKNOWN, confidence=0.1)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        assert result.market_regime is MarketRegime.UNKNOWN

    def test_market_health_healthy(self) -> None:
        vol = make_volume(bias=VolumeBias.BULLISH, rvol=2.0, confidence=0.6)
        breadth = make_breadth(bias=BreadthBias.BULLISH, confidence=0.6)
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms,
            vwap=vwap,
            volume=vol,
            breadth=breadth,
        )
        assert result.market_health == "healthy"

    def test_market_health_divergent(self) -> None:
        vol = make_volume(rvol=0.8, confidence=0.6)
        breadth = make_breadth(
            bias=BreadthBias.NEUTRAL,
            divergence=True,
            confidence=0.6,
        )
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(
            market_structure=ms,
            vwap=vwap,
            volume=vol,
            breadth=breadth,
        )
        assert result.market_health == "divergent"


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestValidation:
    def test_market_regime_analysis_frozen(self) -> None:
        r = MarketRegimeAnalysis.neutral_placeholder()
        with pytest.raises(AttributeError):
            r.market_regime = MarketRegime.BREAKOUT

    def test_trend_regime_frozen(self) -> None:
        t = TrendRegime()
        with pytest.raises(AttributeError):
            t.direction = TrendDirection.BULLISH

    def test_decision_context_frozen(self) -> None:
        d = DecisionContext()
        with pytest.raises(AttributeError):
            d.overall_score = 80.0

    def test_participation_regime_frozen(self) -> None:
        p = ParticipationRegime()
        with pytest.raises(AttributeError):
            p.quality = "strong"

    def test_strategy_suitability_frozen(self) -> None:
        s = StrategySuitability()
        with pytest.raises(AttributeError):
            s.preferred = StrategyType.BREAKOUT


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_volume_only_input(self) -> None:
        vol = make_volume(confidence=0.6)
        result = MarketRegimeAnalyzer().analyze(volume=vol)
        assert result.confidence > 0.0

    def test_breadth_only_input(self) -> None:
        breadth = make_breadth(confidence=0.6)
        result = MarketRegimeAnalyzer().analyze(breadth=breadth)
        assert result.confidence > 0.0

    def test_market_health_neutral(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        assert result.market_health == "neutral"

    def test_decision_context_overall_score(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.8,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        assert result.decision_context is not None
        assert 0.0 <= result.decision_context.overall_score <= 100.0

    def test_confidence_bounds(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        assert 0.0 <= result.confidence <= 1.0

    def test_institutional_interpretation_in_explanation(self) -> None:
        ms = make_ms(
            primary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            confidence=0.8,
        )
        vwap = make_vwap(bias=VWAPBias.BULLISH, confidence=0.7)
        result = MarketRegimeAnalyzer().analyze(market_structure=ms, vwap=vwap)
        assert result.explanation is not None
        assert result.explanation.overall_regime != ""
