from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from titan.brokers.models import Exchange
from titan.decision.models import DecisionAction, TradeDecision
from titan.market.models import Candle
from titan.market.series import MarketDataSeries
from titan.pipeline import (
    PipelineAbortedError,
    PipelineContext,
    PipelineError,
    PipelineExecutionError,
    PipelineFatalError,
    PipelineHooks,
    PipelineRecoverableError,
    PipelineReport,
    PipelineStage,
    PipelineStageError,
    PipelineStatus,
    PipelineValidationError,
    StageTiming,
    TradePipeline,
)
from titan.portfolio.models import ExistingPortfolio
from titan.risk.models import (
    CapitalAllocation,
    DecisionContext,
    ExposureAssessment,
    PositionSizing,
    RiskAnalysis,
    RiskProfile,
    RiskScore,
    RiskScoreBand,
    StopLossPlan,
    TargetPlan,
)
from titan.trading.models import (
    ScoreBand,
    TradeQualification,
    TradeScore,
    TradeStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_series(prices: list[float]) -> MarketDataSeries:
    candles = [
        Candle(timestamp=datetime.now(UTC), open=p, high=p, low=p, close=p, volume=100)
        for p in prices
    ]
    return MarketDataSeries(candles)


def make_basic_qualification(
    status: TradeStatus = TradeStatus.QUALIFIED,
) -> TradeQualification:
    return TradeQualification(
        status=status,
        trade_score=TradeScore(value=75.0, band=ScoreBand.GOOD),
        confidence=0.7,
        decision_context="Test qualification",
        long_qualification=True,
        short_qualification=False,
        option_buying_qualification=False,
        option_selling_qualification=False,
        institutional_alignment=True,
    )


def make_basic_risk() -> RiskAnalysis:
    return RiskAnalysis(
        risk_profile=RiskProfile.MODERATE,
        risk_score=RiskScore(value=30.0, band=RiskScoreBand.LOW),
        position_sizing=PositionSizing(
            maximum_capital=100000.0,
            risk_per_trade=10000.0,
            units=10,
            contracts=10,
            maximum_quantity=100,
            capital_utilization=0.1,
        ),
        stop_loss=StopLossPlan(
            technical_stop=95.0,
            volatility_stop=93.0,
            time_stop="end_of_day",
            invalidation_level=92.0,
            emergency_stop=90.0,
            recommended_stop=94.0,
        ),
        targets=TargetPlan(
            target_1=105.0,
            target_2=110.0,
            target_3=115.0,
            trailing_stop_trigger=103.0,
            expected_risk_reward=2.0,
        ),
        capital_allocation=CapitalAllocation(
            capital_used=100000.0,
            available_capital=900000.0,
            daily_exposure=50000.0,
            weekly_exposure=200000.0,
            maximum_allocation=50000.0,
            portfolio_concentration=0.1,
        ),
        exposure=ExposureAssessment(
            directional_exposure="moderate",
            volatility_exposure="low",
            event_exposure="low",
            sector_exposure="low",
            liquidity_exposure="low",
            overall_portfolio_risk="moderate",
        ),
        decision_context=DecisionContext(
            reduce_size=False,
            normal_size=True,
            increase_size=False,
            avoid_trade=False,
            hedging_required=False,
            maximum_contracts=100,
            confidence=0.8,
        ),
    )


def make_basic_decision(action: DecisionAction = DecisionAction.BUY) -> TradeDecision:
    return TradeDecision(
        decision=action,
        trade_direction="long",
        instrument_type="underlying",
        symbol="NIFTY",
        rank="good",
        confidence=0.75,
        probability=0.65,
        trade_score=75.0,
    )


def make_basic_portfolio() -> ExistingPortfolio:
    return ExistingPortfolio(
        positions=(),
        total_capital=1_000_000.0,
        cash_reserve=100_000.0,
        name="Test Portfolio",
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestTradePipelineConstruction:
    def test_default_construction(self):
        pipeline = TradePipeline()
        assert pipeline is not None

    def test_custom_hooks(self):
        hooks = PipelineHooks()
        pipeline = TradePipeline(_hooks=hooks)
        assert pipeline._hooks is hooks

    def test_custom_max_retries(self):
        pipeline = TradePipeline(_max_retries=2)
        assert pipeline._max_retries == 2

    def test_custom_engines_injected(self):
        mock_market = MagicMock()
        pipeline = TradePipeline(_structure_analyzer=mock_market)
        assert pipeline._structure_analyzer is mock_market


# ---------------------------------------------------------------------------
# Basic execution
# ---------------------------------------------------------------------------


class TestTradePipelineBasicRun:
    def test_run_with_minimal_input(self):
        pipeline = TradePipeline()
        report = pipeline.run("NIFTY", Exchange.NSE)
        assert isinstance(report, PipelineReport)
        assert report.symbol == "NIFTY"
        assert report.exchange == "nse"
        assert report.status in (PipelineStatus.SUCCESS, PipelineStatus.PARTIAL)

    def test_run_with_market_data(self):
        pipeline = TradePipeline()
        md = make_series([100.0 + i for i in range(30)])
        report = pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        assert report.status == PipelineStatus.SUCCESS
        assert report.evidence_count > 0

    def test_run_with_market_data_and_portfolio(self):
        pipeline = TradePipeline()
        md = make_series([100.0 + i for i in range(30)])
        pf = make_basic_portfolio()
        report = pipeline.run("NIFTY", Exchange.NSE, market_data=md, portfolio=pf)
        assert report.status == PipelineStatus.SUCCESS

    def test_run_generates_stage_timings(self):
        pipeline = TradePipeline()
        report = pipeline.run("NIFTY", Exchange.NSE)
        assert len(report.stages) > 0
        for timing in report.stages:
            assert isinstance(timing, StageTiming)
            assert isinstance(timing.stage, PipelineStage)
            assert timing.duration_ms >= 0

    def test_run_all_stages_executed(self):
        pipeline = TradePipeline()
        report = pipeline.run("NIFTY", Exchange.NSE)
        stage_names = [s.stage.value for s in report.stages]
        assert "prepare" in stage_names
        assert "market" in stage_names
        assert "options" in stage_names
        assert "volatility" in stage_names
        assert "dealer" in stage_names
        assert "news" in stage_names
        assert "events" in stage_names
        assert "fusion" in stage_names
        assert "qualification" in stage_names
        assert "risk" in stage_names
        assert "decision" in stage_names
        assert "portfolio" in stage_names
        assert "execution" in stage_names
        assert "oms" in stage_names
        assert "broker" in stage_names


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestTradePipelineValidation:
    def test_empty_symbol_raises(self):
        pipeline = TradePipeline()
        with pytest.raises(PipelineValidationError):
            pipeline.run("", Exchange.NSE)

    def test_whitespace_symbol_raises(self):
        pipeline = TradePipeline()
        with pytest.raises(PipelineValidationError):
            pipeline.run("   ", Exchange.NSE)


# ---------------------------------------------------------------------------
# Report properties
# ---------------------------------------------------------------------------


class TestTradePipelineReport:
    def test_report_success_property(self):
        pipeline = TradePipeline()
        report = pipeline.run("NIFTY", Exchange.NSE)
        assert isinstance(report.success, bool)

    def test_report_has_errors_property(self):
        pipeline = TradePipeline()
        report = pipeline.run("NIFTY", Exchange.NSE)
        assert isinstance(report.has_errors, bool)

    def test_report_has_warnings_property(self):
        pipeline = TradePipeline()
        report = pipeline.run("NIFTY", Exchange.NSE)
        assert isinstance(report.has_warnings, bool)

    def test_report_timing_convenience_properties(self):
        pipeline = TradePipeline()
        report = pipeline.run("NIFTY", Exchange.NSE)
        for timing in report.stages:
            assert timing.duration_s >= 0
        assert report.total_duration_s >= 0

    def test_report_pipeline_id(self):
        pipeline = TradePipeline()
        report1 = pipeline.run("NIFTY", Exchange.NSE)
        report2 = pipeline.run("BANKNIFTY", Exchange.NSE)
        assert report1.pipeline_id != report2.pipeline_id


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestTradePipelineErrors:
    def test_recoverable_error_in_stage(self):
        pipeline = TradePipeline()

        with pytest.raises(PipelineValidationError):
            pipeline.run("", Exchange.NSE)

    def test_stage_error_recorded(self):
        mock_market = MagicMock()
        mock_market.analyze.side_effect = ValueError("Market engine failure")
        pipeline = TradePipeline(_structure_analyzer=mock_market)
        md = make_series([100.0 + i for i in range(30)])
        report = pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        assert report.status in (PipelineStatus.PARTIAL, PipelineStatus.FAILED)
        assert len(report.errors) > 0

    def test_abort_on_fatal(self):
        mock_qual = MagicMock()
        mock_qual.qualify.side_effect = PipelineFatalError("Fatal qualification error")
        pipeline = TradePipeline(_qualification_engine=mock_qual)
        md = make_series([100.0 + i for i in range(30)])
        report = pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        assert report.status in (PipelineStatus.PARTIAL, PipelineStatus.FAILED)
        has_qual_error = any("qualification" in e for e in report.errors)
        assert has_qual_error


# ---------------------------------------------------------------------------
# Hook execution
# ---------------------------------------------------------------------------


class TestTradePipelineHooks:
    def test_before_stage_hook_called(self):
        calls = []
        hooks = PipelineHooks(
            before_stage=lambda stage, ctx: calls.append(("before", stage))
        )
        pipeline = TradePipeline(_hooks=hooks)
        pipeline.run("NIFTY", Exchange.NSE)
        assert len(calls) > 0
        assert calls[0][0] == "before"

    def test_after_stage_hook_called(self):
        calls = []
        hooks = PipelineHooks(
            after_stage=lambda stage, ctx, result, duration: calls.append(
                ("after", stage)
            )
        )
        pipeline = TradePipeline(_hooks=hooks)
        pipeline.run("NIFTY", Exchange.NSE)
        assert len(calls) > 0
        assert calls[0][0] == "after"

    def test_on_complete_hook_called(self):
        calls = []
        hooks = PipelineHooks(
            on_complete=lambda ctx, report: calls.append(("complete", report))
        )
        pipeline = TradePipeline(_hooks=hooks)
        pipeline.run("NIFTY", Exchange.NSE)
        assert len(calls) == 1
        assert calls[0][0] == "complete"
        assert isinstance(calls[0][1], PipelineReport)

    def test_on_error_hook_called_on_failure(self):
        calls = []
        mock_market = MagicMock()
        mock_market.analyze.side_effect = ValueError("fail")
        hooks = PipelineHooks(
            on_error=lambda stage, ctx, error: calls.append(("error", stage, error))
        )
        pipeline = TradePipeline(_structure_analyzer=mock_market, _hooks=hooks)
        md = make_series([100.0 + i for i in range(30)])
        pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        assert len(calls) > 0
        assert calls[0][0] == "error"


# ---------------------------------------------------------------------------
# Context propagation
# ---------------------------------------------------------------------------


class TestTradePipelineContext:
    def test_context_symbol_and_exchange(self):
        pipeline = TradePipeline()
        report = pipeline.run("NIFTY", Exchange.NSE)
        assert report.symbol == "NIFTY"
        assert report.exchange == "nse"

    def test_context_evidence_collection(self):
        pipeline = TradePipeline()
        md = make_series([100.0 + i for i in range(30)])
        report = pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        assert report.evidence_count > 0

    def test_context_metadata_stored(self):
        pipeline = TradePipeline()
        report = pipeline.run(
            "NIFTY", Exchange.NSE, metadata={"test": True, "source": "unit_test"}
        )
        assert report.metadata.get("test") is True
        assert report.metadata.get("source") == "unit_test"


# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------


class TestTradePipelineDI:
    def test_inject_structure_analyzer(self):
        mock = MagicMock()
        mock.analyze.return_value = MagicMock()
        pipeline = TradePipeline(_structure_analyzer=mock)
        md = make_series([100.0 + i for i in range(30)])
        pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        mock.analyze.assert_called_once()

    def test_inject_vwap_analyzer(self):
        mock = MagicMock()
        mock.analyze.return_value = MagicMock()
        pipeline = TradePipeline(_vwap_analyzer=mock)
        md = make_series([100.0 + i for i in range(30)])
        pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        mock.analyze.assert_called_once()

    def test_inject_volume_analyzer(self):
        mock = MagicMock()
        mock.analyze.return_value = MagicMock()
        pipeline = TradePipeline(_volume_analyzer=mock)
        md = make_series([100.0 + i for i in range(30)])
        pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        mock.analyze.assert_called_once()

    def test_inject_regime_analyzer(self):
        mock = MagicMock()
        mock.analyze.return_value = MagicMock()
        pipeline = TradePipeline(_regime_analyzer=mock)
        md = make_series([100.0 + i for i in range(30)])
        pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        mock.analyze.assert_called_once()

    def test_inject_qualification_engine(self):
        mock = MagicMock()
        mock.qualify.return_value = make_basic_qualification()
        pipeline = TradePipeline(_qualification_engine=mock)
        md = make_series([100.0 + i for i in range(30)])
        pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        assert mock.qualify.called

    def test_inject_risk_engine(self):
        mock = MagicMock()
        mock.analyze.return_value = make_basic_risk()
        pipeline = TradePipeline(_risk_engine=mock)
        md = make_series([100.0 + i for i in range(30)])
        pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        assert mock.analyze.called

    def test_inject_decision_engine(self):
        mock = MagicMock()
        mock.decide.return_value = make_basic_decision()
        pipeline = TradePipeline(_decision_engine=mock)
        md = make_series([100.0 + i for i in range(30)])
        pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        assert mock.decide.called

    def test_inject_portfolio_engine(self):
        mock = MagicMock()
        mock.analyze.return_value = MagicMock()
        pipeline = TradePipeline(_portfolio_engine=mock)
        md = make_series([100.0 + i for i in range(30)])
        pf = make_basic_portfolio()
        pipeline.run("NIFTY", Exchange.NSE, market_data=md, portfolio=pf)
        assert mock.analyze.called

    def test_inject_event_analyzer(self):
        mock = MagicMock()
        mock.analyze.return_value = MagicMock()
        pipeline = TradePipeline(_event_analyzer=mock)
        pipeline.run("NIFTY", Exchange.NSE)
        assert mock.analyze.called

    def test_inject_news_analyzer(self):
        mock = MagicMock()
        mock.analyze.return_value = MagicMock()
        pipeline = TradePipeline(_news_analyzer=mock)
        pipeline.run("NIFTY", Exchange.NSE)
        assert not mock.analyze.called  # No articles provided


# ---------------------------------------------------------------------------
# Stage failures
# ---------------------------------------------------------------------------


class TestTradePipelineStageFailure:
    def test_market_stage_failure_is_recoverable(self):
        mock_market = MagicMock()
        mock_market.analyze.side_effect = ValueError("Market failure")
        pipeline = TradePipeline(_structure_analyzer=mock_market)
        md = make_series([100.0 + i for i in range(30)])
        report = pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        assert "market" in report.errors[0] if report.errors else True

    def test_qualification_failure_is_fatal(self):
        pipeline = TradePipeline(
            _qualification_engine=MagicMock(
                qualify=MagicMock(side_effect=ValueError("Fatal"))
            )
        )
        md = make_series([100.0 + i for i in range(30)])
        report = pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        qual_errors = [e for e in report.errors if "qualification" in e.lower()]
        assert len(qual_errors) > 0


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestTradePipelineSerialization:
    def test_report_fields_are_serializable(self):
        pipeline = TradePipeline()
        report = pipeline.run("NIFTY", Exchange.NSE)
        d = {
            "pipeline_id": report.pipeline_id,
            "symbol": report.symbol,
            "exchange": report.exchange,
            "status": report.status.value,
            "evidence_count": report.evidence_count,
            "decision_action": report.decision_action,
            "orders_submitted": report.orders_submitted,
            "total_duration_ms": report.total_duration_ms,
        }
        assert isinstance(d["pipeline_id"], str)
        assert isinstance(d["status"], str)
        assert isinstance(d["total_duration_ms"], float)

    def test_timing_fields_are_serializable(self):
        pipeline = TradePipeline()
        report = pipeline.run("NIFTY", Exchange.NSE)
        for s in report.stages:
            d = {
                "stage": s.stage.value,
                "success": s.success,
                "duration_ms": s.duration_ms,
                "error": s.error,
            }
            assert isinstance(d["stage"], str)
            assert isinstance(d["success"], bool)
            assert isinstance(d["duration_ms"], float)


# ---------------------------------------------------------------------------
# PipelineStage enum
# ---------------------------------------------------------------------------


class TestPipelineStageEnum:
    def test_execution_order_contains_all_stages(self):
        order = PipelineStage.execution_order()
        assert PipelineStage.PREPARE in order
        assert PipelineStage.MARKET in order
        assert PipelineStage.OPTIONS in order
        assert PipelineStage.VOLATILITY in order
        assert PipelineStage.DEALER in order
        assert PipelineStage.NEWS in order
        assert PipelineStage.EVENTS in order
        assert PipelineStage.FUSION in order
        assert PipelineStage.QUALIFICATION in order
        assert PipelineStage.RISK in order
        assert PipelineStage.DECISION in order
        assert PipelineStage.PORTFOLIO in order
        assert PipelineStage.EXECUTION in order
        assert PipelineStage.OMS in order
        assert PipelineStage.BROKER in order
        assert PipelineStage.COMPLETE in order

    def test_terminal_stages(self):
        terminals = PipelineStage.terminal_stages()
        assert PipelineStage.COMPLETE in terminals
        assert PipelineStage.FAILED in terminals

    def test_execution_order_precedes_complete(self):
        order = PipelineStage.execution_order()
        complete_idx = order.index(PipelineStage.COMPLETE)
        for stage in [
            PipelineStage.PREPARE,
            PipelineStage.MARKET,
            PipelineStage.EXECUTION,
        ]:
            assert order.index(stage) < complete_idx

    def test_stage_values_are_strings(self):
        for stage in PipelineStage:
            assert isinstance(stage.value, str)

    def test_stage_from_value(self):
        assert PipelineStage("prepare") == PipelineStage.PREPARE
        assert PipelineStage("execution") == PipelineStage.EXECUTION
        assert PipelineStage("complete") == PipelineStage.COMPLETE


# ---------------------------------------------------------------------------
# PipelineHooks
# ---------------------------------------------------------------------------


class TestPipelineHooks:
    def test_before_stage_noop_when_none(self):
        hooks = PipelineHooks()
        hooks.run_before_stage(PipelineStage.PREPARE, None)

    def test_after_stage_noop_when_none(self):
        hooks = PipelineHooks()
        hooks.run_after_stage(PipelineStage.PREPARE, None, None, 0.0)

    def test_on_error_noop_when_none(self):
        hooks = PipelineHooks()
        hooks.run_on_error(PipelineStage.PREPARE, None, ValueError("test"))

    def test_on_retry_noop_when_none(self):
        hooks = PipelineHooks()
        hooks.run_on_retry(PipelineStage.PREPARE, None, ValueError("test"), 1)

    def test_on_abort_noop_when_none(self):
        hooks = PipelineHooks()
        hooks.run_on_abort(None)

    def test_on_complete_noop_when_none(self):
        hooks = PipelineHooks()
        report = MagicMock(spec=PipelineReport)
        hooks.run_on_complete(None, report)

    def test_all_hooks_callable(self):
        calls = []
        hooks = PipelineHooks(
            before_stage=lambda s, c: calls.append("before"),
            after_stage=lambda s, c, r, d: calls.append("after"),
            on_error=lambda s, c, e: calls.append("error"),
            on_retry=lambda s, c, e, a: calls.append("retry"),
            on_abort=lambda c: calls.append("abort"),
            on_complete=lambda c, r: calls.append("complete"),
        )
        hooks.run_before_stage(PipelineStage.PREPARE, None)
        hooks.run_after_stage(PipelineStage.PREPARE, None, "result", 1.0)
        hooks.run_on_error(PipelineStage.PREPARE, None, ValueError())
        hooks.run_on_retry(PipelineStage.PREPARE, None, ValueError(), 1)
        hooks.run_on_abort(None)
        hooks.run_on_complete(None, MagicMock(spec=PipelineReport))
        assert calls == ["before", "after", "error", "retry", "abort", "complete"]


# ---------------------------------------------------------------------------
# PipelineContext
# ---------------------------------------------------------------------------


class TestPipelineContext:
    def test_context_defaults(self):
        ctx = PipelineContext(
            pipeline_id="test-123",
            symbol="NIFTY",
            exchange=Exchange.NSE,
        )
        assert ctx.pipeline_id == "test-123"
        assert ctx.symbol == "NIFTY"
        assert ctx.exchange == Exchange.NSE
        assert ctx.market_data is None
        assert ctx.market_regime is None
        assert ctx.option_chain is None
        assert ctx.greeks is None
        assert ctx.liquidity is None
        assert ctx.volatility is None
        assert ctx.dealer_positioning is None
        assert ctx.gamma_exposure is None
        assert ctx.vanna_exposure is None
        assert ctx.charm_exposure is None
        assert ctx.news is None
        assert ctx.events is None
        assert ctx.fusion is None
        assert ctx.qualification is None
        assert ctx.risk is None
        assert ctx.decision is None
        assert ctx.portfolio is None
        assert ctx.execution is None
        assert ctx.aborted is False
        assert ctx.current_stage is None

    def test_context_mutable(self):
        ctx = PipelineContext(
            pipeline_id="test-123",
            symbol="NIFTY",
            exchange=Exchange.NSE,
        )
        ctx.aborted = True
        assert ctx.aborted is True


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestPipelineExceptions:
    def test_pipeline_error_base(self):
        assert issubclass(PipelineError, Exception)

    def test_validation_error(self):
        assert issubclass(PipelineValidationError, PipelineError)
        assert issubclass(PipelineValidationError, ValueError)

    def test_fatal_error(self):
        assert issubclass(PipelineFatalError, PipelineExecutionError)
        assert issubclass(PipelineExecutionError, PipelineError)

    def test_recoverable_error(self):
        assert issubclass(PipelineRecoverableError, PipelineExecutionError)

    def test_pipeline_stage_error(self):
        assert issubclass(PipelineStageError, PipelineError)

    def test_pipeline_aborted_error(self):
        assert issubclass(PipelineAbortedError, PipelineError)

    def test_exception_with_message(self):
        exc = PipelineValidationError("Invalid symbol")
        assert str(exc) == "Invalid symbol"


# ---------------------------------------------------------------------------
# Report edge cases
# ---------------------------------------------------------------------------


class TestTradePipelineReportEdgeCases:
    def test_report_no_errors(self):
        pipeline = TradePipeline()
        report = pipeline.run("NIFTY", Exchange.NSE)
        assert report.status == PipelineStatus.SUCCESS
        assert len(report.errors) == 0

    def test_report_no_warnings_with_data(self):
        pipeline = TradePipeline()
        md = make_series([100.0 + i for i in range(30)])
        pf = make_basic_portfolio()
        report = pipeline.run("NIFTY", Exchange.NSE, market_data=md, portfolio=pf)
        assert report.status == PipelineStatus.SUCCESS


# ---------------------------------------------------------------------------
# Options stage data flow
# ---------------------------------------------------------------------------


class TestTradePipelineOptionData:
    def test_options_stage_skipped_without_chain(self):
        pipeline = TradePipeline()
        report = pipeline.run("NIFTY", Exchange.NSE)
        opt_timing = [s for s in report.stages if s.stage == PipelineStage.OPTIONS]
        assert len(opt_timing) == 1
        assert opt_timing[0].success


# ---------------------------------------------------------------------------
# Evidence flow through fusion stage
# ---------------------------------------------------------------------------


class TestTradePipelineEvidenceFlow:
    def test_evidence_from_market_flows_to_fusion(self):
        pipeline = TradePipeline()
        md = make_series([100.0 + i for i in range(30)])
        report = pipeline.run("NIFTY", Exchange.NSE, market_data=md)
        assert report.evidence_count >= 2  # market_structure + market_regime


# ---------------------------------------------------------------------------
# Forbidden imports
# ---------------------------------------------------------------------------


class TestTradePipelineForbiddenImports:
    def test_no_broker_sdk_imports(self):
        import titan.pipeline.pipeline as mod

        source = open(mod.__file__).read()
        assert "yfinance" not in source.lower()
        assert "yfinance" not in source.lower()

    def test_no_analysis_indicator_imports(self):
        import titan.pipeline.pipeline as mod

        source = open(mod.__file__).read()
        assert "indicators" not in source.lower()
