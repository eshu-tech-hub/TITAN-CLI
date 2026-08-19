import json

import pytest

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.events.models import (
    DecisionContext as EventDecisionContext,
)
from titan.events.models import (
    EventAnalysis,
    EventRisk,
    MarketReaction,
    MarketReactionResult,
    NewsAnalysis,
    NewsDecisionContext,
    NewsSentiment,
    SentimentResult,
)
from titan.intelligence.fusion.models import (
    ConflictType,
    EvidenceConflict,
    IntelligenceFusion,
)
from titan.market.intelligence.models import (
    DecisionContext as MarketDecisionContext,
)
from titan.market.intelligence.models import (
    MarketRegime,
    MarketRegimeAnalysis,
    StrategyType,
)
from titan.options.analytics.models import (
    CharmExposureAnalysis,
    CharmPressure,
    CharmPressureLevel,
    CharmRegime,
    CharmRegimeType,
    DealerBiasLevel,
    DealerPositioningAnalysis,
    DealerSide,
    ExecutionGrade,
    GammaExposureAnalysis,
    GammaRegime,
    GreeksAnalysis,
    LiquidityAnalysis,
    MarketBias,
    OptionChainAnalysis,
    PinningProbability,
    VannaExposureAnalysis,
    VannaPressure,
    VannaPressureLevel,
    VannaRegime,
    VannaRegimeType,
    VolatilityAnalysis,
    ZeroGammaLevel,
)
from titan.trading.models import (
    ScoreBand,
    TradeQualification,
    TradeQualificationExplanation,
    TradeQualificationInput,
    TradeStatus,
)
from titan.trading.qualification import TradeQualificationEngine

# ===========================================================================
# Helpers — factory functions for test intelligence outputs
# ===========================================================================


def make_market_regime(
    regime: MarketRegime = MarketRegime.TRENDING_BULLISH,
    confidence: float = 0.8,
    favorable_long: bool = True,
    favorable_short: bool = False,
    favorable_option_buying: bool = True,
    favorable_option_selling: bool = False,
    institutional_confirmation: bool = True,
) -> MarketRegimeAnalysis:
    return MarketRegimeAnalysis(
        market_regime=regime,
        confidence=confidence,
        institutional_confirmation=institutional_confirmation,
        decision_context=MarketDecisionContext(
            favorable_for_long=favorable_long,
            favorable_for_short=favorable_short,
            favorable_for_option_buying=favorable_option_buying,
            favorable_for_option_selling=favorable_option_selling,
            preferred_strategy=StrategyType.TREND_FOLLOWING,
            confidence=confidence,
        ),
    )


def make_option_chain(
    bias: MarketBias = MarketBias.BULLISH,
    confidence: float = 0.7,
    bullish_score: float = 60.0,
    bearish_score: float = 20.0,
) -> OptionChainAnalysis:
    return OptionChainAnalysis(
        overall_bias=bias,
        confidence=confidence,
        support=None,
        resistance=None,
        pcr=0.8,
        highest_put_strike=None,
        highest_call_strike=None,
        bullish_score=bullish_score,
        bearish_score=bearish_score,
        neutral_score=20.0,
    )


def make_dealer(
    dealer_side: DealerSide = DealerSide.LONG_GAMMA,
    dealer_bias: DealerBiasLevel = DealerBiasLevel.BULLISH,
    confidence: float = 0.7,
    hedging_pressure: float = 0.4,
) -> DealerPositioningAnalysis:
    return DealerPositioningAnalysis(
        dealer_side=dealer_side,
        dealer_bias=dealer_bias,
        hedging_pressure=hedging_pressure,
        confidence=confidence,
    )


def make_volatility(
    overall_bias: MarketBias = MarketBias.BULLISH,
    confidence: float = 0.7,
    buying_bias: bool = True,
    selling_bias: bool = False,
) -> VolatilityAnalysis:
    from titan.options.analytics.models import (
        HVStability,
        HVTrend,
        IVHVRelation,
        IVLevel,
        IVRankLevel,
        IVTrend,
        VolatilityRegime,
    )

    return VolatilityAnalysis(
        current_iv=18.0,
        current_hv=15.0,
        iv_rank=60.0,
        iv_percentile=65.0,
        iv_vs_hv=IVHVRelation.IV_PREMIUM,
        volatility_regime=VolatilityRegime.STABLE,
        iv_level=IVLevel.NORMAL,
        iv_rank_level=IVRankLevel.NEUTRAL,
        iv_trend=IVTrend.FLAT,
        hv_trend=HVTrend.FLAT,
        hv_stability=HVStability.STABLE,
        buying_bias=buying_bias,
        selling_bias=selling_bias,
        overall_bias=overall_bias,
        confidence=confidence,
    )


def make_liquidity(
    grade: ExecutionGrade = ExecutionGrade.B,
    confidence: float = 0.8,
) -> LiquidityAnalysis:
    return LiquidityAnalysis(
        spread=0.05,
        spread_percent=0.1,
        depth_score=75.0,
        slippage_score=80.0,
        execution_score=78.0,
        execution_grade=grade,
        confidence=confidence,
    )


def make_greeks(
    bias: MarketBias = MarketBias.BULLISH,
    confidence: float = 0.6,
) -> GreeksAnalysis:
    return GreeksAnalysis(
        net_delta=1000.0,
        net_gamma=500.0,
        net_theta=-200.0,
        net_vega=300.0,
        average_delta=0.5,
        average_gamma=0.05,
        average_theta=-0.02,
        average_vega=0.15,
        overall_bias=bias,
        confidence=confidence,
    )


def make_gamma_exposure(
    confidence: float = 0.7,
) -> GammaExposureAnalysis:
    return GammaExposureAnalysis(
        net_gamma_exposure=1.5e6,
        gamma_regime=GammaRegime.POSITIVE,
        zero_gamma_level=ZeroGammaLevel(strike=18500.0, confidence=0.7),
        call_wall=None,
        put_wall=None,
        pinning_probability=PinningProbability.MEDIUM,
        volatility_expansion_probability=0.3,
        confidence=confidence,
    )


def make_vanna_exposure(
    confidence: float = 0.6,
) -> VannaExposureAnalysis:
    return VannaExposureAnalysis(
        net_vanna=50000.0,
        regime=VannaRegime(
            regime_type=VannaRegimeType.POSITIVE,
            net_vanna=50000.0,
            confidence=0.6,
        ),
        pressure=VannaPressure(
            pressure_level=VannaPressureLevel.MEDIUM,
            dealer_response="Moderate vanna pressure.",
            iv_sensitivity=0.5,
            price_sensitivity=0.5,
            confidence=0.6,
        ),
        confidence=confidence,
    )


def make_charm_exposure(
    confidence: float = 0.5,
) -> CharmExposureAnalysis:
    return CharmExposureAnalysis(
        net_charm=-20000.0,
        regime=CharmRegime(
            regime_type=CharmRegimeType.NEGATIVE,
            net_charm=-20000.0,
            confidence=0.5,
        ),
        pressure=CharmPressure(
            pressure_level=CharmPressureLevel.MEDIUM,
            dealer_response="Moderate charm pressure.",
            time_sensitivity=0.4,
            near_expiry_risk=False,
            confidence=0.5,
        ),
        dealer_delta_decay=0.3,
        near_expiry_risk=False,
        confidence=confidence,
    )


def make_event_analysis(
    risk: EventRisk = EventRisk.LOW,
    confidence: float = 0.7,
    avoid_new_positions: bool = False,
) -> EventAnalysis:
    return EventAnalysis(
        overall_risk=risk,
        confidence=confidence,
        decision_context=EventDecisionContext(
            avoid_new_positions=avoid_new_positions,
            confidence=confidence,
        ),
    )


def make_news_analysis(
    reaction: str = "likely_bullish",
    confidence: float = 0.6,
) -> NewsAnalysis:
    reaction_map = {
        "likely_bullish": MarketReaction.LIKELY_BULLISH,
        "likely_bearish": MarketReaction.LIKELY_BEARISH,
        "likely_neutral": MarketReaction.LIKELY_NEUTRAL,
        "mixed": MarketReaction.MIXED,
    }
    return NewsAnalysis(
        overall_sentiment=SentimentResult(
            sentiment=NewsSentiment.POSITIVE,
            score=0.6,
            confidence=confidence,
        ),
        overall_reaction=MarketReactionResult(
            reaction=reaction_map.get(reaction, MarketReaction.UNKNOWN),
            confidence=confidence,
        ),
        decision_context=NewsDecisionContext(
            high_news_uncertainty=False,
            conflicting_news=False,
            institutional_alignment=True,
            confidence=confidence,
        ),
        confidence=confidence,
    )


def make_fusion(
    score: float = 72.0,
    confidence: float = 0.7,
    signal: EvidenceSignal = EvidenceSignal.BULLISH,
    conflicts: tuple[EvidenceConflict, ...] = (),
) -> IntelligenceFusion:
    return IntelligenceFusion(
        overall_score=Score(score),
        overall_confidence=Confidence(confidence),
        overall_signal=signal,
        conflicting_evidence=conflicts,
        evidence_count=10,
    )


def make_qualified_input(
    with_fusion: bool = True,
    with_event: bool = True,
    with_news: bool = True,
    with_greeks: bool = True,
    with_gamma: bool = True,
    with_vanna: bool = True,
    with_charm: bool = True,
) -> TradeQualificationInput:
    reg = make_market_regime()
    chain = make_option_chain()
    dealer = make_dealer()
    vol = make_volatility()
    liq = make_liquidity()
    evt = make_event_analysis() if with_event else None
    news = make_news_analysis() if with_news else None
    greeks = make_greeks() if with_greeks else None
    gex = make_gamma_exposure() if with_gamma else None
    vanna = make_vanna_exposure() if with_vanna else None
    charm = make_charm_exposure() if with_charm else None

    fusion = None
    if with_fusion:
        fusion_evidences = []
        if reg.evidence:
            fusion_evidences.append(reg.evidence)

        fusion = make_fusion()

    return TradeQualificationInput(
        market_regime=reg,
        option_chain=chain,
        greeks=greeks,
        liquidity=liq,
        volatility=vol,
        dealer_positioning=dealer,
        gamma_exposure=gex,
        vanna_exposure=vanna,
        charm_exposure=charm,
        event_analysis=evt,
        news_analysis=news,
        intelligence_fusion=fusion,
    )


# ===========================================================================
# Tests
# ===========================================================================


class TestTradeQualification:
    """Core test suite for the Trade Qualification Engine."""

    def test_qualified_trade(self) -> None:
        """A fully qualified trade with all positive signals."""
        engine = TradeQualificationEngine()
        inputs = make_qualified_input()
        result = engine.qualify(inputs)

        assert result.status == TradeStatus.QUALIFIED
        assert result.trade_score.value >= 60.0
        assert result.trade_score.band in (ScoreBand.EXCELLENT, ScoreBand.GOOD)
        assert result.long_qualification is True
        assert result.institutional_alignment is True
        assert len(result.failed_filters) == 0

    def test_rejected_trade_high_event_risk(self) -> None:
        """A trade is rejected when event risk is extreme."""
        engine = TradeQualificationEngine()
        event = make_event_analysis(
            risk=EventRisk.EXTREME,
            avoid_new_positions=True,
        )
        inputs = make_qualified_input()
        inputs = TradeQualificationInput(
            market_regime=inputs.market_regime,
            option_chain=inputs.option_chain,
            greeks=inputs.greeks,
            liquidity=inputs.liquidity,
            volatility=inputs.volatility,
            dealer_positioning=inputs.dealer_positioning,
            gamma_exposure=inputs.gamma_exposure,
            vanna_exposure=inputs.vanna_exposure,
            charm_exposure=inputs.charm_exposure,
            event_analysis=event,
            news_analysis=inputs.news_analysis,
            intelligence_fusion=inputs.intelligence_fusion,
        )
        result = engine.qualify(inputs)

        assert result.status == TradeStatus.REJECTED
        assert result.trade_score.band == ScoreBand.REJECT
        assert len(result.failed_filters) > 0
        assert any("event" in f.lower() for f in result.failed_filters)

    def test_rejected_trade_low_confidence(self) -> None:
        """A trade is rejected when overall confidence is too low."""
        engine = TradeQualificationEngine()
        low_conf_regime = make_market_regime(confidence=0.05)
        low_conf_chain = make_option_chain(confidence=0.05)
        low_conf_dealer = make_dealer(confidence=0.05)
        low_conf_vol = make_volatility(confidence=0.05)

        inputs = TradeQualificationInput(
            market_regime=low_conf_regime,
            option_chain=low_conf_chain,
            greeks=None,
            liquidity=None,
            volatility=low_conf_vol,
            dealer_positioning=low_conf_dealer,
            gamma_exposure=None,
            vanna_exposure=None,
            charm_exposure=None,
            event_analysis=None,
            news_analysis=None,
            intelligence_fusion=None,
        )
        result = engine.qualify(inputs)

        assert result.status == TradeStatus.REJECTED
        assert len(result.failed_filters) > 0

    def test_rejected_trade_conflicting_intelligence(self) -> None:
        """A trade is rejected when fusion detects conflicts."""
        engine = TradeQualificationEngine()
        conflict = EvidenceConflict(
            conflict_type=ConflictType.BULLISH_VS_BEARISH,
            reason="Market regime bullish but dealer bearish.",
            evidence_items=(
                Evidence(
                    source="Market",
                    category=EvidenceCategory.MARKET_REGIME,
                    signal=EvidenceSignal.BULLISH,
                    score=Score(70.0),
                    confidence=Confidence(0.7),
                ),
                Evidence(
                    source="Dealer",
                    category=EvidenceCategory.SYSTEM,
                    signal=EvidenceSignal.BEARISH,
                    score=Score(30.0),
                    confidence=Confidence(0.6),
                ),
            ),
        )
        fusion = make_fusion(signal=EvidenceSignal.NEUTRAL, conflicts=(conflict,))
        inputs = make_qualified_input()
        inputs = TradeQualificationInput(
            market_regime=inputs.market_regime,
            option_chain=inputs.option_chain,
            greeks=inputs.greeks,
            liquidity=inputs.liquidity,
            volatility=inputs.volatility,
            dealer_positioning=inputs.dealer_positioning,
            gamma_exposure=inputs.gamma_exposure,
            vanna_exposure=inputs.vanna_exposure,
            charm_exposure=inputs.charm_exposure,
            event_analysis=inputs.event_analysis,
            news_analysis=inputs.news_analysis,
            intelligence_fusion=fusion,
        )
        result = engine.qualify(inputs)

        assert result.status == TradeStatus.REJECTED

    def test_watchlist_insufficient_confirmations(self) -> None:
        """A trade with partial confirmations is placed on watchlist."""
        engine = TradeQualificationEngine()
        weak_regime = make_market_regime(
            regime=MarketRegime.RANGING,
            confidence=0.4,
            favorable_long=False,
            favorable_short=False,
            institutional_confirmation=False,
        )
        weak_chain = make_option_chain(
            bias=MarketBias.NEUTRAL,
            confidence=0.3,
        )
        weak_dealer = make_dealer(
            dealer_side=DealerSide.NEUTRAL,
            dealer_bias=DealerBiasLevel.NEUTRAL,
            confidence=0.3,
        )

        inputs = TradeQualificationInput(
            market_regime=weak_regime,
            option_chain=weak_chain,
            greeks=None,
            liquidity=make_liquidity(),
            volatility=None,
            dealer_positioning=weak_dealer,
            gamma_exposure=None,
            vanna_exposure=None,
            charm_exposure=None,
            event_analysis=None,
            news_analysis=None,
            intelligence_fusion=None,
        )
        result = engine.qualify(inputs)

        assert result.status in (TradeStatus.WATCHLIST, TradeStatus.WAIT)

    def test_wait_low_score(self) -> None:
        """A trade with very low score is placed in wait status."""
        engine = TradeQualificationEngine()
        regime = make_market_regime(
            regime=MarketRegime.MIXED,
            confidence=0.3,
            favorable_long=False,
            favorable_short=False,
            institutional_confirmation=False,
        )
        chain = make_option_chain(
            bias=MarketBias.NEUTRAL,
            confidence=0.2,
        )
        dealer = make_dealer(
            dealer_side=DealerSide.NEUTRAL,
            dealer_bias=DealerBiasLevel.NEUTRAL,
            confidence=0.2,
        )

        inputs = TradeQualificationInput(
            market_regime=regime,
            option_chain=chain,
            dealer_positioning=dealer,
            greeks=None,
            liquidity=None,
            volatility=None,
            gamma_exposure=None,
            vanna_exposure=None,
            charm_exposure=None,
            event_analysis=None,
            news_analysis=None,
            intelligence_fusion=None,
        )
        result = engine.qualify(inputs)

        assert result.status == TradeStatus.WAIT

    def test_rejected_extreme_liquidity_risk(self) -> None:
        """A trade is rejected when liquidity risk is extreme."""
        engine = TradeQualificationEngine()
        bad_liq = make_liquidity(grade=ExecutionGrade.F)
        inputs = make_qualified_input()
        inputs = TradeQualificationInput(
            market_regime=inputs.market_regime,
            option_chain=inputs.option_chain,
            greeks=inputs.greeks,
            liquidity=bad_liq,
            volatility=inputs.volatility,
            dealer_positioning=inputs.dealer_positioning,
            gamma_exposure=inputs.gamma_exposure,
            vanna_exposure=inputs.vanna_exposure,
            charm_exposure=inputs.charm_exposure,
            event_analysis=inputs.event_analysis,
            news_analysis=inputs.news_analysis,
            intelligence_fusion=inputs.intelligence_fusion,
        )
        result = engine.qualify(inputs)

        assert result.status == TradeStatus.REJECTED
        assert any("liquidity" in f.lower() for f in result.failed_filters)

    def test_rejected_unknown_market_regime(self) -> None:
        """A trade is rejected when market regime is unknown."""
        engine = TradeQualificationEngine()
        unknown_regime = make_market_regime(
            regime=MarketRegime.UNKNOWN,
            confidence=0.0,
        )
        inputs = make_qualified_input()
        inputs = TradeQualificationInput(
            market_regime=unknown_regime,
            option_chain=inputs.option_chain,
            greeks=inputs.greeks,
            liquidity=inputs.liquidity,
            volatility=inputs.volatility,
            dealer_positioning=inputs.dealer_positioning,
            gamma_exposure=inputs.gamma_exposure,
            vanna_exposure=inputs.vanna_exposure,
            charm_exposure=inputs.charm_exposure,
            event_analysis=inputs.event_analysis,
            news_analysis=inputs.news_analysis,
            intelligence_fusion=inputs.intelligence_fusion,
        )
        result = engine.qualify(inputs)

        assert result.status == TradeStatus.REJECTED

    def test_missing_intelligence_degradation(self) -> None:
        """Engine degrades gracefully with minimal intelligence."""
        engine = TradeQualificationEngine()
        inputs = TradeQualificationInput(
            market_regime=make_market_regime(
                institutional_confirmation=False,
                favorable_long=True,
            ),
            option_chain=make_option_chain(),
            dealer_positioning=make_dealer(),
        )
        result = engine.qualify(inputs)

        assert isinstance(result, TradeQualification)
        assert result.status in (
            TradeStatus.WATCHLIST,
            TradeStatus.QUALIFIED,
            TradeStatus.WAIT,
        )

    def test_evidence_generation(self) -> None:
        """Qualified trade generates proper evidence."""
        engine = TradeQualificationEngine()
        inputs = make_qualified_input()
        result = engine.qualify(inputs)

        assert result.evidence is not None
        assert result.evidence.source == "TradeQualificationEngine"
        assert result.evidence.category == EvidenceCategory.TRADE_QUALIFICATION
        assert result.evidence.score.value > 0
        assert len(result.evidence.reasons) > 0

    def test_explanation_generation(self) -> None:
        """Qualified trade generates proper explanation."""
        engine = TradeQualificationEngine()
        inputs = make_qualified_input()
        result = engine.qualify(inputs)

        assert result.explanation is not None
        assert isinstance(result.explanation, TradeQualificationExplanation)
        assert result.explanation.overall_qualification
        assert result.explanation.confirmations
        assert result.explanation.final_assessment

    def test_validation_input_type(self) -> None:
        """Engine validates input type."""
        engine = TradeQualificationEngine()
        from titan.trading.exceptions import TradeQualificationInputError

        with pytest.raises(TradeQualificationInputError):
            engine.qualify(None)  # type: ignore[arg-type]

    def test_serialization(self) -> None:
        """TradeQualification models are serializable via dataclass."""
        engine = TradeQualificationEngine()
        inputs = make_qualified_input()
        result = engine.qualify(inputs)

        data = {
            "status": result.status.value,
            "score": result.trade_score.value,
            "band": result.trade_score.band.value,
            "confidence": result.confidence,
            "long_qualification": result.long_qualification,
            "short_qualification": result.short_qualification,
            "institutional_alignment": result.institutional_alignment,
        }
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)

        assert deserialized["status"] == TradeStatus.QUALIFIED.value
        assert deserialized["score"] >= 60.0
        assert deserialized["long_qualification"] is True

    def test_direction_qualifications(self) -> None:
        """Engine evaluates all four trade directions."""
        engine = TradeQualificationEngine()
        inputs = make_qualified_input()
        result = engine.qualify(inputs)

        assert isinstance(result.long_qualification, bool)
        assert isinstance(result.short_qualification, bool)
        assert isinstance(result.option_buying_qualification, bool)
        assert isinstance(result.option_selling_qualification, bool)

    def test_warnings_collected(self) -> None:
        """Warnings from all input modules are collected."""
        engine = TradeQualificationEngine()
        inputs = make_qualified_input()
        result = engine.qualify(inputs)

        assert isinstance(result.warnings, tuple)

    def test_filter_results_in_output(self) -> None:
        """Passed and failed filters are exposed in output."""
        engine = TradeQualificationEngine()

        # Qualified case
        inputs = make_qualified_input()
        result = engine.qualify(inputs)
        assert len(result.passed_filters) > 0
        assert len(result.failed_filters) == 0

        # Rejected case
        bad_event = make_event_analysis(
            risk=EventRisk.EXTREME, avoid_new_positions=True
        )
        bad_inputs = make_qualified_input()
        bad_inputs = TradeQualificationInput(
            market_regime=bad_inputs.market_regime,
            option_chain=bad_inputs.option_chain,
            greeks=bad_inputs.greeks,
            liquidity=bad_inputs.liquidity,
            volatility=bad_inputs.volatility,
            dealer_positioning=bad_inputs.dealer_positioning,
            gamma_exposure=bad_inputs.gamma_exposure,
            vanna_exposure=bad_inputs.vanna_exposure,
            charm_exposure=bad_inputs.charm_exposure,
            event_analysis=bad_event,
            news_analysis=bad_inputs.news_analysis,
            intelligence_fusion=bad_inputs.intelligence_fusion,
        )
        rejected = engine.qualify(bad_inputs)
        assert len(rejected.failed_filters) > 0

    def test_metadata_in_output(self) -> None:
        """Metadata is present in output."""
        engine = TradeQualificationEngine()
        inputs = make_qualified_input()
        result = engine.qualify(inputs)

        assert "engine" in result.metadata
        assert result.metadata["engine"] == "TradeQualificationEngine"
        assert "inputs" in result.metadata

    def test_unknown_market_regime_filter(self) -> None:
        """Hard filter catches unknown market regime."""
        engine = TradeQualificationEngine()
        unknown = make_market_regime(
            regime=MarketRegime.UNKNOWN,
            confidence=0.0,
        )
        inputs = TradeQualificationInput(
            market_regime=unknown,
            option_chain=make_option_chain(),
            intelligence_fusion=make_fusion(),
        )
        result = engine.qualify(inputs)

        assert result.status == TradeStatus.REJECTED
        assert any("regime" in f.lower() for f in result.failed_filters)

    def test_insufficient_evidence_filter(self) -> None:
        """Hard filter catches insufficient evidence."""
        engine = TradeQualificationEngine()
        inputs = TradeQualificationInput()
        result = engine.qualify(inputs)

        assert result.status == TradeStatus.REJECTED

    def test_short_qualification(self) -> None:
        """Engine qualifies short positions when signals align."""
        engine = TradeQualificationEngine()
        bearish_regime = make_market_regime(
            regime=MarketRegime.TRENDING_BEARISH,
            confidence=0.8,
            favorable_long=False,
            favorable_short=True,
        )
        bearish_chain = make_option_chain(
            bias=MarketBias.BEARISH,
            bullish_score=20.0,
            bearish_score=60.0,
        )
        bearish_dealer = make_dealer(
            dealer_side=DealerSide.SHORT_GAMMA,
            dealer_bias=DealerBiasLevel.BEARISH,
        )
        bearish_vol = make_volatility(
            overall_bias=MarketBias.BEARISH,
            buying_bias=False,
            selling_bias=True,
        )

        inputs = TradeQualificationInput(
            market_regime=bearish_regime,
            option_chain=bearish_chain,
            dealer_positioning=bearish_dealer,
            volatility=bearish_vol,
            liquidity=make_liquidity(),
            event_analysis=make_event_analysis(),
            news_analysis=make_news_analysis(reaction="likely_bearish"),
            intelligence_fusion=make_fusion(
                signal=EvidenceSignal.BEARISH,
                score=65.0,
            ),
        )
        result = engine.qualify(inputs)

        assert result.status in (TradeStatus.QUALIFIED, TradeStatus.WATCHLIST)
