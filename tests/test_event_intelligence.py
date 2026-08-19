"""Tests for Event Intelligence Foundation (M4.1.1)."""

from datetime import UTC, datetime, timedelta

import pytest

from titan.core.evidence import (
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
)
from titan.events import (
    AssetClass,
    CorporateEvent,
    CorporateEventAnalyzer,
    CorporateEventType,
    DecisionContext,
    EconomicCalendarAnalyzer,
    EconomicEvent,
    EconomicEventType,
    EventAnalysis,
    EventExplanation,
    EventImpact,
    EventImportance,
    EventIntelligenceAnalyzer,
    EventRisk,
    EventRiskAnalyzer,
    EventRiskAssessment,
    ImpactAnalyzer,
)

NOW = datetime.now(UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_economic(
    event_type: EconomicEventType = EconomicEventType.FOMC,
    importance: EventImportance = EventImportance.MEDIUM,
    days_from_now: int = 7,
    country: str = "US",
    previous: float | None = None,
    forecast: float | None = None,
) -> EconomicEvent:
    return EconomicEvent(
        event_type=event_type,
        timestamp=NOW + timedelta(days=days_from_now),
        importance=importance,
        description=f"{event_type.value} release",
        country=country,
        previous=previous,
        forecast=forecast,
    )


def make_corporate(
    event_type: CorporateEventType = CorporateEventType.QUARTERLY_RESULTS,
    importance: EventImportance = EventImportance.MEDIUM,
    days_from_now: int = 14,
    company: str = "TESTCORP",
) -> CorporateEvent:
    return CorporateEvent(
        event_type=event_type,
        timestamp=NOW + timedelta(days=days_from_now),
        company=company,
        importance=importance,
        description=f"{company} {event_type.value}",
    )


# ===========================================================================
# EconomicCalendarAnalyzer Tests
# ===========================================================================


class TestEconomicCalendarAnalyzer:
    def test_no_events(self) -> None:
        analyzer = EconomicCalendarAnalyzer()
        events, importance, confidence, reasons = analyzer.analyze(())
        assert events == ()
        assert importance is EventImportance.LOW
        assert confidence == 0.0
        assert "No economic events" in reasons[0]

    def test_single_event(self) -> None:
        analyzer = EconomicCalendarAnalyzer()
        event = make_economic(EconomicEventType.GDP)
        events, importance, confidence, _reasons = analyzer.analyze((event,))
        assert len(events) == 1
        assert events[0].importance is EventImportance.HIGH
        assert importance is EventImportance.HIGH
        assert confidence > 0.0

    def test_multiple_events(self) -> None:
        analyzer = EconomicCalendarAnalyzer()
        events = (
            make_economic(EconomicEventType.CPI),
            make_economic(EconomicEventType.NFP),
            make_economic(EconomicEventType.PMI, days_from_now=3),
        )
        sorted_events, importance, confidence, _reasons = analyzer.analyze(events)
        assert len(sorted_events) == 3
        assert importance is EventImportance.CRITICAL  # NFP is critical
        assert confidence > 0.0

    def test_importance_critical_events(self) -> None:
        for etype in (
            EconomicEventType.FOMC,
            EconomicEventType.NFP,
            EconomicEventType.RBI_POLICY,
            EconomicEventType.INTEREST_RATE_DECISION,
        ):
            event = make_economic(etype)
            imp = EconomicCalendarAnalyzer.importance_for(event)
            assert imp is EventImportance.CRITICAL, f"{etype} should be CRITICAL"

    def test_importance_high_events(self) -> None:
        for etype in (
            EconomicEventType.GDP,
            EconomicEventType.CPI,
            EconomicEventType.PPI,
        ):
            event = make_economic(etype)
            imp = EconomicCalendarAnalyzer.importance_for(event)
            assert imp is EventImportance.HIGH, f"{etype} should be HIGH"

    def test_importance_low_holiday(self) -> None:
        event = make_economic(EconomicEventType.HOLIDAY)
        imp = EconomicCalendarAnalyzer.importance_for(event)
        assert imp is EventImportance.LOW

    def test_importance_override(self) -> None:
        event = make_economic(EconomicEventType.PMI, importance=EventImportance.LOW)
        imp = EconomicCalendarAnalyzer.importance_for(event)
        assert imp is EventImportance.LOW  # explicit LOW should be preserved

    def test_reasons_included(self) -> None:
        analyzer = EconomicCalendarAnalyzer()
        events = (
            make_economic(EconomicEventType.FOMC),
            make_economic(EconomicEventType.GDP, days_from_now=5),
        )
        _, _, _, reasons = analyzer.analyze(events)
        assert any("Critical" in r for r in reasons)

    def test_confidence_scaling(self) -> None:
        analyzer = EconomicCalendarAnalyzer()
        events_1 = (make_economic(EconomicEventType.CPI),)
        _, _, conf_1, _ = analyzer.analyze(events_1)
        events_5 = tuple(
            make_economic(EconomicEventType.PMI, days_from_now=i) for i in range(5)
        )
        _, _, conf_5, _ = analyzer.analyze(events_5)
        assert conf_5 >= conf_1


# ===========================================================================
# CorporateEventAnalyzer Tests
# ===========================================================================


class TestCorporateEventAnalyzer:
    def test_no_events(self) -> None:
        analyzer = CorporateEventAnalyzer()
        events, importance, confidence, reasons = analyzer.analyze(())
        assert events == ()
        assert importance is EventImportance.LOW
        assert confidence == 0.0
        assert "No corporate events" in reasons[0]

    def test_single_event(self) -> None:
        analyzer = CorporateEventAnalyzer()
        event = make_corporate(CorporateEventType.DIVIDEND)
        events, importance, confidence, _reasons = analyzer.analyze((event,))
        assert len(events) == 1
        assert importance is EventImportance.MEDIUM
        assert confidence > 0.0

    def test_multiple_events(self) -> None:
        analyzer = CorporateEventAnalyzer()
        events = (
            make_corporate(CorporateEventType.QUARTERLY_RESULTS),
            make_corporate(CorporateEventType.BUYBACK),
            make_corporate(CorporateEventType.SPLIT, days_from_now=5),
        )
        sorted_events, importance, confidence, _reasons = analyzer.analyze(events)
        assert len(sorted_events) == 3
        assert importance is EventImportance.CRITICAL
        assert confidence > 0.0

    def test_importance_critical_events(self) -> None:
        for etype in (
            CorporateEventType.QUARTERLY_RESULTS,
            CorporateEventType.MERGER,
            CorporateEventType.ACQUISITION,
            CorporateEventType.BUYBACK,
        ):
            event = make_corporate(etype)
            imp = CorporateEventAnalyzer.importance_for(event)
            assert imp is EventImportance.CRITICAL, f"{etype} should be CRITICAL"

    def test_importance_high_events(self) -> None:
        for etype in (
            CorporateEventType.GUIDANCE,
            CorporateEventType.PROMOTER_ACTIVITY,
            CorporateEventType.BLOCK_DEAL,
            CorporateEventType.RIGHTS_ISSUE,
        ):
            event = make_corporate(etype)
            imp = CorporateEventAnalyzer.importance_for(event)
            assert imp is EventImportance.HIGH, f"{etype} should be HIGH"

    def test_importance_medium_events(self) -> None:
        for etype in (
            CorporateEventType.DIVIDEND,
            CorporateEventType.BONUS,
            CorporateEventType.SPLIT,
        ):
            event = make_corporate(etype)
            imp = CorporateEventAnalyzer.importance_for(event)
            assert imp is EventImportance.MEDIUM, f"{etype} should be MEDIUM"

    def test_importance_override(self) -> None:
        event = make_corporate(
            CorporateEventType.DIVIDEND, importance=EventImportance.CRITICAL
        )
        imp = CorporateEventAnalyzer.importance_for(event)
        assert imp is EventImportance.CRITICAL

    def test_reasons_included(self) -> None:
        analyzer = CorporateEventAnalyzer()
        events = (make_corporate(CorporateEventType.QUARTERLY_RESULTS),)
        _, _, _, reasons = analyzer.analyze(events)
        assert len(reasons) >= 2


# ===========================================================================
# ImpactAnalyzer Tests
# ===========================================================================


class TestImpactAnalyzer:
    def test_no_events(self) -> None:
        analyzer = ImpactAnalyzer()
        impact = analyzer.analyze()
        assert impact.expected_volatility == 0.0
        assert impact.expected_liquidity == 0.0
        assert impact.expected_gap_risk == 0.0
        assert impact.affected_asset_class is AssetClass.BROAD

    def test_economic_event_impact(self) -> None:
        analyzer = ImpactAnalyzer()
        events = (make_economic(EconomicEventType.FOMC),)
        impact = analyzer.analyze(economic_events=events)
        assert impact.expected_volatility > 0.5
        assert impact.expected_gap_risk > 0.5
        assert impact.affected_asset_class is AssetClass.CURRENCY

    def test_corporate_event_impact(self) -> None:
        analyzer = ImpactAnalyzer()
        events = (make_corporate(CorporateEventType.QUARTERLY_RESULTS),)
        impact = analyzer.analyze(corporate_events=events)
        assert impact.expected_volatility > 0.5
        assert impact.affected_asset_class is AssetClass.EQUITY
        assert impact.affected_sector != ""

    def test_mixed_events_highest_importance_wins(self) -> None:
        analyzer = ImpactAnalyzer()
        eco = (make_economic(EconomicEventType.CPI),)
        corp = (make_corporate(CorporateEventType.DIVIDEND),)
        impact = analyzer.analyze(economic_events=eco, corporate_events=corp)
        # CPI is HIGH impact
        assert impact.expected_volatility > 0.5

    def test_low_importance_impact(self) -> None:
        analyzer = ImpactAnalyzer()
        event = make_economic(EconomicEventType.HOLIDAY)
        impact = analyzer.analyze(economic_events=(event,))
        assert impact.expected_volatility <= 0.2

    def test_affected_sector_from_corporate(self) -> None:
        analyzer = ImpactAnalyzer()
        corp = (make_corporate(CorporateEventType.QUARTERLY_RESULTS, company="BANK"),)
        impact = analyzer.analyze(corporate_events=corp)
        assert "BANK" in impact.affected_sector

    def test_multiple_events_volatility(self) -> None:
        analyzer = ImpactAnalyzer()
        events = (
            make_economic(EconomicEventType.FOMC),
            make_economic(EconomicEventType.NFP, days_from_now=3),
        )
        impact = analyzer.analyze(economic_events=events)
        # Both CRITICAL -> high vol
        assert impact.expected_volatility >= 0.7


# ===========================================================================
# EventRiskAnalyzer Tests
# ===========================================================================


class TestEventRiskAnalyzer:
    def test_no_events(self) -> None:
        analyzer = EventRiskAnalyzer()
        risk = analyzer.analyze()
        assert risk.risk_level is EventRisk.LOW
        assert risk.confidence == 0.0

    def test_low_importance_risk(self) -> None:
        analyzer = EventRiskAnalyzer()
        events = (make_economic(EconomicEventType.HOLIDAY),)
        risk = analyzer.analyze(economic_events=events)
        assert risk.risk_level is EventRisk.LOW

    def test_medium_importance_risk(self) -> None:
        analyzer = EventRiskAnalyzer()
        events = (make_economic(EconomicEventType.PMI),)
        risk = analyzer.analyze(economic_events=events)
        # PMI is HIGH importance level -> risk should be at least MODERATE
        assert risk.risk_level in (EventRisk.HIGH, EventRisk.MODERATE)

    def test_critical_importance_risk(self) -> None:
        analyzer = EventRiskAnalyzer()
        events = (make_economic(EconomicEventType.FOMC),)
        risk = analyzer.analyze(economic_events=events)
        assert risk.risk_level is EventRisk.EXTREME

    def test_corporate_event_risk(self) -> None:
        analyzer = EventRiskAnalyzer()
        events = (make_corporate(CorporateEventType.QUARTERLY_RESULTS),)
        risk = analyzer.analyze(corporate_events=events)
        assert risk.risk_level is EventRisk.EXTREME

    def test_mixed_events_risk(self) -> None:
        analyzer = EventRiskAnalyzer()
        eco = (make_economic(EconomicEventType.CPI),)
        corp = (make_corporate(CorporateEventType.DIVIDEND),)
        risk = analyzer.analyze(economic_events=eco, corporate_events=corp)
        # CPI is HIGH
        assert risk.risk_level is EventRisk.HIGH

    def test_risk_dimensions_from_impact(self) -> None:
        analyzer = EventRiskAnalyzer()
        impact = EventImpact(
            expected_volatility=0.8,
            expected_liquidity=0.3,
            expected_gap_risk=0.7,
        )
        events = (make_economic(EconomicEventType.FOMC),)
        risk = analyzer.analyze(impact=impact, economic_events=events)
        assert risk.gap_risk is EventRisk.EXTREME
        assert risk.volatility_risk is EventRisk.HIGH
        assert risk.liquidity_risk is EventRisk.HIGH

    def test_confidence_scales_with_events(self) -> None:
        analyzer = EventRiskAnalyzer()
        risk_0 = analyzer.analyze()
        risk_1 = analyzer.analyze(
            economic_events=(make_economic(EconomicEventType.CPI),)
        )
        risk_3 = analyzer.analyze(
            economic_events=(
                make_economic(EconomicEventType.CPI),
                make_economic(EconomicEventType.PMI, days_from_now=5),
                make_economic(EconomicEventType.GDP, days_from_now=10),
            )
        )
        assert risk_0.confidence == 0.0
        assert risk_1.confidence > 0.0
        assert risk_3.confidence >= risk_1.confidence


# ===========================================================================
# EventIntelligenceAnalyzer Tests
# ===========================================================================


class TestEventIntelligenceAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        result = analyzer.analyze()
        assert result.confidence == 0.0
        assert "No events provided" in result.warnings[0]
        assert result.highest_importance is EventImportance.LOW
        assert result.overall_risk is EventRisk.LOW

    def test_single_economic_event(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert len(result.economic_events) == 1
        assert result.highest_importance is EventImportance.CRITICAL
        assert result.confidence > 0.0

    def test_single_corporate_event(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_corporate(CorporateEventType.MERGER)
        result = analyzer.analyze(corporate_events=(event,))
        assert len(result.corporate_events) == 1
        assert result.highest_importance is EventImportance.CRITICAL
        assert result.confidence > 0.0

    def test_mixed_events(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        eco = (make_economic(EconomicEventType.NFP),)
        corp = (make_corporate(CorporateEventType.DIVIDEND),)
        result = analyzer.analyze(economic_events=eco, corporate_events=corp)
        assert len(result.economic_events) == 1
        assert len(result.corporate_events) == 1
        assert result.highest_importance is EventImportance.CRITICAL

    def test_decision_context_critical(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert result.decision_context is not None
        assert result.decision_context.avoid_new_positions is True
        assert result.decision_context.reduce_position_size is True
        assert result.decision_context.expect_high_volatility is True
        assert result.decision_context.expect_gap_open is True
        assert result.decision_context.allow_intraday_only is True

    def test_decision_context_low_importance(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.HOLIDAY)
        result = analyzer.analyze(economic_events=(event,))
        assert result.decision_context is not None
        assert result.decision_context.avoid_new_positions is False
        assert result.decision_context.reduce_position_size is False

    def test_decision_context_high_risk_no_gap(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.GDP)
        result = analyzer.analyze(economic_events=(event,))
        assert result.decision_context is not None
        assert result.decision_context.avoid_new_positions is True
        # GDP has expected_gap_risk 0.55 from impact -> gap risk triggers
        assert result.decision_context.expect_gap_open is True

    def test_evidence_generated(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert result.evidence is not None
        assert isinstance(result.evidence, Evidence)

    def test_evidence_category(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert result.evidence is not None
        assert result.evidence.category is EvidenceCategory.EVENT

    def test_evidence_source(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert result.evidence is not None
        assert result.evidence.source == "Event Intelligence"

    def test_evidence_signal_critical(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert result.evidence is not None
        assert result.evidence.signal is EvidenceSignal.VERY_BEARISH

    def test_evidence_signal_low_importance(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.HOLIDAY)
        result = analyzer.analyze(economic_events=(event,))
        assert result.evidence is not None
        assert result.evidence.signal is EvidenceSignal.NEUTRAL

    def test_evidence_score(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert result.evidence is not None
        assert 0 <= float(result.evidence.score) <= 100

    def test_evidence_score_low_importance(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.HOLIDAY)
        result = analyzer.analyze(economic_events=(event,))
        assert result.evidence is not None
        # LOW importance -> neutral base 50
        assert float(result.evidence.score) >= 50.0

    def test_evidence_reasons(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert result.evidence is not None
        assert len(result.evidence.reasons) >= 2

    def test_explanation_generated(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert result.explanation is not None
        assert isinstance(result.explanation, EventExplanation)

    def test_explanation_sections(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert result.explanation is not None
        assert result.explanation.upcoming_events != ""
        assert result.explanation.importance != ""
        assert result.explanation.market_impact != ""
        assert result.explanation.risk_assessment != ""
        assert result.explanation.trading_implications != ""
        assert result.explanation.overall_assessment != ""

    def test_warnings_no_eco_no_corp(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        result = analyzer.analyze(economic_events=(), corporate_events=())
        assert "No events provided" in result.warnings[0]

    def test_warnings_missing_type(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        eco = (make_economic(EconomicEventType.CPI),)
        result = analyzer.analyze(economic_events=eco)
        assert any("No corporate events" in w for w in result.warnings)

    def test_metadata_present(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert "analyzer" in result.metadata
        assert result.metadata["analyzer"] == "EventIntelligenceAnalyzer"
        assert result.metadata["economic_event_count"] == 1

    def test_neutral_placeholder(self) -> None:
        placeholder = EventAnalysis.neutral_placeholder()
        assert placeholder.confidence == 0.0
        assert "unavailable" in placeholder.warnings[0]
        assert placeholder.highest_importance is EventImportance.LOW
        assert placeholder.overall_risk is EventRisk.LOW

    def test_empty_analysis(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        result = analyzer.analyze()
        assert result.highest_importance is EventImportance.LOW
        assert result.overall_risk is EventRisk.LOW
        assert result.explanation is not None
        assert "no events provided" in result.explanation.upcoming_events.lower()


# ===========================================================================
# Validation Tests
# ===========================================================================


class TestValidation:
    def test_event_analysis_frozen(self) -> None:
        analysis = EventAnalysis()
        with pytest.raises(AttributeError):
            analysis.confidence = 0.5  # type: ignore[misc]

    def test_decision_context_frozen(self) -> None:
        ctx = DecisionContext()
        with pytest.raises(AttributeError):
            ctx.avoid_new_positions = True  # type: ignore[misc]

    def test_event_impact_frozen(self) -> None:
        impact = EventImpact()
        with pytest.raises(AttributeError):
            impact.expected_volatility = 0.5  # type: ignore[misc]

    def test_event_risk_assessment_frozen(self) -> None:
        risk = EventRiskAssessment()
        with pytest.raises(AttributeError):
            risk.risk_level = EventRisk.HIGH  # type: ignore[misc]

    def test_economic_event_frozen(self) -> None:
        event = make_economic()
        with pytest.raises(AttributeError):
            event.country = "IN"  # type: ignore[misc]

    def test_corporate_event_frozen(self) -> None:
        event = make_corporate()
        with pytest.raises(AttributeError):
            event.company = "OTHER"  # type: ignore[misc]

    def test_event_explanation_frozen(self) -> None:
        explanation = EventExplanation()
        with pytest.raises(AttributeError):
            explanation.upcoming_events = "test"  # type: ignore[misc]

    def test_economic_event_defaults(self) -> None:
        event = EconomicEvent(
            event_type=EconomicEventType.GDP,
            timestamp=NOW,
        )
        assert event.importance is EventImportance.MEDIUM
        assert event.country == ""
        assert event.previous is None

    def test_corporate_event_defaults(self) -> None:
        event = CorporateEvent(
            event_type=CorporateEventType.DIVIDEND,
            timestamp=NOW,
        )
        assert event.importance is EventImportance.MEDIUM
        assert event.company == ""
        assert event.description == ""

    def test_decision_context_defaults(self) -> None:
        ctx = DecisionContext()
        assert ctx.avoid_new_positions is False
        assert ctx.reduce_position_size is False
        assert ctx.expect_high_volatility is False
        assert ctx.expect_gap_open is False
        assert ctx.allow_intraday_only is False
        assert ctx.confidence == 0.0

    def test_event_impact_defaults(self) -> None:
        impact = EventImpact()
        assert impact.expected_volatility == 0.0
        assert impact.expected_liquidity == 0.0
        assert impact.expected_gap_risk == 0.0
        assert impact.affected_asset_class is AssetClass.BROAD
        assert impact.affected_sector == ""
        assert impact.expected_duration == ""

    def test_event_risk_assessment_defaults(self) -> None:
        risk = EventRiskAssessment()
        assert risk.risk_level is EventRisk.MODERATE
        assert risk.gap_risk is EventRisk.MODERATE
        assert risk.volatility_risk is EventRisk.MODERATE
        assert risk.liquidity_risk is EventRisk.MODERATE
        assert risk.confidence == 0.0

    def test_event_analysis_defaults(self) -> None:
        analysis = EventAnalysis()
        assert analysis.economic_events == ()
        assert analysis.corporate_events == ()
        assert analysis.highest_importance is EventImportance.LOW
        assert analysis.overall_risk is EventRisk.LOW
        assert analysis.decision_context is None
        assert analysis.confidence == 0.0
        assert analysis.evidence is None
        assert analysis.explanation is None


# ===========================================================================
# Edge Case Tests
# ===========================================================================


class TestEdgeCases:
    def test_economic_only_no_impact(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        result = analyzer.analyze(
            economic_events=(make_economic(EconomicEventType.HOLIDAY),)
        )
        assert result.decision_context is not None
        assert result.decision_context.avoid_new_positions is False

    def test_corporate_only_no_impact(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        result = analyzer.analyze(
            corporate_events=(make_corporate(CorporateEventType.SPLIT),)
        )
        assert result.decision_context is not None
        assert result.decision_context.confidence > 0.0

    def test_multiple_economic_sorted_by_importance(self) -> None:
        analyzer = EconomicCalendarAnalyzer()
        events = (
            make_economic(EconomicEventType.PMI),
            make_economic(EconomicEventType.FOMC, days_from_now=10),
            make_economic(EconomicEventType.HOLIDAY, days_from_now=1),
        )
        sorted_events, _, _, _ = analyzer.analyze(events)
        # FOMC (CRITICAL) should be first, then PMI (HIGH), then HOLIDAY (LOW)
        assert sorted_events[0].event_type is EconomicEventType.FOMC
        assert sorted_events[1].event_type is EconomicEventType.PMI
        assert sorted_events[2].event_type is EconomicEventType.HOLIDAY

    def test_economic_event_with_previous_forecast(self) -> None:
        event = EconomicEvent(
            event_type=EconomicEventType.CPI,
            timestamp=NOW + timedelta(days=3),
            previous=5.2,
            forecast=5.0,
            country="US",
        )
        assert event.previous == 5.2
        assert event.forecast == 5.0
        assert event.actual is None

    def test_multiple_risk_levels_from_impact(self) -> None:
        analyzer = EventRiskAnalyzer()
        impact = EventImpact(
            expected_volatility=0.3,
            expected_liquidity=0.8,
            expected_gap_risk=0.2,
        )
        events = (make_economic(EconomicEventType.PMI),)
        risk = analyzer.analyze(impact=impact, economic_events=events)
        assert risk.volatility_risk is EventRisk.LOW
        assert risk.liquidity_risk is EventRisk.LOW
        assert risk.gap_risk is EventRisk.LOW

    def test_decision_context_no_gap_risk(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.CPI)
        result = analyzer.analyze(economic_events=(event,))
        assert result.decision_context is not None
        # CPI is HIGH importance -> triggers avoid_new_positions
        assert result.decision_context.avoid_new_positions is True

    def test_evidence_weight_default(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert result.evidence is not None
        assert result.evidence.weight == 1.0

    def test_evidence_timestamp(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        event = make_economic(EconomicEventType.FOMC)
        result = analyzer.analyze(economic_events=(event,))
        assert result.evidence is not None
        assert result.evidence.timestamp is not None

    def test_events_in_past(self) -> None:
        analyzer = EconomicCalendarAnalyzer()
        past_event = EconomicEvent(
            event_type=EconomicEventType.PMI,
            timestamp=NOW - timedelta(days=1),
        )
        events, _, confidence, _ = analyzer.analyze((past_event,))
        assert len(events) == 1
        assert confidence == 0.0  # no upcoming events

    def test_mixed_events_highest_importance_critical(self) -> None:
        analyzer = EventIntelligenceAnalyzer()
        eco = (make_economic(EconomicEventType.GDP),)
        corp = (make_corporate(CorporateEventType.QUARTERLY_RESULTS),)
        result = analyzer.analyze(economic_events=eco, corporate_events=corp)
        # Both CRITICAL
        assert result.highest_importance is EventImportance.CRITICAL
