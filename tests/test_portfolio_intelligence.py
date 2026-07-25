import json

import pytest

from titan.core.evidence import (
    Confidence,
    EvidenceCategory,
    Score,
)
from titan.decision.models import (
    DecisionAction,
    DecisionRank,
    HoldingStyle,
    InstrumentType,
    TradeDecision,
)
from titan.trading.models import TradeDirection

from titan.portfolio import (
    CapitalAllocationAnalyzer,
    CorrelationAnalysis,
    CorrelationAnalyzer,
    CorrelationLevel,
    ExistingPortfolio,
    ExposureAnalyzer,
    HedgingAction,
    HedgingAnalyzer,
    HedgingRecommendation,
    OpenPosition,
    PortfolioAnalysis,
    PortfolioDecisionContext,
    PortfolioEngine,
    PortfolioExplanation,
    PortfolioExposure,
    PortfolioInputError,
    PortfolioScoreBand,
    PositionAnalyzer,
    SectorExposure,
)
from titan.risk.models import (
    CapitalAllocation as RiskCapitalAllocation,
    DecisionContext as RiskDecisionContext,
    ExposureAssessment,
    PositionSizing,
    RiskAnalysis,
    RiskExplanation,
    RiskProfile,
    RiskScore,
    RiskScoreBand,
    StopLossPlan,
    TargetPlan,
)

# ===========================================================================
# Helpers — factory functions
# ===========================================================================


def make_open_position(
    symbol: str = "AAPL",
    instrument_type: str = "underlying",
    direction: str = "long",
    quantity: int = 100,
    entry_price: float = 150.0,
    current_price: float = 155.0,
    market_value: float = 15500.0,
    pnl: float = 500.0,
    sector: str = "Technology",
    weight: float = 0.25,
    delta: float | None = None,
    gamma: float | None = None,
    vega: float | None = None,
    theta: float | None = None,
) -> OpenPosition:
    return OpenPosition(
        symbol=symbol,
        instrument_type=instrument_type,
        direction=direction,
        quantity=quantity,
        entry_price=entry_price,
        current_price=current_price,
        market_value=market_value,
        pnl=pnl,
        sector=sector,
        weight=weight,
        delta=delta,
        gamma=gamma,
        vega=vega,
        theta=theta,
    )


def make_portfolio(
    positions: tuple[OpenPosition, ...] | None = None,
    total_capital: float = 100000.0,
    cash_reserve: float = 10000.0,
    name: str = "Test Portfolio",
) -> ExistingPortfolio:
    return ExistingPortfolio(
        positions=positions or (),
        total_capital=total_capital,
        cash_reserve=cash_reserve,
        name=name,
    )


def make_trade_decision(
    symbol: str = "AAPL",
    action: DecisionAction = DecisionAction.BUY,
) -> TradeDecision:
    return TradeDecision(
        decision=action,
        trade_direction=TradeDirection.LONG,
        instrument_type=InstrumentType.UNDERLYING,
        symbol=symbol,
        holding_style=HoldingStyle.SWING,
        rank=DecisionRank.GOOD,
        confidence=0.75,
        probability=0.65,
        trade_score=75.0,
    )


def make_simple_portfolio() -> ExistingPortfolio:
    return make_portfolio(
        positions=(
            make_open_position(
                symbol="AAPL",
                market_value=25000.0,
                pnl=500.0,
                sector="Technology",
                weight=0.25,
            ),
            make_open_position(
                symbol="MSFT",
                market_value=20000.0,
                pnl=-200.0,
                sector="Technology",
                weight=0.20,
            ),
            make_open_position(
                symbol="GOOGL",
                market_value=15000.0,
                pnl=300.0,
                sector="Technology",
                weight=0.15,
            ),
        ),
        total_capital=100000.0,
        cash_reserve=10000.0,
    )


def make_risk_analysis() -> RiskAnalysis:
    return RiskAnalysis(
        risk_profile=RiskProfile.MODERATE,
        risk_score=RiskScore(value=20.0, band=RiskScoreBand.LOW),
        position_sizing=PositionSizing(
            maximum_capital=10000.0,
            risk_per_trade=500.0,
            units=50,
            contracts=5,
            maximum_quantity=50,
            capital_utilization=0.1,
        ),
        stop_loss=StopLossPlan(recommended_stop=19400.0),
        targets=TargetPlan(target_1=19700.0, expected_risk_reward=2.5),
        capital_allocation=RiskCapitalAllocation(
            capital_used=0.0, available_capital=90000.0
        ),
        exposure=ExposureAssessment(),
        decision_context=RiskDecisionContext(normal_size=True),
        explanation=RiskExplanation(),
    )


# ===========================================================================
# Enum Tests
# ===========================================================================


class TestPortfolioEnums:
    def test_portfolio_score_band_values(self) -> None:
        assert PortfolioScoreBand.EXCELLENT.value == "excellent"
        assert PortfolioScoreBand.GOOD.value == "good"
        assert PortfolioScoreBand.MODERATE.value == "moderate"
        assert PortfolioScoreBand.POOR.value == "poor"
        assert PortfolioScoreBand.CRITICAL.value == "critical"

    def test_correlation_level_values(self) -> None:
        assert CorrelationLevel.VERY_LOW.value == "very_low"
        assert CorrelationLevel.LOW.value == "low"
        assert CorrelationLevel.MODERATE.value == "moderate"
        assert CorrelationLevel.HIGH.value == "high"
        assert CorrelationLevel.EXTREME.value == "extreme"

    def test_hedging_action_values(self) -> None:
        assert HedgingAction.NO_HEDGE_REQUIRED.value == "no_hedge_required"
        assert HedgingAction.REDUCE_EXPOSURE.value == "reduce_exposure"
        assert HedgingAction.INCREASE_HEDGE.value == "increase_hedge"
        assert HedgingAction.DIVERSIFY.value == "diversify"


# ===========================================================================
# Model Tests
# ===========================================================================


class TestOpenPosition:
    def test_required_fields(self) -> None:
        pos = OpenPosition(
            symbol="AAPL",
            instrument_type="underlying",
            direction="long",
            quantity=100,
            entry_price=150.0,
            current_price=155.0,
            market_value=15500.0,
        )
        assert pos.symbol == "AAPL"
        assert pos.quantity == 100
        assert pos.pnl == 0.0
        assert pos.delta is None

    def test_full_position(self) -> None:
        pos = make_open_position(delta=0.8, gamma=0.05, vega=0.3, theta=-0.1)
        assert pos.delta == 0.8
        assert pos.gamma == 0.05
        assert pos.vega == 0.3
        assert pos.theta == -0.1
        assert pos.weight == 0.25


class TestExistingPortfolio:
    def test_empty_portfolio(self) -> None:
        pf = ExistingPortfolio()
        assert pf.positions == ()
        assert pf.total_capital == 0.0
        assert pf.name == ""

    def test_with_positions(self) -> None:
        pf = make_simple_portfolio()
        assert len(pf.positions) == 3
        assert pf.total_capital == 100000.0
        assert pf.cash_reserve == 10000.0
        assert pf.name == "Test Portfolio"


class TestPortfolioSnapshot:
    def test_default_values(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        snap = PortfolioSnapshot()
        assert snap.total_capital == 0.0
        assert snap.utilization == 0.0
        assert snap.position_count == 0

    def test_populated_snapshot(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        snap = PortfolioSnapshot(
            total_capital=100000.0,
            cash_reserve=10000.0,
            capital_used=60000.0,
            available_capital=30000.0,
            total_market_value=60000.0,
            total_pnl=600.0,
            position_count=3,
            winning_positions=2,
            losing_positions=1,
            utilization=0.6,
        )
        assert snap.utilization == 0.6
        assert snap.winning_positions == 2
        assert snap.losing_positions == 1


class TestPortfolioExposure:
    def test_default_values(self) -> None:
        exp = PortfolioExposure()
        assert exp.net_delta is None
        assert exp.sector_concentration == 0.0

    def test_populated(self) -> None:
        exp = PortfolioExposure(
            net_delta=150.0,
            net_gamma=25.0,
            net_vega=300.0,
            net_theta=-50.0,
            directional_bias=150.0,
            sector_concentration=0.6,
            symbol_concentration=0.25,
        )
        assert exp.net_delta == 150.0
        assert exp.sector_concentration == 0.6


class TestSectorExposure:
    def test_fields(self) -> None:
        se = SectorExposure(
            sector="Technology",
            total_value=45000.0,
            weight=0.45,
            position_count=3,
        )
        assert se.sector == "Technology"
        assert se.weight == 0.45


class TestCorrelationAnalysis:
    def test_default_values(self) -> None:
        ca = CorrelationAnalysis()
        assert ca.highly_correlated_pairs == 0
        assert ca.overall_correlation_level == CorrelationLevel.LOW

    def test_high_correlation(self) -> None:
        ca = CorrelationAnalysis(
            highly_correlated_pairs=3,
            duplicate_exposure=True,
            index_concentration=True,
            sector_correlation=CorrelationLevel.HIGH,
            overall_correlation_level=CorrelationLevel.HIGH,
        )
        assert ca.overall_correlation_level == CorrelationLevel.HIGH
        assert ca.duplicate_exposure is True


class TestHedgingRecommendation:
    def test_default_values(self) -> None:
        hr = HedgingRecommendation()
        assert hr.action == HedgingAction.NO_HEDGE_REQUIRED
        assert hr.suggested_instruments == ()

    def test_populated(self) -> None:
        hr = HedgingRecommendation(
            action=HedgingAction.REDUCE_EXPOSURE,
            reason="Portfolio utilisation too high",
            suggested_instruments=("Index Futures",),
            max_cost=5000.0,
        )
        assert hr.action == HedgingAction.REDUCE_EXPOSURE
        assert "Index Futures" in hr.suggested_instruments


class TestPortfolioDecisionContext:
    def test_default_values(self) -> None:
        dc = PortfolioDecisionContext()
        assert dc.allow_trade is False
        assert dc.block_trade is False
        assert dc.confidence == 0.0

    def test_allow_trade(self) -> None:
        dc = PortfolioDecisionContext(
            allow_trade=True,
            max_contracts=5,
            remaining_capital=30000.0,
            confidence=0.85,
        )
        assert dc.allow_trade is True
        assert dc.max_contracts == 5


class TestPortfolioExplanation:
    def test_default_values(self) -> None:
        pe = PortfolioExplanation()
        assert pe.portfolio_summary == ""
        assert pe.recommendation == ""

    def test_populated(self) -> None:
        pe = PortfolioExplanation(
            portfolio_summary="3 positions, 60% utilised",
            exposure="Net delta 150.0",
            correlation="Low correlation risk",
            capital_allocation="30k remaining",
            hedging="No hedge required",
            recommendation="Allow trade",
        )
        assert "60% utilised" in pe.portfolio_summary


class TestPortfolioAnalysis:
    def test_default_construction(self) -> None:
        snap = type("S", (), dict(utilization=0.0))()
        exp = PortfolioExposure()
        corr = CorrelationAnalysis()
        hedge = HedgingRecommendation()
        dc = PortfolioDecisionContext()

        analysis = PortfolioAnalysis(
            portfolio_name="Test",
            snapshot=snap,  # type: ignore[arg-type]
            exposure=exp,
            sector_exposures=(),
            correlation=corr,
            hedging=hedge,
            portfolio_score=25.0,
            portfolio_band=PortfolioScoreBand.GOOD,
            decision_context=dc,
            allow_trade=True,
        )
        assert analysis.portfolio_name == "Test"
        assert analysis.portfolio_score == 25.0
        assert analysis.portfolio_band == PortfolioScoreBand.GOOD

    def test_full_analysis_fields(self) -> None:
        snap = type(
            "S",
            (),
            dict(
                utilization=0.0,
                capital_used=0.0,
                available_capital=0.0,
                total_pnl=0.0,
                position_count=0,
            ),
        )()
        exp = PortfolioExposure()
        se = SectorExposure("Technology", 45000.0, 0.45, 3)
        corr = CorrelationAnalysis()
        hedge = HedgingRecommendation()
        dc = PortfolioDecisionContext()

        analysis = PortfolioAnalysis(
            portfolio_name="Full",
            snapshot=snap,  # type: ignore[arg-type]
            exposure=exp,
            sector_exposures=(se,),
            correlation=corr,
            hedging=hedge,
            portfolio_score=50.0,
            portfolio_band=PortfolioScoreBand.MODERATE,
            decision_context=dc,
            allow_trade=True,
            evidence=None,
            explanation=None,
        )
        assert len(analysis.sector_exposures) == 1
        assert analysis.sector_exposures[0].sector == "Technology"


class TestSerialization:
    def test_portfolio_analysis_to_dict(self) -> None:
        snap = type(
            "S",
            (),
            dict(
                utilization=0.0,
                capital_used=0.0,
                available_capital=0.0,
                total_pnl=0.0,
                position_count=0,
            ),
        )()
        exp = PortfolioExposure()
        corr = CorrelationAnalysis()
        hedge = HedgingRecommendation()
        dc = PortfolioDecisionContext()

        analysis = PortfolioAnalysis(
            portfolio_name="Ser",
            snapshot=snap,  # type: ignore[arg-type]
            exposure=exp,
            sector_exposures=(),
            correlation=corr,
            hedging=hedge,
            portfolio_score=30.0,
            portfolio_band=PortfolioScoreBand.GOOD,
            decision_context=dc,
            allow_trade=True,
        )

        data = {
            "portfolio_name": analysis.portfolio_name,
            "portfolio_score": analysis.portfolio_score,
            "portfolio_band": analysis.portfolio_band.value,
            "allow_trade": analysis.allow_trade,
        }
        assert data["portfolio_name"] == "Ser"
        assert data["portfolio_score"] == 30.0
        assert data["portfolio_band"] == "good"

        json_str = json.dumps(data)
        restored = json.loads(json_str)
        assert restored["portfolio_score"] == 30.0


# ===========================================================================
# Position Analyzer Tests
# ===========================================================================


class TestPositionAnalyzer:
    def test_empty_portfolio(self) -> None:
        analyzer = PositionAnalyzer()
        pf = make_portfolio()
        snap = analyzer.analyze(pf)
        assert snap.position_count == 0
        assert snap.capital_used == 0.0
        assert snap.utilization == 0.0

    def test_simple_portfolio(self) -> None:
        analyzer = PositionAnalyzer()
        pf = make_simple_portfolio()
        snap = analyzer.analyze(pf)
        assert snap.position_count == 3
        assert snap.total_capital == 100000.0
        assert snap.cash_reserve == 10000.0
        assert snap.capital_used == 60000.0
        assert snap.total_pnl == 600.0
        assert snap.winning_positions == 2
        assert snap.losing_positions == 1
        assert snap.utilization == 0.6

    def test_available_capital(self) -> None:
        analyzer = PositionAnalyzer()
        pf = make_portfolio(
            positions=(make_open_position(market_value=50000.0),),
            total_capital=100000.0,
            cash_reserve=10000.0,
        )
        snap = analyzer.analyze(pf)
        assert snap.available_capital == 40000.0

    def test_name(self) -> None:
        assert PositionAnalyzer().name == "PositionAnalyzer"


# ===========================================================================
# Exposure Analyzer Tests
# ===========================================================================


class TestExposureAnalyzer:
    def test_empty_portfolio(self) -> None:
        analyzer = ExposureAnalyzer()
        pf = make_portfolio()
        exposure, sectors = analyzer.analyze(pf)
        assert exposure.net_delta is None
        assert exposure.sector_concentration == 0.0
        assert sectors == ()

    def test_simple_portfolio(self) -> None:
        analyzer = ExposureAnalyzer()
        pf = make_simple_portfolio()
        exposure, sectors = analyzer.analyze(pf)
        assert exposure.net_delta is None
        assert exposure.directional_bias == 0.0
        assert len(sectors) == 1
        assert sectors[0].sector == "Technology"
        assert sectors[0].position_count == 3

    def test_with_option_greeks(self) -> None:
        analyzer = ExposureAnalyzer()
        pf = make_portfolio(
            positions=(
                make_open_position(
                    symbol="AAPL",
                    market_value=25000.0,
                    sector="Technology",
                    delta=0.6,
                    gamma=0.05,
                    vega=0.3,
                    theta=-0.1,
                    quantity=10,
                ),
                make_open_position(
                    symbol="MSFT",
                    market_value=20000.0,
                    sector="Technology",
                    delta=0.7,
                    gamma=0.03,
                    vega=0.2,
                    theta=-0.05,
                    quantity=5,
                ),
            ),
            total_capital=100000.0,
        )
        exposure, sectors = analyzer.analyze(pf)
        assert exposure.net_delta is not None
        assert exposure.net_delta == 6.0 + 3.5
        assert exposure.net_gamma is not None
        assert exposure.net_vega is not None
        assert exposure.net_theta is not None

    def test_sector_concentration(self) -> None:
        analyzer = ExposureAnalyzer()
        pf = make_portfolio(
            positions=(
                make_open_position(market_value=40000.0, sector="Technology"),
                make_open_position(
                    symbol="JPM", market_value=10000.0, sector="Finance"
                ),
            ),
            total_capital=100000.0,
        )
        exposure, sectors = analyzer.analyze(pf)
        assert exposure.sector_concentration == 0.4
        assert len(sectors) == 2

    def test_name(self) -> None:
        assert ExposureAnalyzer().name == "ExposureAnalyzer"


# ===========================================================================
# Correlation Analyzer Tests
# ===========================================================================


class TestCorrelationAnalyzer:
    def test_empty_portfolio(self) -> None:
        analyzer = CorrelationAnalyzer()
        pf = make_portfolio()
        result = analyzer.analyze(pf)
        assert result.highly_correlated_pairs == 0
        assert result.duplicate_exposure is False
        assert result.overall_correlation_level == CorrelationLevel.LOW

    def test_all_same_sector(self) -> None:
        analyzer = CorrelationAnalyzer()
        pf = make_simple_portfolio()
        result = analyzer.analyze(pf)
        assert result.highly_correlated_pairs == 3
        assert result.sector_correlation == CorrelationLevel.EXTREME
        assert result.overall_correlation_level == CorrelationLevel.EXTREME

    def test_duplicate_symbol(self) -> None:
        analyzer = CorrelationAnalyzer()
        pf = make_portfolio(
            positions=(
                make_open_position(symbol="AAPL", sector="Technology"),
                make_open_position(symbol="AAPL", sector="Technology"),
            ),
        )
        result = analyzer.analyze(pf)
        assert result.duplicate_exposure is True
        assert result.overall_correlation_level == CorrelationLevel.EXTREME

    def test_index_concentration(self) -> None:
        analyzer = CorrelationAnalyzer()
        pf = make_portfolio(
            positions=(
                make_open_position(symbol="NIFTY", sector="Index"),
                make_open_position(symbol="BANKNIFTY", sector="Index"),
            ),
        )
        result = analyzer.analyze(pf)
        assert result.index_concentration is True

    def test_diversified_portfolio(self) -> None:
        analyzer = CorrelationAnalyzer()
        pf = make_portfolio(
            positions=(
                make_open_position(symbol="AAPL", sector="Technology"),
                make_open_position(symbol="JPM", sector="Finance"),
                make_open_position(symbol="PFE", sector="Healthcare"),
                make_open_position(symbol="XOM", sector="Energy"),
            ),
        )
        result = analyzer.analyze(pf)
        assert result.highly_correlated_pairs == 0
        assert result.sector_correlation == CorrelationLevel.LOW
        assert result.overall_correlation_level == CorrelationLevel.LOW

    def test_name(self) -> None:
        assert CorrelationAnalyzer().name == "CorrelationAnalyzer"


# ===========================================================================
# Capital Allocation Analyzer Tests
# ===========================================================================


class TestCapitalAllocationAnalyzer:
    def test_empty_portfolio(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        analyzer = CapitalAllocationAnalyzer()
        pf = make_portfolio()
        snap = PortfolioSnapshot(total_capital=100000.0, available_capital=90000.0)
        remaining, max_new, efficiency, headroom = analyzer.analyze(pf, snap)
        assert remaining == 90000.0
        assert max_new == 15000.0
        assert efficiency == 0.0

    def test_with_positions(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        analyzer = CapitalAllocationAnalyzer()
        pf = make_portfolio(
            positions=(make_open_position(market_value=10000.0),),
        )
        snap = PortfolioSnapshot(
            total_capital=100000.0,
            capital_used=10000.0,
            available_capital=80000.0,
            total_pnl=500.0,
            utilization=0.1,
        )
        remaining, max_new, efficiency, headroom = analyzer.analyze(pf, snap)
        assert remaining == 80000.0
        assert max_new == 5000.0
        assert efficiency == 0.05
        assert headroom >= 0.0

    def test_full_utilisation_zero_allocation(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        analyzer = CapitalAllocationAnalyzer()
        pf = make_portfolio(
            positions=(make_open_position(market_value=100000.0),),
            total_capital=100000.0,
        )
        snap = PortfolioSnapshot(
            total_capital=100000.0,
            capital_used=100000.0,
            utilization=1.0,
        )
        _, max_new, _, _ = analyzer.analyze(pf, snap)
        assert max_new == 0.0

    def test_negative_efficiency(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        analyzer = CapitalAllocationAnalyzer()
        pf = make_portfolio()
        snap = PortfolioSnapshot(
            total_capital=100000.0,
            capital_used=50000.0,
            total_pnl=-10000.0,
            available_capital=50000.0,
        )
        _, _, efficiency, _ = analyzer.analyze(pf, snap)
        assert efficiency < 0.0

    def test_name(self) -> None:
        assert CapitalAllocationAnalyzer().name == "CapitalAllocationAnalyzer"


# ===========================================================================
# Hedging Analyzer Tests
# ===========================================================================


class TestHedgingAnalyzer:
    def test_empty_portfolio(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        analyzer = HedgingAnalyzer()
        pf = make_portfolio()
        snap = PortfolioSnapshot()
        exp = PortfolioExposure()
        corr = CorrelationAnalysis()
        result = analyzer.analyze(pf, snap, exp, corr)
        assert result.action == HedgingAction.NO_HEDGE_REQUIRED

    def test_high_utilisation(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        analyzer = HedgingAnalyzer()
        pf = make_portfolio(positions=(make_open_position(market_value=95000.0),))
        snap = PortfolioSnapshot(utilization=0.95, capital_used=95000.0)
        exp = PortfolioExposure()
        corr = CorrelationAnalysis()
        result = analyzer.analyze(pf, snap, exp, corr)
        assert result.action == HedgingAction.REDUCE_EXPOSURE

    def test_symbol_concentration(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        analyzer = HedgingAnalyzer()
        pf = make_portfolio(
            positions=(make_open_position(market_value=80000.0, weight=0.8),)
        )
        snap = PortfolioSnapshot(
            utilization=0.5, total_capital=100000.0, capital_used=50000.0
        )
        exp = PortfolioExposure(symbol_concentration=0.8)
        corr = CorrelationAnalysis()
        result = analyzer.analyze(pf, snap, exp, corr)
        assert result.action == HedgingAction.DIVERSIFY

    def test_sector_concentration(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        analyzer = HedgingAnalyzer()
        pf = make_portfolio(
            positions=(
                make_open_position(market_value=30000.0, sector="Technology"),
                make_open_position(
                    symbol="MSFT", market_value=15000.0, sector="Technology"
                ),
            ),
        )
        snap = PortfolioSnapshot(
            utilization=0.5, total_capital=100000.0, capital_used=45000.0
        )
        exp = PortfolioExposure(sector_concentration=0.45, symbol_concentration=0.3)
        corr = CorrelationAnalysis()
        result = analyzer.analyze(pf, snap, exp, corr)
        assert result.action == HedgingAction.DIVERSIFY

    def test_high_correlation(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        analyzer = HedgingAnalyzer()
        pf = make_portfolio(
            positions=(make_open_position(), make_open_position(symbol="MSFT"))
        )
        snap = PortfolioSnapshot(
            utilization=0.5, total_capital=100000.0, capital_used=50000.0
        )
        exp = PortfolioExposure(sector_concentration=0.3, symbol_concentration=0.15)
        corr = CorrelationAnalysis(overall_correlation_level=CorrelationLevel.HIGH)
        result = analyzer.analyze(pf, snap, exp, corr)
        assert result.action == HedgingAction.DIVERSIFY

    def test_strong_directional_bias(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        analyzer = HedgingAnalyzer()
        pf = make_portfolio(
            positions=(make_open_position(delta=0.8, quantity=100),),
            total_capital=100000.0,
        )
        snap = PortfolioSnapshot(
            utilization=0.3, total_capital=100000.0, capital_used=30000.0
        )
        exp = PortfolioExposure(
            directional_bias=80.0,
            sector_concentration=0.2,
            symbol_concentration=0.15,
        )
        corr = CorrelationAnalysis()
        result = analyzer.analyze(pf, snap, exp, corr)
        assert result.action == HedgingAction.INCREASE_HEDGE

    def test_name(self) -> None:
        assert HedgingAnalyzer().name == "HedgingAnalyzer"


# ===========================================================================
# Portfolio Engine Integration Tests
# ===========================================================================


class TestPortfolioEngine:
    def test_empty_portfolio(self) -> None:
        engine = PortfolioEngine()
        pf = make_portfolio()
        td = make_trade_decision()
        ra = make_risk_analysis()

        result = engine.analyze(
            trade_decision=td,
            risk_analysis=ra,
            portfolio=pf,
        )

        assert isinstance(result, PortfolioAnalysis)
        assert result.portfolio_name == "Test Portfolio"
        assert result.snapshot.position_count == 0
        assert result.exposure.net_delta is None
        assert result.portfolio_score == 5.0
        assert result.portfolio_band == PortfolioScoreBand.EXCELLENT
        assert result.decision_context.allow_trade is True
        assert result.decision_context.block_trade is False
        assert result.evidence is not None
        assert result.evidence.category == EvidenceCategory.PORTFOLIO
        assert result.explanation is not None
        assert isinstance(result.warnings, tuple)

    def test_high_utilisation_blocks_trade(self) -> None:
        engine = PortfolioEngine()
        pf = make_portfolio(
            positions=(make_open_position(market_value=96000.0),),
            total_capital=100000.0,
        )
        td = make_trade_decision()
        ra = make_risk_analysis()

        result = engine.analyze(
            trade_decision=td,
            risk_analysis=ra,
            portfolio=pf,
        )

        assert result.decision_context.block_trade is True
        assert result.allow_trade is False
        assert "BLOCK" in (
            result.explanation.recommendation if result.explanation else ""
        )

    def test_moderate_utilisation_reduces_position(self) -> None:
        engine = PortfolioEngine()
        pf = make_portfolio(
            positions=(make_open_position(market_value=86000.0),),
            total_capital=100000.0,
        )
        td = make_trade_decision()
        ra = make_risk_analysis()

        result = engine.analyze(
            trade_decision=td,
            risk_analysis=ra,
            portfolio=pf,
        )

        assert result.decision_context.reduce_position is True
        assert "REDUCE" in (
            result.explanation.recommendation if result.explanation else ""
        )

    def test_high_concentration_generates_warning(self) -> None:
        engine = PortfolioEngine()
        pf = make_portfolio(
            positions=(
                make_open_position(market_value=55000.0, sector="Technology"),
                make_open_position(
                    symbol="MSFT", market_value=10000.0, sector="Technology"
                ),
            ),
            total_capital=100000.0,
        )
        td = make_trade_decision()
        ra = make_risk_analysis()

        result = engine.analyze(
            trade_decision=td,
            risk_analysis=ra,
            portfolio=pf,
        )

        sector_warnings = [w for w in result.warnings if "concentration" in w.lower()]
        assert len(sector_warnings) > 0

    def test_evidence_generated(self) -> None:
        engine = PortfolioEngine()
        pf = make_portfolio()
        td = make_trade_decision()
        ra = make_risk_analysis()

        result = engine.analyze(
            trade_decision=td,
            risk_analysis=ra,
            portfolio=pf,
        )

        evidence = result.evidence
        assert evidence is not None
        assert evidence.source == "PortfolioIntelligence"
        assert evidence.category == EvidenceCategory.PORTFOLIO
        assert isinstance(evidence.score, Score)
        assert isinstance(evidence.confidence, Confidence)

    def test_invalid_input_trade_decision(self) -> None:
        engine = PortfolioEngine()
        with pytest.raises(
            PortfolioInputError, match="trade_decision must be a TradeDecision"
        ):
            engine.analyze(
                trade_decision="invalid",  # type: ignore[arg-type]
                risk_analysis=make_risk_analysis(),
                portfolio=make_portfolio(),
            )

    def test_invalid_input_portfolio(self) -> None:
        engine = PortfolioEngine()
        td = make_trade_decision()
        with pytest.raises(
            PortfolioInputError, match="portfolio must be an ExistingPortfolio"
        ):
            engine.analyze(
                trade_decision=td,
                risk_analysis=make_risk_analysis(),
                portfolio="invalid",  # type: ignore[arg-type]
            )

    def test_negative_capital_raises_error(self) -> None:
        engine = PortfolioEngine()
        td = make_trade_decision()
        ra = make_risk_analysis()
        pf = make_portfolio(total_capital=-100.0)
        with pytest.raises(
            PortfolioInputError, match="Total capital cannot be negative"
        ):
            engine.analyze(
                trade_decision=td,
                risk_analysis=ra,
                portfolio=pf,
            )

    def test_score_band_thresholds(self) -> None:
        engine = PortfolioEngine()
        pf = make_portfolio(total_capital=100000.0)
        td = make_trade_decision()
        ra = make_risk_analysis()

        result = engine.analyze(trade_decision=td, risk_analysis=ra, portfolio=pf)
        assert result.portfolio_band == PortfolioScoreBand.EXCELLENT

    def test_metadata_contains_symbol(self) -> None:
        engine = PortfolioEngine()
        pf = make_portfolio()
        td = make_trade_decision(symbol="AAPL")
        ra = make_risk_analysis()

        result = engine.analyze(
            trade_decision=td,
            risk_analysis=ra,
            portfolio=pf,
        )
        assert "trade_symbol" in result.metadata
        assert result.metadata["trade_symbol"] == "AAPL"
        assert "sub_engines" in result.metadata
        assert len(result.metadata["sub_engines"]) == 5

    def test_full_portfolio_pipeline(self) -> None:
        engine = PortfolioEngine()
        pf = make_simple_portfolio()
        td = make_trade_decision()
        ra = make_risk_analysis()

        result = engine.analyze(
            trade_decision=td,
            risk_analysis=ra,
            portfolio=pf,
        )

        assert isinstance(result, PortfolioAnalysis)
        assert result.snapshot.position_count == 3
        assert result.exposure.net_delta is None
        sectors = result.sector_exposures
        assert len(sectors) == 1
        assert sectors[0].sector == "Technology"
        assert result.correlation.overall_correlation_level == CorrelationLevel.EXTREME
        assert result.portfolio_score > 0.0
        assert result.explanation is not None
        assert "3 position" in result.explanation.portfolio_summary


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestEdgeCases:
    def test_single_position_portfolio(self) -> None:
        analyzer = PositionAnalyzer()
        pf = make_portfolio(
            positions=(make_open_position(market_value=50000.0),),
            total_capital=100000.0,
        )
        snap = analyzer.analyze(pf)
        assert snap.position_count == 1
        assert snap.utilization == 0.5

    def test_zero_total_capital(self) -> None:
        analyzer = PositionAnalyzer()
        pf = make_portfolio(total_capital=0.0)
        snap = analyzer.analyze(pf)
        assert snap.utilization == 0.0

    def test_hedging_analyzer_no_positions(self) -> None:
        from titan.portfolio.models import PortfolioSnapshot

        analyzer = HedgingAnalyzer()
        pf = make_portfolio()
        snap = PortfolioSnapshot()
        exp = PortfolioExposure()
        corr = CorrelationAnalysis()
        result = analyzer.analyze(pf, snap, exp, corr)
        assert result.action == HedgingAction.NO_HEDGE_REQUIRED
        assert "No open positions" in result.reason
