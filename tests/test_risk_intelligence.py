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
    EventAnalysis,
    EventImportance,
    EventRisk,
    NewsAnalysis,
)
from titan.intelligence.fusion.models import IntelligenceFusion
from titan.market.intelligence.models import MarketRegime, MarketRegimeAnalysis
from titan.options.analytics.models import (
    DealerBiasLevel,
    DealerPositioningAnalysis,
    DealerSide,
    ExecutionGrade,
    GammaExposureAnalysis,
    GammaRegime,
    IVHVRelation,
    IVLevel,
    IVRankLevel,
    LiquidityAnalysis,
    MarketBias,
    PinningProbability,
    VolatilityAnalysis,
    VolatilityRegime,
    ZeroGammaLevel,
)
from titan.trading.models import (
    ScoreBand,
    TradeQualification,
    TradeScore,
    TradeStatus,
)
from titan.risk import (
    CapitalAllocationEngine,
    DecisionContext,
    ExposureAssessment,
    ExposureEngine,
    ExposureLevel,
    PositionInfo,
    PositionSizing,
    PositionSizingEngine,
    RiskAnalysis,
    RiskEngine,
    RiskExplanation,
    RiskInput,
    RiskProfile,
    RiskScore,
    RiskScoreBand,
    StopLossEngine,
    StopLossPlan,
    TargetEngine,
    TargetPlan,
)
from titan.risk.exceptions import RiskInputError, RiskValidationError

# ===========================================================================
# Helpers — factory functions
# ===========================================================================


def make_trade_qualification(
    status: TradeStatus = TradeStatus.QUALIFIED,
    score: float = 75.0,
    confidence: float = 0.7,
    long_q: bool = True,
    short_q: bool = False,
) -> TradeQualification:
    return TradeQualification(
        status=status,
        trade_score=TradeScore(value=score, band=ScoreBand.GOOD),
        confidence=confidence,
        decision_context="Test trade",
        long_qualification=long_q,
        short_qualification=short_q,
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
    iv_vs_hv: IVHVRelation = IVHVRelation.NORMAL,
) -> VolatilityAnalysis:
    return VolatilityAnalysis(
        current_iv=iv,
        current_hv=15.0,
        iv_rank=45.0,
        iv_percentile=50.0,
        iv_vs_hv=iv_vs_hv,
        volatility_regime=regime,
        iv_level=IVLevel.NORMAL,
        iv_rank_level=iv_rank,
        iv_trend="flat",
        hv_trend="flat",
        hv_stability="stable",
        buying_bias=False,
        selling_bias=False,
        overall_bias=MarketBias.NEUTRAL,
        confidence=0.7,
    )


def make_liquidity(
    grade: ExecutionGrade = ExecutionGrade.A,
    confidence: float = 0.8,
) -> LiquidityAnalysis:
    return LiquidityAnalysis(
        spread=0.05,
        spread_percent=0.01,
        depth_score=0.9,
        slippage_score=0.9,
        execution_score=0.9,
        execution_grade=grade,
        confidence=confidence,
    )


def make_dealer(
    side: DealerSide = DealerSide.LONG_GAMMA,
    bias: DealerBiasLevel = DealerBiasLevel.BULLISH,
    confidence: float = 0.7,
) -> DealerPositioningAnalysis:
    return DealerPositioningAnalysis(
        dealer_side=side,
        dealer_bias=bias,
        hedging_pressure=0.5,
        confidence=confidence,
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
    importance: EventImportance = EventImportance.LOW,
) -> EventAnalysis:
    return EventAnalysis(
        economic_events=(),
        corporate_events=(),
        highest_importance=importance,
        overall_risk=overall_risk,
        confidence=0.7,
    )


def make_risk_input(
    trade_qualification: TradeQualification | None = None,
    market_regime: MarketRegimeAnalysis | None = None,
    volatility: VolatilityAnalysis | None = None,
    liquidity: LiquidityAnalysis | None = None,
    dealer_positioning: DealerPositioningAnalysis | None = None,
    gamma_exposure: GammaExposureAnalysis | None = None,
    event_analysis: EventAnalysis | None = None,
    news_analysis: NewsAnalysis | None = None,
    intelligence_fusion: IntelligenceFusion | None = None,
    underlying_price: float | None = 19600.0,
    entry_price: float | None = 19600.0,
) -> RiskInput:
    return RiskInput(
        trade_qualification=trade_qualification or make_trade_qualification(),
        market_regime=market_regime,
        volatility=volatility,
        liquidity=liquidity,
        dealer_positioning=dealer_positioning,
        gamma_exposure=gamma_exposure,
        event_analysis=event_analysis,
        news_analysis=news_analysis,
        intelligence_fusion=intelligence_fusion,
        underlying_price=underlying_price,
        entry_price=entry_price,
    )


# ===========================================================================
# Model Tests
# ===========================================================================


class TestRiskScore:
    def test_valid_risk_score(self) -> None:
        score = RiskScore(value=45.0, band=RiskScoreBand.MODERATE)
        assert score.value == 45.0
        assert score.band == RiskScoreBand.MODERATE

    def test_invalid_risk_score_low(self) -> None:
        with pytest.raises(
            ValueError, match="RiskScore value must be between 0 and 100"
        ):
            RiskScore(value=-1.0, band=RiskScoreBand.VERY_LOW)

    def test_invalid_risk_score_high(self) -> None:
        with pytest.raises(
            ValueError, match="RiskScore value must be between 0 and 100"
        ):
            RiskScore(value=101.0, band=RiskScoreBand.EXTREME)


class TestPositionSizing:
    def test_fields(self) -> None:
        ps = PositionSizing(
            maximum_capital=10000.0,
            risk_per_trade=500.0,
            units=50,
            contracts=5,
            maximum_quantity=50,
            capital_utilization=0.1,
        )
        assert ps.maximum_capital == 10000.0
        assert ps.units == 50
        assert ps.contracts == 5


class TestStopLossPlan:
    def test_default_stop_loss(self) -> None:
        sl = StopLossPlan()
        assert sl.recommended_stop == 0.0
        assert sl.technical_stop is None

    def test_full_stop_loss(self) -> None:
        sl = StopLossPlan(
            technical_stop=19400.0,
            volatility_stop=19350.0,
            time_stop="Before FOMC: 2026-07-10",
            invalidation_level=19200.0,
            emergency_stop=19000.0,
            recommended_stop=19400.0,
        )
        assert sl.technical_stop == 19400.0
        assert sl.invalidation_level == 19200.0


class TestTargetPlan:
    def test_default_targets(self) -> None:
        tp = TargetPlan()
        assert tp.target_1 == 0.0
        assert tp.expected_risk_reward == 0.0

    def test_full_targets(self) -> None:
        tp = TargetPlan(
            target_1=19700.0,
            target_2=19800.0,
            target_3=20000.0,
            trailing_stop_trigger=19700.0,
            expected_risk_reward=2.5,
        )
        assert tp.expected_risk_reward == 2.5


class TestRiskInput:
    def test_required_trade_qualification(self) -> None:
        tq = make_trade_qualification()
        ri = RiskInput(trade_qualification=tq)
        assert ri.trade_qualification.status == TradeStatus.QUALIFIED
        assert ri.entry_price is None

    def test_with_all_fields(self) -> None:
        ri = make_risk_input()
        assert ri.underlying_price == 19600.0
        assert ri.entry_price == 19600.0


class TestRiskAnalysis:
    def test_default_construction(self) -> None:
        ps = PositionSizing(10000.0, 500.0, 50, 5, 50, 0.1)
        sl = StopLossPlan(recommended_stop=19400.0)
        tp = TargetPlan(19700.0, 19800.0, 20000.0, 19700.0, 2.5)
        ca = type("CA", (), {})()
        ea = ExposureAssessment()
        dc = DecisionContext()
        rs = RiskScore(30.0, RiskScoreBand.LOW)

        analysis = RiskAnalysis(
            risk_profile=RiskProfile.MODERATE,
            risk_score=rs,
            position_sizing=ps,
            stop_loss=sl,
            targets=tp,
            capital_allocation=ca,
            exposure=ea,
            decision_context=dc,
        )
        assert analysis.risk_profile == RiskProfile.MODERATE
        assert analysis.risk_score.value == 30.0
        assert analysis.decision_context.normal_size is False


class TestRiskProfile:
    def test_all_profiles_have_config(self) -> None:
        from titan.risk.models import RISK_PROFILE_MAP

        for profile in RiskProfile:
            assert profile in RISK_PROFILE_MAP
            config = RISK_PROFILE_MAP[profile]
            assert config.max_risk_per_trade_pct > 0.0
            assert config.kelly_fraction > 0.0


class TestSerialization:
    def test_risk_analysis_to_dict(self) -> None:
        ps = PositionSizing(10000.0, 500.0, 50, 5, 50, 0.1)
        sl = StopLossPlan(recommended_stop=19400.0)
        tp = TargetPlan(19700.0, 19800.0, 20000.0, 19700.0, 2.5)
        ca = type("CA", (), dict(capital_used=50000.0, available_capital=950000.0))()
        ea = ExposureAssessment()
        dc = DecisionContext()
        rs = RiskScore(30.0, RiskScoreBand.LOW)

        analysis = RiskAnalysis(
            risk_profile=RiskProfile.MODERATE,
            risk_score=rs,
            position_sizing=ps,
            stop_loss=sl,
            targets=tp,
            capital_allocation=ca,
            exposure=ea,
            decision_context=dc,
        )

        data = {
            "risk_profile": analysis.risk_profile.value,
            "risk_score": {
                "value": analysis.risk_score.value,
                "band": analysis.risk_score.band.value,
            },
            "position_sizing": {
                "maximum_capital": analysis.position_sizing.maximum_capital,
                "units": analysis.position_sizing.units,
                "contracts": analysis.position_sizing.contracts,
            },
        }
        assert data["risk_profile"] == "moderate"
        assert data["risk_score"]["value"] == 30.0
        assert data["position_sizing"]["units"] == 50

        json_str = json.dumps(data)
        restored = json.loads(json_str)
        assert restored["risk_profile"] == "moderate"
        assert restored["position_sizing"]["units"] == 50


# ===========================================================================
# Low Risk Scenario
# ===========================================================================


class TestLowRiskScenario:
    def test_low_risk_analysis(self) -> None:
        tq = make_trade_qualification(score=85.0, confidence=0.8)
        regime = make_market_regime(trend_strength=0.8)
        vol = make_volatility(VolatilityRegime.STABLE, IVRankLevel.LOW)
        liq = make_liquidity(ExecutionGrade.A)
        dealer = make_dealer(DealerSide.LONG_GAMMA, DealerBiasLevel.BULLISH)
        gamma = make_gamma(GammaRegime.POSITIVE)
        event = make_event(EventRisk.LOW)

        risk_input = make_risk_input(
            trade_qualification=tq,
            market_regime=regime,
            volatility=vol,
            liquidity=liq,
            dealer_positioning=dealer,
            gamma_exposure=gamma,
            event_analysis=event,
        )

        engine = RiskEngine()
        result = engine.analyze(
            risk_input=risk_input,
            risk_profile=RiskProfile.CONSERVATIVE,
            total_capital=1_000_000.0,
        )

        assert result.risk_profile == RiskProfile.CONSERVATIVE
        assert result.risk_score.band in (
            RiskScoreBand.VERY_LOW,
            RiskScoreBand.LOW,
        )
        assert (
            result.decision_context.normal_size or result.decision_context.increase_size
        )
        assert result.decision_context.avoid_trade is False
        assert result.position_sizing.units > 0
        assert result.stop_loss.recommended_stop > 0.0
        assert result.targets.expected_risk_reward > 1.0
        assert result.evidence is not None
        assert result.explanation is not None
        assert "Position Sizing" in result.explanation.position_size


# ===========================================================================
# High Risk Scenario
# ===========================================================================


class TestHighRiskScenario:
    def test_high_risk_analysis(self) -> None:
        tq = make_trade_qualification(score=30.0, confidence=0.3)
        vol = make_volatility(VolatilityRegime.EXPANSION, IVRankLevel.VERY_HIGH)
        liq = make_liquidity(ExecutionGrade.D)
        dealer = make_dealer(DealerSide.SHORT_GAMMA, DealerBiasLevel.BEARISH)
        gamma = make_gamma(GammaRegime.NEGATIVE)
        event = make_event(EventRisk.HIGH)

        risk_input = make_risk_input(
            trade_qualification=tq,
            volatility=vol,
            liquidity=liq,
            dealer_positioning=dealer,
            gamma_exposure=gamma,
            event_analysis=event,
        )

        engine = RiskEngine()
        result = engine.analyze(
            risk_input=risk_input,
            risk_profile=RiskProfile.MODERATE,
            total_capital=1_000_000.0,
        )

        assert result.risk_score.band in (
            RiskScoreBand.HIGH,
            RiskScoreBand.EXTREME,
        )
        assert (
            result.decision_context.reduce_size or result.decision_context.avoid_trade
        )
        assert result.position_sizing.units <= 10
        assert result.evidence is not None


# ===========================================================================
# Extreme Event Risk Scenario
# ===========================================================================


class TestExtremeEventRisk:
    def test_extreme_event_avoids_trade(self) -> None:
        tq = make_trade_qualification(score=75.0, confidence=0.7)
        event = make_event(EventRisk.EXTREME, EventImportance.CRITICAL)

        risk_input = make_risk_input(
            trade_qualification=tq,
            event_analysis=event,
        )

        engine = RiskEngine()
        result = engine.analyze(
            risk_input=risk_input,
            risk_profile=RiskProfile.CONSERVATIVE,
            total_capital=1_000_000.0,
        )

        assert result.decision_context.avoid_trade is True
        assert "avoid" in result.explanation.overall_risk_assessment.lower()


# ===========================================================================
# Low Liquidity Scenario
# ===========================================================================


class TestLowLiquidityScenario:
    def test_low_liquidity_reduces_size(self) -> None:
        tq = make_trade_qualification(score=80.0, confidence=0.8)
        liq = make_liquidity(ExecutionGrade.F)

        risk_input = make_risk_input(
            trade_qualification=tq,
            liquidity=liq,
        )

        engine = RiskEngine()
        result = engine.analyze(
            risk_input=risk_input,
            risk_profile=RiskProfile.MODERATE,
            total_capital=1_000_000.0,
        )

        assert result.exposure.liquidity_exposure == ExposureLevel.EXTREME
        # Position size should be reduced vs. full sizing
        full_input = make_risk_input(trade_qualification=tq)
        full_result = engine.analyze(
            risk_input=full_input,
            risk_profile=RiskProfile.MODERATE,
            total_capital=1_000_000.0,
        )
        assert (
            result.position_sizing.maximum_capital
            <= full_result.position_sizing.maximum_capital
        )


# ===========================================================================
# High Volatility Scenario
# ===========================================================================


class TestHighVolatilityScenario:
    def test_high_volatility_assessment(self) -> None:
        tq = make_trade_qualification(score=70.0)
        vol = make_volatility(VolatilityRegime.EXPANSION, IVRankLevel.VERY_HIGH)

        risk_input = make_risk_input(
            trade_qualification=tq,
            volatility=vol,
        )

        engine = RiskEngine()
        result = engine.analyze(
            risk_input=risk_input,
            risk_profile=RiskProfile.MODERATE,
            total_capital=1_000_000.0,
        )

        assert result.exposure.volatility_exposure in (
            ExposureLevel.HIGH,
            ExposureLevel.MODERATE,
        )
        assert result.stop_loss.volatility_stop is not None


# ===========================================================================
# Position Sizing Tests
# ===========================================================================


class TestPositionSizingEngine:
    def test_conservative_sizing(self) -> None:
        tq = make_trade_qualification(score=75.0)
        ri = make_risk_input(trade_qualification=tq)

        engine = PositionSizingEngine()
        result = engine.size(
            risk_input=ri,
            risk_profile=RiskProfile.CONSERVATIVE,
            total_capital=1_000_000.0,
            entry_price=19600.0,
        )

        assert result.maximum_capital <= 100000.0  # 10% of 1M
        assert result.risk_per_trade <= 20000.0  # 2% of 1M
        assert result.units > 0
        assert result.contracts > 0
        assert 0.0 <= result.capital_utilization <= 1.0

    def test_aggressive_sizing_larger_than_conservative(self) -> None:
        tq = make_trade_qualification(score=75.0)
        ri = make_risk_input(trade_qualification=tq)

        engine = PositionSizingEngine()
        cons = engine.size(ri, RiskProfile.CONSERVATIVE, entry_price=19600.0)
        aggr = engine.size(ri, RiskProfile.AGGRESSIVE, entry_price=19600.0)

        assert aggr.maximum_capital > cons.maximum_capital
        assert aggr.risk_per_trade > cons.risk_per_trade

    def test_no_entry_price(self) -> None:
        tq = make_trade_qualification()
        ri = make_risk_input(trade_qualification=tq, entry_price=None)

        engine = PositionSizingEngine()
        result = engine.size(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
            total_capital=1_000_000.0,
            entry_price=None,
        )

        assert result.units == 0
        assert result.contracts == 0

    def test_low_score_reduces_size(self) -> None:
        high = make_risk_input(
            trade_qualification=make_trade_qualification(score=85.0),
        )
        low = make_risk_input(
            trade_qualification=make_trade_qualification(score=25.0),
        )

        engine = PositionSizingEngine()
        high_result = engine.size(high, RiskProfile.MODERATE, entry_price=19600.0)
        low_result = engine.size(low, RiskProfile.MODERATE, entry_price=19600.0)

        assert low_result.maximum_capital < high_result.maximum_capital


# ===========================================================================
# Stop Loss Tests
# ===========================================================================


class TestStopLossEngine:
    def test_stop_loss_calculation(self) -> None:
        tq = make_trade_qualification()
        ri = make_risk_input(trade_qualification=tq)

        engine = StopLossEngine()
        result = engine.calculate(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
            entry_price=19600.0,
        )

        assert result.recommended_stop > 0.0
        assert result.recommended_stop < 19600.0  # Long = stop below entry

    def test_no_entry_price(self) -> None:
        tq = make_trade_qualification()
        ri = make_risk_input(trade_qualification=tq, entry_price=None)

        engine = StopLossEngine()
        result = engine.calculate(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
            entry_price=None,
        )

        assert result.recommended_stop == 0.0
        assert result.time_stop == "No entry price provided."

    def test_technical_stop_from_gamma(self) -> None:
        tq = make_trade_qualification()
        gamma = make_gamma(GammaRegime.POSITIVE)
        ri = make_risk_input(trade_qualification=tq, gamma_exposure=gamma)

        engine = StopLossEngine()
        result = engine.calculate(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
            entry_price=19600.0,
        )

        # Zero gamma level at 19500 should be the technical stop
        assert result.technical_stop is not None


# ===========================================================================
# Target Tests
# ===========================================================================


class TestTargetEngine:
    def test_target_calculation(self) -> None:
        tq = make_trade_qualification()
        ri = make_risk_input(trade_qualification=tq)
        sl = StopLossPlan(recommended_stop=19400.0)

        engine = TargetEngine()
        result = engine.calculate(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
            entry_price=19600.0,
            stop_loss=sl,
        )

        assert result.target_1 > 19600.0  # Long = targets above entry
        assert result.target_2 > result.target_1
        assert result.target_3 > result.target_2
        assert result.expected_risk_reward > 0.0

    def test_no_stop_loss_uses_default(self) -> None:
        tq = make_trade_qualification()
        ri = make_risk_input(trade_qualification=tq)

        engine = TargetEngine()
        result = engine.calculate(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
            entry_price=19600.0,
            stop_loss=None,
        )

        assert result.target_1 > 0.0
        assert result.expected_risk_reward > 0.0

    def test_no_entry_price(self) -> None:
        engine = TargetEngine()
        result = engine.calculate(
            risk_input=make_risk_input(),
            risk_profile=RiskProfile.MODERATE,
            entry_price=None,
            stop_loss=None,
        )

        assert result.target_1 == 0.0


# ===========================================================================
# Exposure Tests
# ===========================================================================


class TestExposureEngine:
    def test_low_exposure(self) -> None:
        ri = make_risk_input()

        engine = ExposureEngine()
        result = engine.assess(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
        )

        assert result.directional_exposure in (ExposureLevel.LOW,)
        assert result.volatility_exposure in (ExposureLevel.LOW,)

    def test_high_exposure_from_dealer(self) -> None:
        tq = make_trade_qualification()
        dealer = make_dealer(DealerSide.SHORT_GAMMA, DealerBiasLevel.BEARISH)
        gamma = make_gamma(GammaRegime.NEGATIVE)
        ri = make_risk_input(
            trade_qualification=tq,
            dealer_positioning=dealer,
            gamma_exposure=gamma,
        )

        engine = ExposureEngine()
        result = engine.assess(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
        )

        assert result.directional_exposure == ExposureLevel.HIGH

    def test_extreme_liquidity_exposure(self) -> None:
        tq = make_trade_qualification()
        liq = make_liquidity(ExecutionGrade.F)
        ri = make_risk_input(trade_qualification=tq, liquidity=liq)

        engine = ExposureEngine()
        result = engine.assess(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
        )

        assert result.liquidity_exposure == ExposureLevel.EXTREME


# ===========================================================================
# Capital Allocation Tests
# ===========================================================================


class TestCapitalAllocationEngine:
    def test_no_positions(self) -> None:
        tq = make_trade_qualification()
        ri = make_risk_input(trade_qualification=tq)

        engine = CapitalAllocationEngine()
        result = engine.allocate(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
            total_capital=1_000_000.0,
        )

        assert result.capital_used == 0.0
        assert result.available_capital == 1_000_000.0
        assert result.maximum_allocation == 150_000.0  # 15% of 1M
        assert result.portfolio_concentration == 0.0

    def test_with_positions(self) -> None:
        tq = make_trade_qualification()
        ri = make_risk_input(trade_qualification=tq)
        positions = (
            PositionInfo(
                symbol="BANKNIFTY",
                direction="long",
                quantity=50,
                entry_price=49000.0,
                current_price=49200.0,
                market_value=2_460_000.0,
                pnl=10000.0,
            ),
        )

        engine = CapitalAllocationEngine()
        result = engine.allocate(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
            total_capital=10_000_000.0,
            current_positions=positions,
        )

        assert result.capital_used == 2_460_000.0
        assert result.available_capital == 7_540_000.0
        assert result.portfolio_concentration == 0.246

    def test_event_risk_reduces_allocation(self) -> None:
        tq = make_trade_qualification()
        event = make_event(EventRisk.EXTREME)
        ri = make_risk_input(trade_qualification=tq, event_analysis=event)

        engine = CapitalAllocationEngine()
        result = engine.allocate(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
            total_capital=1_000_000.0,
        )

        assert result.maximum_allocation <= 150_000.0 * 0.25


# ===========================================================================
# Evidence Generation Tests
# ===========================================================================


class TestEvidenceGeneration:
    def test_evidence_produced(self) -> None:
        ri = make_risk_input()

        engine = RiskEngine()
        result = engine.analyze(risk_input=ri)

        assert result.evidence is not None
        assert result.evidence.source == "RiskEngine"
        assert result.evidence.category == EvidenceCategory.RISK
        assert isinstance(result.evidence.score, Score)
        assert isinstance(result.evidence.confidence, Confidence)
        assert len(result.evidence.reasons) > 0

    def test_evidence_avoid_trade_signal(self) -> None:
        tq = make_trade_qualification(score=20.0, confidence=0.2)
        event = make_event(EventRisk.EXTREME)
        ri = make_risk_input(trade_qualification=tq, event_analysis=event)

        engine = RiskEngine()
        result = engine.analyze(
            risk_input=ri,
            risk_profile=RiskProfile.CONSERVATIVE,
        )

        assert result.evidence is not None
        assert result.evidence.signal in (
            EvidenceSignal.VERY_BEARISH,
            EvidenceSignal.BEARISH,
        )


# ===========================================================================
# Explanation Generation Tests
# ===========================================================================


class TestExplanationGeneration:
    def test_explanation_produced(self) -> None:
        ri = make_risk_input()

        engine = RiskEngine()
        result = engine.analyze(risk_input=ri)

        assert result.explanation is not None
        assert "Position Sizing" in result.explanation.position_size
        assert "Capital Allocation" in result.explanation.capital_allocation
        assert "Stop Loss" in result.explanation.stop_loss
        assert "Targets" in result.explanation.targets
        assert "Exposure" in result.explanation.exposure
        assert "Overall Risk Assessment" in result.explanation.overall_risk_assessment

    def test_avoid_trade_explanation(self) -> None:
        tq = make_trade_qualification(score=15.0)
        event = make_event(EventRisk.EXTREME)
        ri = make_risk_input(trade_qualification=tq, event_analysis=event)

        engine = RiskEngine()
        result = engine.analyze(
            risk_input=ri,
            risk_profile=RiskProfile.CONSERVATIVE,
        )

        assert result.explanation is not None
        assert "avoided" in result.explanation.overall_risk_assessment.lower()


# ===========================================================================
# Validation Tests
# ===========================================================================


class TestValidation:
    def test_invalid_input_type(self) -> None:
        engine = RiskEngine()
        with pytest.raises(RiskInputError):
            engine.analyze(risk_input="not_risk_input")  # type: ignore

    def test_invalid_risk_profile(self) -> None:
        tq = make_trade_qualification()
        ri = make_risk_input(trade_qualification=tq)
        engine = RiskEngine()

        with pytest.raises(RiskValidationError):
            engine.analyze(
                risk_input=ri,
                risk_profile="ultra_aggressive",  # type: ignore
            )

    def test_missing_trade_qualification(self) -> None:
        with pytest.raises(RiskInputError):
            engine = RiskEngine()
            engine.analyze(
                risk_input="bad_input",  # type: ignore
            )


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestEdgeCases:
    def test_zero_capital(self) -> None:
        tq = make_trade_qualification()
        ri = make_risk_input(trade_qualification=tq)

        engine = RiskEngine()
        result = engine.analyze(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
            total_capital=0.0,
        )

        assert result.position_sizing.maximum_capital >= 0.0
        assert result.capital_allocation.available_capital == 0.0

    def test_all_intelligence_missing(self) -> None:
        tq = make_trade_qualification()
        ri = RiskInput(trade_qualification=tq)

        engine = RiskEngine()
        result = engine.analyze(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
        )

        assert result.risk_score is not None
        assert 0.0 <= result.risk_score.value <= 100.0
        assert result.position_sizing.maximum_capital >= 0.0

    def test_high_score_extreme_event_rejected(self) -> None:
        tq = make_trade_qualification(score=95.0, confidence=0.9)
        event = make_event(EventRisk.EXTREME)
        ri = make_risk_input(trade_qualification=tq, event_analysis=event)

        engine = RiskEngine()
        result = engine.analyze(
            risk_input=ri,
            risk_profile=RiskProfile.MODERATE,
        )

        assert result.decision_context.avoid_trade is True
        assert result.decision_context.hedging_required is True


# ===========================================================================
# Integration: Full Pipeline
# ===========================================================================


class TestIntegration:
    def test_full_risk_analysis_pipeline(self) -> None:
        tq = make_trade_qualification(
            status=TradeStatus.QUALIFIED,
            score=80.0,
            confidence=0.75,
        )
        regime = make_market_regime(trend_strength=0.7)
        vol = make_volatility(VolatilityRegime.STABLE, IVRankLevel.LOW)
        liq = make_liquidity(ExecutionGrade.A)
        dealer = make_dealer(DealerSide.LONG_GAMMA, DealerBiasLevel.BULLISH)
        gamma = make_gamma(GammaRegime.POSITIVE)
        event = make_event(EventRisk.LOW)

        ri = make_risk_input(
            trade_qualification=tq,
            market_regime=regime,
            volatility=vol,
            liquidity=liq,
            dealer_positioning=dealer,
            gamma_exposure=gamma,
            event_analysis=event,
        )

        engine = RiskEngine()
        result = engine.analyze(
            risk_input=ri,
            risk_profile=RiskProfile.INSTITUTIONAL,
            total_capital=10_000_000.0,
        )

        assert isinstance(result, RiskAnalysis)
        assert isinstance(result.risk_score, RiskScore)
        assert isinstance(result.position_sizing, PositionSizing)
        assert isinstance(result.stop_loss, StopLossPlan)
        assert isinstance(result.targets, TargetPlan)
        assert isinstance(result.capital_allocation, type(result.capital_allocation))
        assert isinstance(result.exposure, ExposureAssessment)
        assert isinstance(result.decision_context, DecisionContext)
        assert isinstance(result.evidence, Evidence)
        assert isinstance(result.explanation, RiskExplanation)
        assert isinstance(result.warnings, tuple)
        assert isinstance(result.metadata, dict)
        assert "Risk Score" in str(result.evidence.reasons)

        assert result.position_sizing.maximum_capital > 0.0
        assert result.stop_loss.recommended_stop > 0.0
        assert result.targets.expected_risk_reward > 0.0


# ===========================================================================
# Risk Score Band Tests
# ===========================================================================


class TestRiskScoreBand:
    def test_band_thresholds(self) -> None:
        engine = RiskEngine()

        good_tq = make_trade_qualification(score=90.0, confidence=0.9)
        good_vol = make_volatility()
        good_liq = make_liquidity()
        good_event = make_event()
        good_ri = make_risk_input(
            trade_qualification=good_tq,
            volatility=good_vol,
            liquidity=good_liq,
            event_analysis=good_event,
        )
        good_result = engine.analyze(risk_input=good_ri)
        assert good_result.risk_score.band == RiskScoreBand.VERY_LOW

        bad_tq = make_trade_qualification(score=10.0, confidence=0.1)
        bad_vol = make_volatility(VolatilityRegime.EXPANSION, IVRankLevel.VERY_HIGH)
        bad_liq = make_liquidity(ExecutionGrade.F)
        bad_event = make_event(EventRisk.EXTREME)
        bad_dealer = make_dealer(DealerSide.SHORT_GAMMA, DealerBiasLevel.BEARISH)
        bad_gamma = make_gamma(GammaRegime.NEGATIVE)
        bad_ri = make_risk_input(
            trade_qualification=bad_tq,
            volatility=bad_vol,
            liquidity=bad_liq,
            event_analysis=bad_event,
            dealer_positioning=bad_dealer,
            gamma_exposure=bad_gamma,
        )
        bad_result = engine.analyze(risk_input=bad_ri)
        assert bad_result.risk_score.band in (
            RiskScoreBand.HIGH,
            RiskScoreBand.EXTREME,
        )
