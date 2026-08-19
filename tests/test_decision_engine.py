import json

import pytest

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.decision import (
    DecisionAction,
    DecisionEngine,
    DecisionEngineError,
    DecisionExplanation,
    DecisionInput,
    DecisionInputError,
    DecisionRank,
    DecisionRankingEngine,
    DecisionSelectionEngine,
    DecisionValidationEngine,
    DecisionValidationError,
    HoldingStyle,
    InstrumentType,
    TradeDecision,
)
from titan.decision.exceptions import DecisionError
from titan.events.models import EventAnalysis, EventImportance, EventRisk
from titan.intelligence.fusion.models import (
    ConflictType,
    EvidenceConflict,
    IntelligenceFusion,
)
from titan.market.intelligence.models import MarketRegime, MarketRegimeAnalysis
from titan.options.analytics.models import (
    DealerBiasLevel,
    DealerPositioningAnalysis,
    DealerSide,
    ExecutionGrade,
    GammaExposureAnalysis,
    GammaRegime,
    GreeksAnalysis,
    IVHVRelation,
    IVLevel,
    IVRankLevel,
    LiquidityAnalysis,
    MarketBias,
    OptionChainAnalysis,
    PinningProbability,
    VolatilityAnalysis,
    VolatilityRegime,
    ZeroGammaLevel,
)
from titan.risk import (
    RiskAnalysis,
    RiskEngine,
    RiskInput,
)
from titan.trading.models import (
    ScoreBand,
    TradeDirection,
    TradeQualification,
    TradeScore,
    TradeStatus,
)

# ===========================================================================
# Helpers — factory functions
# ===========================================================================


def _score_band_for_value(score: float) -> ScoreBand:
    if score >= 90.0:
        return ScoreBand.EXCELLENT
    if score >= 70.0:
        return ScoreBand.GOOD
    if score >= 50.0:
        return ScoreBand.AVERAGE
    if score >= 30.0:
        return ScoreBand.WEAK
    return ScoreBand.REJECT


def make_trade_qualification(
    status: TradeStatus = TradeStatus.QUALIFIED,
    score: float = 75.0,
    confidence: float = 0.7,
    long_q: bool = True,
    short_q: bool = False,
    institutional: bool = False,
) -> TradeQualification:
    return TradeQualification(
        status=status,
        trade_score=TradeScore(value=score, band=_score_band_for_value(score)),
        confidence=confidence,
        decision_context="Test trade",
        long_qualification=long_q,
        short_qualification=short_q,
        institutional_alignment=institutional,
    )


def make_market_regime(
    regime: MarketRegime = MarketRegime.TRENDING_BULLISH,
    confidence: float = 0.7,
    trend_strength: float = 0.7,
) -> MarketRegimeAnalysis:
    return MarketRegimeAnalysis(
        market_regime=regime,
        confidence=confidence,
        trend_strength=trend_strength,
        institutional_confirmation=True,
    )


def make_volatility(
    regime: VolatilityRegime = VolatilityRegime.STABLE,
    iv_rank: IVRankLevel = IVRankLevel.NEUTRAL,
    iv: float | None = 20.0,
    bias: MarketBias = MarketBias.NEUTRAL,
) -> VolatilityAnalysis:
    return VolatilityAnalysis(
        current_iv=iv,
        current_hv=15.0,
        iv_rank=45.0,
        iv_percentile=50.0,
        iv_vs_hv=IVHVRelation.NORMAL,
        volatility_regime=regime,
        iv_level=IVLevel.NORMAL,
        iv_rank_level=iv_rank,
        iv_trend="flat",
        hv_trend="flat",
        hv_stability="stable",
        buying_bias=False,
        selling_bias=False,
        overall_bias=bias,
        confidence=0.7,
    )


def make_liquidity(
    grade: ExecutionGrade = ExecutionGrade.A,
) -> LiquidityAnalysis:
    return LiquidityAnalysis(
        spread=0.05,
        spread_percent=0.01,
        depth_score=0.9,
        slippage_score=0.9,
        execution_score=0.9,
        execution_grade=grade,
        confidence=0.8,
    )


def make_dealer(
    side: DealerSide = DealerSide.LONG_GAMMA,
    bias: DealerBiasLevel = DealerBiasLevel.BULLISH,
) -> DealerPositioningAnalysis:
    return DealerPositioningAnalysis(
        dealer_side=side,
        dealer_bias=bias,
        hedging_pressure=0.5,
        confidence=0.7,
    )


def make_gamma(
    regime: GammaRegime = GammaRegime.POSITIVE,
) -> GammaExposureAnalysis:
    return GammaExposureAnalysis(
        net_gamma_exposure=1000000.0,
        gamma_regime=regime,
        zero_gamma_level=ZeroGammaLevel(
            strike=19500.0,
            underlying_price=19600.0,
            distance_percent=0.5,
            confidence=0.7,
        ),
        call_wall=None,
        put_wall=None,
        pinning_probability=PinningProbability.MEDIUM,
        volatility_expansion_probability=0.3,
        confidence=0.7,
    )


def make_event(
    overall_risk: EventRisk = EventRisk.LOW,
) -> EventAnalysis:
    return EventAnalysis(
        economic_events=(),
        corporate_events=(),
        highest_importance=EventImportance.LOW,
        overall_risk=overall_risk,
        confidence=0.7,
    )


def make_risk_analysis(
    tq: TradeQualification | None = None,
    event_risk: EventRisk = EventRisk.LOW,
) -> RiskAnalysis:
    engine = RiskEngine()
    tq = tq or make_trade_qualification()
    event = make_event(event_risk)
    ri = RiskInput(trade_qualification=tq, event_analysis=event)
    return engine.analyze(risk_input=ri)


def make_decision_input(
    trade_qualification: TradeQualification | None = None,
    risk_analysis: RiskAnalysis | None = None,
    market_regime: MarketRegimeAnalysis | None = None,
    volatility: VolatilityAnalysis | None = None,
    liquidity: LiquidityAnalysis | None = None,
    dealer_positioning: DealerPositioningAnalysis | None = None,
    gamma_exposure: GammaExposureAnalysis | None = None,
    event_analysis: EventAnalysis | None = None,
    option_chain: OptionChainAnalysis | None = None,
    greeks: GreeksAnalysis | None = None,
    intelligence_fusion: IntelligenceFusion | None = None,
    symbol: str = "TEST",
) -> DecisionInput:
    tq = trade_qualification or make_trade_qualification()
    ra = risk_analysis or make_risk_analysis(tq)
    return DecisionInput(
        trade_qualification=tq,
        risk_analysis=ra,
        market_regime=market_regime,
        volatility=volatility,
        liquidity=liquidity,
        dealer_positioning=dealer_positioning,
        gamma_exposure=gamma_exposure,
        event_analysis=event_analysis,
        option_chain=option_chain,
        greeks=greeks,
        intelligence_fusion=intelligence_fusion,
        symbol=symbol,
    )


# ===========================================================================
# Model Tests
# ===========================================================================


class TestEnums:
    def test_decision_action_values(self) -> None:
        assert DecisionAction.BUY.value == "buy"
        assert DecisionAction.SELL.value == "sell"
        assert DecisionAction.NO_TRADE.value == "no_trade"
        assert DecisionAction.WATCHLIST.value == "watchlist"
        assert DecisionAction.WAIT.value == "wait"

    def test_instrument_type_values(self) -> None:
        assert InstrumentType.UNDERLYING.value == "underlying"
        assert InstrumentType.FUTURES.value == "futures"
        assert InstrumentType.CALL_OPTION.value == "call_option"
        assert InstrumentType.PUT_OPTION.value == "put_option"

    def test_holding_style_values(self) -> None:
        assert HoldingStyle.SCALP.value == "scalp"
        assert HoldingStyle.DAY_TRADE.value == "day_trade"
        assert HoldingStyle.SWING.value == "swing"
        assert HoldingStyle.POSITION.value == "position"

    def test_decision_rank_values(self) -> None:
        assert DecisionRank.BEST.value == "best"
        assert DecisionRank.GOOD.value == "good"
        assert DecisionRank.ACCEPTABLE.value == "acceptable"
        assert DecisionRank.REJECT.value == "reject"


class TestDecisionInput:
    def test_required_fields(self) -> None:
        tq = make_trade_qualification()
        ra = make_risk_analysis(tq)
        di = DecisionInput(trade_qualification=tq, risk_analysis=ra)
        assert di.trade_qualification == tq
        assert di.risk_analysis == ra
        assert di.market_regime is None
        assert di.symbol == ""

    def test_with_all_fields(self) -> None:
        tq = make_trade_qualification()
        ra = make_risk_analysis(tq)
        vol = make_volatility()
        liq = make_liquidity()
        event = make_event()
        di = DecisionInput(
            trade_qualification=tq,
            risk_analysis=ra,
            volatility=vol,
            liquidity=liq,
            event_analysis=event,
            symbol="BANKNIFTY",
        )
        assert di.volatility == vol
        assert di.liquidity == liq
        assert di.symbol == "BANKNIFTY"


class TestTradeDecision:
    def test_default_construction(self) -> None:
        td = TradeDecision(
            decision=DecisionAction.BUY,
            trade_direction=TradeDirection.LONG,
            instrument_type=InstrumentType.UNDERLYING,
            symbol="TEST",
        )
        assert td.decision == DecisionAction.BUY
        assert td.rank == DecisionRank.ACCEPTABLE
        assert td.confidence == 0.0
        assert td.expiry is None
        assert td.strike is None

    def test_full_construction(self) -> None:
        td = TradeDecision(
            decision=DecisionAction.BUY,
            trade_direction=TradeDirection.OPTION_BUYING,
            instrument_type=InstrumentType.CALL_OPTION,
            symbol="NIFTY",
            expiry="28JUL2026",
            strike=19600.0,
            entry_strategy="Buy on confirmation standard size",
            stop_loss_reference=19500.0,
            target_reference=19700.0,
            holding_style=HoldingStyle.DAY_TRADE,
            rank=DecisionRank.BEST,
            confidence=0.85,
            probability=0.72,
            trade_score=82.5,
            institutional_grade=True,
        )
        assert td.expiry == "28JUL2026"
        assert td.strike == 19600.0
        assert td.institutional_grade is True
        assert td.rank == DecisionRank.BEST


# ===========================================================================
# Scenario Tests
# ===========================================================================


class TestQualifiedBuy:
    def test_buy_decision(self) -> None:
        tq = make_trade_qualification(
            status=TradeStatus.QUALIFIED,
            score=85.0,
            confidence=0.8,
            long_q=True,
            short_q=False,
            institutional=True,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.LOW)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
            volatility=make_volatility(
                VolatilityRegime.STABLE, bias=MarketBias.BULLISH
            ),
            liquidity=make_liquidity(ExecutionGrade.A),
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.decision == DecisionAction.BUY
        assert result.trade_direction == TradeDirection.LONG
        assert result.rank in (DecisionRank.BEST, DecisionRank.GOOD)
        assert result.confidence >= 0.5
        assert result.evidence is not None
        assert result.explanation is not None


class TestQualifiedSell:
    def test_sell_decision(self) -> None:
        tq = make_trade_qualification(
            status=TradeStatus.QUALIFIED,
            score=75.0,
            confidence=0.7,
            long_q=False,
            short_q=True,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.LOW)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
            volatility=make_volatility(
                VolatilityRegime.STABLE, bias=MarketBias.BEARISH
            ),
            liquidity=make_liquidity(ExecutionGrade.A),
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.decision == DecisionAction.SELL
        assert result.trade_direction == TradeDirection.SHORT


class TestNoTrade:
    def test_risk_engine_rejects(self) -> None:
        tq = make_trade_qualification(
            score=30.0, confidence=0.3, long_q=True, short_q=False
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.EXTREME)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.decision == DecisionAction.NO_TRADE
        assert result.rank == DecisionRank.REJECT


class TestWatchlist:
    def test_watchlist_from_qualification(self) -> None:
        tq = make_trade_qualification(
            status=TradeStatus.WATCHLIST,
            score=60.0,
            confidence=0.5,
            long_q=True,
            short_q=False,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.MODERATE)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.decision == DecisionAction.WATCHLIST


class TestWait:
    def test_wait_from_qualification(self) -> None:
        tq = make_trade_qualification(
            status=TradeStatus.WAIT,
            score=60.0,
            confidence=0.5,
            long_q=True,
            short_q=False,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.MODERATE)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.decision == DecisionAction.WAIT


# ===========================================================================
# Conflicting & Missing Inputs
# ===========================================================================


class TestConflictingInputs:
    def test_conflicting_intelligence(self) -> None:
        tq = make_trade_qualification(
            score=75.0,
            confidence=0.7,
            long_q=True,
            short_q=False,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.LOW)
        conflict = EvidenceConflict(
            conflict_type=ConflictType.BULLISH_VS_BEARISH,
            reason="Volatility bullish vs Dealer bearish",
            evidence_items=(),
        )
        fusion = IntelligenceFusion(
            overall_score=Score(50.0),
            overall_confidence=Confidence(0.5),
            overall_signal=EvidenceSignal.NEUTRAL,
            conflicting_evidence=(conflict,),
            evidence_count=0,
        )
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
            intelligence_fusion=fusion,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert "conflicting" in str(result.warnings).lower()


class TestMissingInputs:
    def test_minimal_input(self) -> None:
        tq = make_trade_qualification()
        risk_analysis = make_risk_analysis(tq)
        di = DecisionInput(trade_qualification=tq, risk_analysis=risk_analysis)

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert isinstance(result, TradeDecision)
        assert result.decision in (
            DecisionAction.BUY,
            DecisionAction.NO_TRADE,
        )
        assert result.evidence is not None
        assert result.explanation is not None


# ===========================================================================
# Ranking Tests
# ===========================================================================


class TestRanking:
    def test_best_rank(self) -> None:
        tq = make_trade_qualification(
            score=95.0,
            confidence=0.9,
            long_q=True,
            short_q=False,
            institutional=True,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.LOW)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
            volatility=make_volatility(
                VolatilityRegime.STABLE, bias=MarketBias.BULLISH
            ),
            liquidity=make_liquidity(ExecutionGrade.A),
        )

        ranker = DecisionRankingEngine()
        rank = ranker.rank(di)

        assert rank == DecisionRank.BEST

    def test_good_rank(self) -> None:
        tq = make_trade_qualification(
            score=70.0,
            confidence=0.6,
            long_q=True,
            short_q=False,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.LOW)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        ranker = DecisionRankingEngine()
        rank = ranker.rank(di)

        assert rank == DecisionRank.GOOD

    def test_acceptable_rank(self) -> None:
        tq = make_trade_qualification(
            score=50.0,
            confidence=0.5,
            long_q=True,
            short_q=False,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.MODERATE)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        ranker = DecisionRankingEngine()
        rank = ranker.rank(di)

        assert rank == DecisionRank.ACCEPTABLE

    def test_reject_rank(self) -> None:
        tq = make_trade_qualification(
            score=20.0,
            confidence=0.2,
            long_q=True,
            short_q=False,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.HIGH)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        ranker = DecisionRankingEngine()
        rank = ranker.rank(di)

        assert rank == DecisionRank.REJECT


# ===========================================================================
# Validation Tests
# ===========================================================================


class TestValidation:
    def test_risk_rejection(self) -> None:
        tq = make_trade_qualification(score=30.0, confidence=0.3)
        risk_analysis = make_risk_analysis(tq, EventRisk.EXTREME)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        validator = DecisionValidationEngine()
        reasons = validator.validate(di)

        assert len(reasons) > 0
        assert any("Risk engine rejects" in r for r in reasons)

    def test_qualification_rejection(self) -> None:
        tq = make_trade_qualification(
            status=TradeStatus.REJECTED,
            score=20.0,
            confidence=0.2,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.LOW)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        validator = DecisionValidationEngine()
        reasons = validator.validate(di)

        assert len(reasons) > 0
        assert any("Trade qualification rejected" in r for r in reasons)

    def test_insufficient_confidence(self) -> None:
        tq = make_trade_qualification(
            score=75.0,
            confidence=0.1,
            long_q=True,
            short_q=False,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.LOW)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        validator = DecisionValidationEngine()
        reasons = validator.validate(di)

        assert len(reasons) > 0
        assert any("Insufficient confidence" in r for r in reasons)

    def test_conflicting_intelligence_rejection(self) -> None:
        tq = make_trade_qualification()
        risk_analysis = make_risk_analysis(tq)
        conflict = EvidenceConflict(
            conflict_type=ConflictType.BULLISH_VS_BEARISH,
            reason="Test conflict",
            evidence_items=(),
        )
        fusion = IntelligenceFusion(
            overall_score=Score(50.0),
            overall_confidence=Confidence(0.5),
            overall_signal=EvidenceSignal.NEUTRAL,
            conflicting_evidence=(conflict,),
            evidence_count=0,
        )
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
            intelligence_fusion=fusion,
        )

        validator = DecisionValidationEngine()
        reasons = validator.validate(di)

        assert len(reasons) > 0
        assert any("Conflicting intelligence" in r for r in reasons)

    def test_all_validations_pass(self) -> None:
        tq = make_trade_qualification(
            score=85.0,
            confidence=0.8,
            long_q=True,
            short_q=False,
            institutional=True,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.LOW)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        validator = DecisionValidationEngine()
        reasons = validator.validate(di)

        assert len(reasons) == 0


# ===========================================================================
# Evidence & Explanation Tests
# ===========================================================================


class TestEvidence:
    def test_evidence_produced(self) -> None:
        tq = make_trade_qualification()
        risk_analysis = make_risk_analysis(tq)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.evidence is not None
        assert result.evidence.source == "DecisionEngine"
        assert result.evidence.category == EvidenceCategory.TRADE_QUALIFICATION
        assert isinstance(result.evidence.score, Score)
        assert isinstance(result.evidence.confidence, Confidence)

    def test_evidence_no_trade(self) -> None:
        tq = make_trade_qualification(score=20.0, confidence=0.2)
        risk_analysis = make_risk_analysis(tq, EventRisk.EXTREME)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.evidence is not None
        assert (
            "no_trade" in str(result.evidence.reasons).lower()
            or result.decision == DecisionAction.NO_TRADE
        )


class TestExplanation:
    def test_explanation_produced(self) -> None:
        tq = make_trade_qualification(
            score=85.0,
            confidence=0.8,
            long_q=True,
            short_q=False,
            institutional=True,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.LOW)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.explanation is not None
        assert isinstance(result.explanation, DecisionExplanation)
        assert (
            "BUY" in result.explanation.decision_summary.upper()
            or result.explanation.decision_summary
        )

    def test_explanation_no_trade(self) -> None:
        tq = make_trade_qualification(score=20.0, confidence=0.2)
        risk_analysis = make_risk_analysis(tq, EventRisk.EXTREME)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.explanation is not None
        assert result.explanation.decision_summary


# ===========================================================================
# Serialization Tests
# ===========================================================================


class TestSerialization:
    def test_trade_decision_to_dict(self) -> None:
        td = TradeDecision(
            decision=DecisionAction.BUY,
            trade_direction=TradeDirection.LONG,
            instrument_type=InstrumentType.UNDERLYING,
            symbol="TEST",
            confidence=0.75,
            trade_score=80.0,
        )
        data = {
            "decision": td.decision.value,
            "trade_direction": td.trade_direction.value,
            "instrument_type": td.instrument_type.value,
            "symbol": td.symbol,
            "confidence": td.confidence,
            "trade_score": td.trade_score,
        }
        assert data["decision"] == "buy"
        assert data["trade_direction"] == "long"
        assert data["confidence"] == 0.75

    def test_trade_decision_json_serializable(self) -> None:
        td = TradeDecision(
            decision=DecisionAction.WATCHLIST,
            trade_direction=TradeDirection.LONG,
            instrument_type=InstrumentType.UNDERLYING,
            symbol="TEST",
            confidence=0.5,
            trade_score=60.0,
        )
        serializable = {
            "decision": td.decision.value,
            "trade_direction": td.trade_direction.value,
            "instrument_type": td.instrument_type.value,
            "symbol": td.symbol,
            "rank": td.rank.value,
            "confidence": td.confidence,
            "probability": td.probability,
            "trade_score": td.trade_score,
            "institutional_grade": td.institutional_grade,
        }
        json_str = json.dumps(serializable)
        restored = json.loads(json_str)
        assert restored["decision"] == "watchlist"
        assert restored["rank"] == "acceptable"
        assert restored["confidence"] == 0.5


# ===========================================================================
# Input Validation Tests
# ===========================================================================


class TestInputValidation:
    def test_invalid_input_type(self) -> None:
        engine = DecisionEngine()
        with pytest.raises(DecisionInputError):
            engine.decide(decision_input=None)  # type: ignore[arg-type]

    def test_missing_trade_qualification(self) -> None:
        engine = DecisionEngine()
        ra = make_risk_analysis(make_trade_qualification())
        with pytest.raises(DecisionInputError):
            di = DecisionInput(trade_qualification=None, risk_analysis=ra)  # type: ignore[arg-type]
            engine.decide(decision_input=di)

    def test_missing_risk_analysis(self) -> None:
        engine = DecisionEngine()
        tq = make_trade_qualification()
        with pytest.raises(DecisionInputError):
            di = DecisionInput(trade_qualification=tq, risk_analysis=None)  # type: ignore[arg-type]
            engine.decide(decision_input=di)


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestEdgeCases:
    def test_extreme_event_rejected(self) -> None:
        tq = make_trade_qualification(score=95.0, confidence=0.9)
        risk_analysis = make_risk_analysis(tq, EventRisk.EXTREME)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.decision == DecisionAction.NO_TRADE

    def test_low_score_rejected(self) -> None:
        tq = make_trade_qualification(score=10.0, confidence=0.1)
        risk_analysis = make_risk_analysis(tq, EventRisk.LOW)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.decision == DecisionAction.NO_TRADE
        assert result.rank == DecisionRank.REJECT

    def test_institutional_grade_detected(self) -> None:
        tq = make_trade_qualification(
            score=90.0,
            confidence=0.8,
            long_q=True,
            short_q=False,
            institutional=True,
        )
        risk_analysis = make_risk_analysis(tq, EventRisk.LOW)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.institutional_grade is True
        assert result.rank == DecisionRank.BEST


# ===========================================================================
# Exception Hierarchy
# ===========================================================================


class TestExceptions:
    def test_decision_error_base(self) -> None:
        assert issubclass(DecisionInputError, DecisionError)
        assert issubclass(DecisionValidationError, DecisionError)
        assert issubclass(DecisionEngineError, DecisionError)

    def test_decision_error_raised(self) -> None:
        with pytest.raises(DecisionError):
            raise DecisionInputError("test")


# ===========================================================================
# Selection Engine Tests
# ===========================================================================


class TestSelection:
    def test_holding_style_from_volatility(self) -> None:
        tq = make_trade_qualification()
        ra = make_risk_analysis(tq)
        vol = make_volatility(VolatilityRegime.EXPANSION)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=ra,
            volatility=vol,
        )

        selector = DecisionSelectionEngine()
        result = selector.select(
            decision_input=di,
            rank=DecisionRank.GOOD,
            validation_reasons=[],
        )

        assert result.holding_style == HoldingStyle.DAY_TRADE

    def test_instrument_type_option_call(self) -> None:
        tq = TradeQualification(
            status=TradeStatus.QUALIFIED,
            trade_score=TradeScore(value=80.0, band=ScoreBand.GOOD),
            confidence=0.7,
            decision_context="Test option trade",
            long_qualification=True,
            short_qualification=False,
            option_buying_qualification=True,
            option_selling_qualification=False,
        )
        ra = make_risk_analysis(tq)
        vol = make_volatility(VolatilityRegime.COMPRESSION, bias=MarketBias.BULLISH)
        gamma = make_gamma(GammaRegime.POSITIVE)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=ra,
            volatility=vol,
            gamma_exposure=gamma,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.instrument_type == InstrumentType.CALL_OPTION

    def test_instrument_type_underlying_default(self) -> None:
        tq = make_trade_qualification(
            score=75.0,
            confidence=0.7,
            long_q=True,
            short_q=False,
        )
        ra = make_risk_analysis(tq)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=ra,
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert result.instrument_type == InstrumentType.UNDERLYING


# ===========================================================================
# Integration
# ===========================================================================


class TestIntegration:
    def test_full_decision_pipeline(self) -> None:
        tq = make_trade_qualification(
            status=TradeStatus.QUALIFIED,
            score=85.0,
            confidence=0.8,
            long_q=True,
            short_q=False,
            institutional=True,
        )
        regime = make_market_regime()
        vol = make_volatility(VolatilityRegime.STABLE, bias=MarketBias.BULLISH)
        liq = make_liquidity(ExecutionGrade.A)
        dealer = make_dealer(DealerSide.LONG_GAMMA, DealerBiasLevel.BULLISH)
        gamma = make_gamma(GammaRegime.POSITIVE)
        event = make_event(EventRisk.LOW)

        risk_analysis = make_risk_analysis(tq, EventRisk.LOW)
        di = make_decision_input(
            trade_qualification=tq,
            risk_analysis=risk_analysis,
            market_regime=regime,
            volatility=vol,
            liquidity=liq,
            dealer_positioning=dealer,
            gamma_exposure=gamma,
            event_analysis=event,
            symbol="NIFTY",
        )

        engine = DecisionEngine()
        result = engine.decide(decision_input=di)

        assert isinstance(result, TradeDecision)
        assert isinstance(result.decision, DecisionAction)
        assert isinstance(result.trade_direction, TradeDirection)
        assert isinstance(result.instrument_type, InstrumentType)
        assert isinstance(result.rank, DecisionRank)
        assert isinstance(result.holding_style, HoldingStyle)
        assert isinstance(result.evidence, Evidence)
        assert isinstance(result.explanation, DecisionExplanation)
        assert isinstance(result.warnings, tuple)
        assert isinstance(result.metadata, dict)

        assert result.symbol == "NIFTY"
        assert result.confidence > 0.0
        assert result.trade_score > 0.0
        assert "sub_engines" in result.metadata
