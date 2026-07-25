from datetime import datetime

import pytest

from titan.core.evidence import EvidenceCategory, EvidenceSignal
from titan.market.intelligence.advance_decline import (
    AdvanceDeclineAnalyzer,
)
from titan.market.intelligence.breadth import BreadthAnalyzer
from titan.market.intelligence.market_participation import (
    MarketParticipationAnalyzer,
)
from titan.market.intelligence.models import (
    AdvanceDecline,
    BreadthAnalysis,
    BreadthBias,
    BreadthExplanation,
    BreadthStrength,
    MarketBreadthSnapshot,
    MarketParticipation,
    SectorBreadth,
    SectorBreadthSnapshot,
)
from titan.market.intelligence.sector_breadth import (
    SectorBreadthAnalyzer,
)

NOW = datetime(2026, 7, 2, 15, 30)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_snapshot(
    advances: int = 0,
    declines: int = 0,
    unchanged: int = 0,
    total: int | None = None,
    sectors: tuple[SectorBreadthSnapshot, ...] | None = None,
) -> MarketBreadthSnapshot:
    total_syms = total if total is not None else advances + declines + unchanged
    return MarketBreadthSnapshot(
        timestamp=NOW,
        index_name="TEST",
        advances=advances,
        declines=declines,
        unchanged=unchanged,
        total_symbols=total_syms,
        sector_summaries=sectors or (),
    )


def make_sector(
    name: str,
    advances: int = 0,
    declines: int = 0,
    unchanged: int = 0,
    weight: float = 0.0,
) -> SectorBreadthSnapshot:
    return SectorBreadthSnapshot(
        sector_name=name,
        advances=advances,
        declines=declines,
        unchanged=unchanged,
        weight=weight,
    )


# ---------------------------------------------------------------------------
# AdvanceDeclineAnalyzer unit tests
# ---------------------------------------------------------------------------


class TestAdvanceDeclineAnalyzer:
    def test_insufficient_data(self) -> None:
        snap = make_snapshot(advances=2, declines=2, unchanged=0, total=4)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert result.confidence == 0.0
        assert "Insufficient data" in result.reasons[0]

    def test_healthy_breadth(self) -> None:
        snap = make_snapshot(advances=800, declines=200, unchanged=50, total=1050)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert result.ad_ratio == pytest.approx(4.0, abs=0.01)
        assert result.breadth_strength is BreadthStrength.VERY_STRONG
        assert result.advance_dominance is True

    def test_weak_breadth(self) -> None:
        snap = make_snapshot(advances=150, declines=850, unchanged=50, total=1050)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert result.breadth_strength is BreadthStrength.VERY_WEAK
        assert result.decline_dominance is True

    def test_neutral_breadth(self) -> None:
        snap = make_snapshot(advances=500, declines=500, unchanged=50, total=1050)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert result.breadth_strength is BreadthStrength.NEUTRAL
        assert result.ad_ratio == pytest.approx(1.0, abs=0.01)

    def test_strong_breadth(self) -> None:
        snap = make_snapshot(advances=600, declines=400, unchanged=50, total=1050)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert result.breadth_strength is BreadthStrength.STRONG

    def test_weak_breadth_classification(self) -> None:
        snap = make_snapshot(advances=350, declines=650, unchanged=50, total=1050)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert result.breadth_strength is BreadthStrength.WEAK

    def test_zero_declines(self) -> None:
        snap = make_snapshot(advances=500, declines=0, unchanged=0, total=500)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert result.ad_ratio == 500.0
        assert result.advance_dominance is True

    def test_zero_advances(self) -> None:
        snap = make_snapshot(advances=0, declines=500, unchanged=0, total=500)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert result.ad_ratio == 0.0
        assert result.decline_dominance is True

    def test_zero_total(self) -> None:
        snap = make_snapshot(advances=0, declines=0, unchanged=0, total=0)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert result.confidence == 0.0

    def test_advance_percentage(self) -> None:
        snap = make_snapshot(advances=250, declines=500, unchanged=250, total=1000)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert result.advance_percentage == 25.0
        assert result.decline_percentage == 50.0

    def test_reasons_include_ad_ratio(self) -> None:
        snap = make_snapshot(advances=500, declines=500, unchanged=0, total=1000)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert any("A/D ratio" in r for r in result.reasons)

    def test_reasons_include_breadth_strength(self) -> None:
        snap = make_snapshot(advances=800, declines=200, unchanged=0, total=1000)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert any("very_strong" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# SectorBreadthAnalyzer unit tests
# ---------------------------------------------------------------------------


class TestSectorBreadthAnalyzer:
    def test_insufficient_sectors(self) -> None:
        snap = make_snapshot(
            advances=500,
            declines=500,
            unchanged=0,
            total=1000,
            sectors=(make_sector("Tech", advances=50, declines=30),),
        )
        result = SectorBreadthAnalyzer().analyze(snap)
        assert result.confidence == 0.0
        assert "Insufficient sector data" in result.reasons[0]

    def test_advancing_sectors(self) -> None:
        sectors = (
            make_sector("Tech", advances=80, declines=20),
            make_sector("Finance", advances=60, declines=40),
            make_sector("Energy", advances=55, declines=45),
        )
        snap = make_snapshot(advances=500, declines=500, total=1000, sectors=sectors)
        result = SectorBreadthAnalyzer().analyze(snap)
        assert result.advancing_sectors == 3
        assert result.declining_sectors == 0

    def test_declining_sectors(self) -> None:
        sectors = (
            make_sector("Tech", advances=20, declines=80),
            make_sector("Finance", advances=40, declines=60),
            make_sector("Energy", advances=45, declines=55),
        )
        snap = make_snapshot(advances=500, declines=500, total=1000, sectors=sectors)
        result = SectorBreadthAnalyzer().analyze(snap)
        assert result.declining_sectors == 3

    def test_rotation_detected(self) -> None:
        sectors = (
            make_sector("Tech", advances=80, declines=20),
            make_sector("Finance", advances=20, declines=80),
            make_sector("Energy", advances=55, declines=45),
        )
        snap = make_snapshot(advances=500, declines=500, total=1000, sectors=sectors)
        result = SectorBreadthAnalyzer().analyze(snap)
        assert result.rotation_detected is True

    def test_leading_and_lagging_sectors(self) -> None:
        sectors = (
            make_sector("Tech", advances=90, declines=10),
            make_sector("Finance", advances=60, declines=40),
            make_sector("Energy", advances=10, declines=90),
            make_sector("Health", advances=50, declines=50),
            make_sector("Consumer", advances=30, declines=70),
        )
        snap = make_snapshot(advances=500, declines=500, total=1000, sectors=sectors)
        result = SectorBreadthAnalyzer().analyze(snap)
        assert "Tech" in result.leading_sectors
        assert "Energy" in result.lagging_sectors

    def test_no_sectors(self) -> None:
        snap = make_snapshot(advances=500, declines=500, total=1000)
        result = SectorBreadthAnalyzer().analyze(snap)
        assert result.confidence == 0.0

    def test_concentration_risk(self) -> None:
        sectors = (
            make_sector("Tech", advances=80, declines=20, weight=0.6),
            make_sector("Finance", advances=50, declines=50, weight=0.2),
            make_sector("Energy", advances=50, declines=50, weight=0.2),
        )
        snap = make_snapshot(advances=500, declines=500, total=1000, sectors=sectors)
        result = SectorBreadthAnalyzer().analyze(snap)
        assert result.concentration_risk is True

    def test_no_concentration_risk(self) -> None:
        sectors = (
            make_sector("Tech", advances=50, declines=50, weight=0.3),
            make_sector("Finance", advances=50, declines=50, weight=0.3),
            make_sector("Energy", advances=50, declines=50, weight=0.4),
        )
        snap = make_snapshot(advances=500, declines=500, total=1000, sectors=sectors)
        result = SectorBreadthAnalyzer().analyze(snap)
        assert result.concentration_risk is False

    def test_reasons_include_sector_count(self) -> None:
        sectors = (
            make_sector("Tech", advances=80, declines=20),
            make_sector("Finance", advances=60, declines=40),
        )
        snap = make_snapshot(advances=500, declines=500, total=1000, sectors=sectors)
        result = SectorBreadthAnalyzer().analyze(snap)
        assert any("sector(s)" in r for r in result.reasons)

    def test_mixed_sectors_with_unchanged(self) -> None:
        sectors = (
            make_sector("Tech", advances=50, declines=50),
            make_sector("Finance", advances=50, declines=50),
            make_sector("Energy", advances=50, declines=50),
        )
        snap = make_snapshot(advances=500, declines=500, total=1000, sectors=sectors)
        result = SectorBreadthAnalyzer().analyze(snap)
        assert result.advancing_sectors == 0
        assert result.declining_sectors == 0


# ---------------------------------------------------------------------------
# MarketParticipationAnalyzer unit tests
# ---------------------------------------------------------------------------


class TestMarketParticipationAnalyzer:
    def test_insufficient_data(self) -> None:
        snap = make_snapshot(advances=2, declines=2, total=4)
        result = MarketParticipationAnalyzer().analyze(snap)
        assert result.confidence == 0.0
        assert "Insufficient data" in result.reasons[0]

    def test_internal_strength(self) -> None:
        snap = make_snapshot(advances=700, declines=250, unchanged=50, total=1000)
        result = MarketParticipationAnalyzer().analyze(snap)
        assert result.internal_strength is True
        assert result.internal_weakness is False

    def test_internal_weakness_narrow(self) -> None:
        snap = make_snapshot(advances=200, declines=800, unchanged=0, total=1000)
        result = MarketParticipationAnalyzer().analyze(snap)
        assert result.internal_weakness is True

    def test_divergence_narrow_participation(self) -> None:
        snap = make_snapshot(advances=400, declines=100, unchanged=500, total=1000)
        result = MarketParticipationAnalyzer().analyze(snap)
        assert result.divergence_detected is True

    def test_divergence_skewed_breadth(self) -> None:
        snap = make_snapshot(advances=850, declines=100, unchanged=50, total=1000)
        result = MarketParticipationAnalyzer().analyze(snap)
        assert result.divergence_detected is True

    def test_neutral_participation(self) -> None:
        snap = make_snapshot(advances=500, declines=450, unchanged=50, total=1000)
        result = MarketParticipationAnalyzer().analyze(snap)
        assert result.internal_strength is False
        assert result.internal_weakness is False

    def test_participation_ratio(self) -> None:
        snap = make_snapshot(advances=300, declines=300, unchanged=400, total=1000)
        result = MarketParticipationAnalyzer().analyze(snap)
        assert result.participation_ratio == 0.6

    def test_reasons_include_participation_ratio(self) -> None:
        snap = make_snapshot(advances=500, declines=450, unchanged=50, total=1000)
        result = MarketParticipationAnalyzer().analyze(snap)
        assert any("Participation ratio" in r for r in result.reasons)

    def test_full_participation(self) -> None:
        snap = make_snapshot(advances=500, declines=500, unchanged=0, total=1000)
        result = MarketParticipationAnalyzer().analyze(snap)
        assert result.participation_ratio == 1.0


# ---------------------------------------------------------------------------
# BreadthAnalyzer orchestrator tests
# ---------------------------------------------------------------------------


class TestBreadthAnalyzer:
    def test_insufficient_data(self) -> None:
        snap = make_snapshot(advances=1, declines=0, total=1)
        result = BreadthAnalyzer().analyze(snap)
        assert result.confidence == 0.0
        assert "Insufficient data" in result.warnings[0]

    def test_healthy_breadth_bullish(self) -> None:
        snap = make_snapshot(advances=800, declines=150, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.breadth_bias is BreadthBias.BULLISH
        assert result.breadth_strength is BreadthStrength.VERY_STRONG
        assert result.advance_decline_ratio > 1.0

    def test_weak_breadth_bearish(self) -> None:
        snap = make_snapshot(advances=150, declines=800, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.breadth_bias is BreadthBias.BEARISH
        assert result.breadth_strength is BreadthStrength.VERY_WEAK

    def test_neutral_breadth(self) -> None:
        snap = make_snapshot(advances=500, declines=480, unchanged=20, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.breadth_bias is BreadthBias.NEUTRAL

    def test_advance_dominance_bullish(self) -> None:
        snap = make_snapshot(advances=600, declines=300, unchanged=100, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.breadth_bias is BreadthBias.BULLISH

    def test_decline_dominance_bearish(self) -> None:
        snap = make_snapshot(advances=300, declines=600, unchanged=100, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.breadth_bias is BreadthBias.BEARISH

    def test_divergence_detected(self) -> None:
        snap = make_snapshot(advances=400, declines=100, unchanged=500, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.divergence_detected is True

    def test_market_health_healthy(self) -> None:
        snap = make_snapshot(advances=800, declines=150, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.market_health == "healthy"

    def test_market_health_unhealthy(self) -> None:
        snap = make_snapshot(advances=100, declines=850, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.market_health == "unhealthy"

    def test_market_health_divergent(self) -> None:
        snap = make_snapshot(advances=400, declines=100, unchanged=500, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.market_health == "divergent"

    def test_market_health_neutral(self) -> None:
        snap = make_snapshot(advances=500, declines=480, unchanged=20, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.market_health == "neutral"

    def test_leading_sectors_from_orchestrator(self) -> None:
        sectors = (
            make_sector("Tech", advances=90, declines=10),
            make_sector("Energy", advances=10, declines=90),
            make_sector("Finance", advances=70, declines=30),
        )
        snap = make_snapshot(
            advances=500,
            declines=500,
            total=1000,
            sectors=sectors,
        )
        result = BreadthAnalyzer().analyze(snap)
        assert len(result.leading_sectors) > 0

    def test_evidence_generated(self) -> None:
        snap = make_snapshot(advances=700, declines=250, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.evidence is not None
        assert result.evidence.category is EvidenceCategory.MARKET_BREADTH
        assert result.evidence.source == "Breadth"

    def test_evidence_signal_bullish(self) -> None:
        snap = make_snapshot(advances=800, declines=150, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.evidence is not None
        assert result.evidence.signal is EvidenceSignal.BULLISH

    def test_evidence_signal_bearish(self) -> None:
        snap = make_snapshot(advances=150, declines=800, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.evidence is not None
        assert result.evidence.signal is EvidenceSignal.BEARISH

    def test_evidence_score_bullish(self) -> None:
        snap = make_snapshot(advances=800, declines=150, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.evidence is not None
        assert result.evidence.score.value >= 50.0

    def test_evidence_score_bearish(self) -> None:
        snap = make_snapshot(advances=150, declines=800, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.evidence is not None
        assert result.evidence.score.value <= 50.0

    def test_evidence_reasons(self) -> None:
        snap = make_snapshot(advances=500, declines=500, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.evidence is not None
        assert len(result.evidence.reasons) > 0

    def test_explanation_generated(self) -> None:
        snap = make_snapshot(advances=700, declines=250, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.explanation is not None
        assert isinstance(result.explanation, BreadthExplanation)

    def test_explanation_sections(self) -> None:
        snap = make_snapshot(advances=700, declines=250, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        exp = result.explanation
        assert exp.overall_breadth != ""
        assert exp.advance_decline != ""
        assert exp.participation != ""
        assert exp.institutional_interpretation != ""

    def test_warnings_limited_symbols(self) -> None:
        snap = make_snapshot(advances=10, declines=10, total=20)
        result = BreadthAnalyzer().analyze(snap)
        assert any("Limited" in w for w in result.warnings)

    def test_metadata_present(self) -> None:
        snap = make_snapshot(advances=500, declines=500, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert "analyzer" in result.metadata
        assert result.metadata["analyzer"] == "BreadthAnalyzer"

    def test_neutral_placeholder(self) -> None:
        result = BreadthAnalysis.neutral_placeholder()
        assert result.confidence == 0.0
        assert "Breadth data unavailable." in result.warnings

    def test_advance_decline_subresult(self) -> None:
        snap = make_snapshot(advances=500, declines=500, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.advance_decline is not None
        assert isinstance(result.advance_decline, AdvanceDecline)

    def test_sector_breadth_subresult(self) -> None:
        sectors = (
            make_sector("Tech", advances=50, declines=50),
            make_sector("Finance", advances=50, declines=50),
        )
        snap = make_snapshot(advances=500, declines=500, total=1000, sectors=sectors)
        result = BreadthAnalyzer().analyze(snap)
        assert result.sector_breadth is not None
        assert isinstance(result.sector_breadth, SectorBreadth)

    def test_market_participation_subresult(self) -> None:
        snap = make_snapshot(advances=500, declines=500, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.market_participation is not None
        assert isinstance(result.market_participation, MarketParticipation)

    def test_empty_analysis(self) -> None:
        snap = make_snapshot(advances=0, declines=0, total=0)
        result = BreadthAnalyzer().analyze(snap)
        assert result.confidence == 0.0
        assert len(result.warnings) >= 1

    def test_empty_analysis_explanation(self) -> None:
        snap = make_snapshot(advances=0, declines=0, total=0)
        result = BreadthAnalyzer().analyze(snap)
        assert result.explanation is not None
        assert "unavailable" in result.explanation.overall_breadth

    def test_breadth_analysis_type(self) -> None:
        snap = make_snapshot(advances=500, declines=500, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert isinstance(result, BreadthAnalysis)

    def test_participation_ratio_in_analysis(self) -> None:
        snap = make_snapshot(advances=300, declines=200, unchanged=500, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.participation_ratio == 0.5

    def test_advance_percentage_in_analysis(self) -> None:
        snap = make_snapshot(advances=250, declines=500, unchanged=250, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.advance_percentage == 25.0


# ---------------------------------------------------------------------------
# Validation and serialization tests
# ---------------------------------------------------------------------------


class TestValidation:
    def test_breadth_analysis_frozen(self) -> None:
        result = BreadthAnalysis.neutral_placeholder()
        with pytest.raises(AttributeError):
            result.advance_decline_ratio = 2.0

    def test_advance_decline_frozen(self) -> None:
        ad = AdvanceDecline()
        with pytest.raises(AttributeError):
            ad.ad_ratio = 2.0

    def test_sector_breadth_frozen(self) -> None:
        sb = SectorBreadth()
        with pytest.raises(AttributeError):
            sb.advancing_sectors = 5

    def test_market_participation_frozen(self) -> None:
        mp = MarketParticipation()
        with pytest.raises(AttributeError):
            mp.participation_ratio = 0.5

    def test_sector_breadth_snapshot_frozen(self) -> None:
        sbs = SectorBreadthSnapshot()
        with pytest.raises(AttributeError):
            sbs.sector_name = "Changed"

    def test_market_breadth_snapshot_frozen(self) -> None:
        mbs = MarketBreadthSnapshot()
        with pytest.raises(AttributeError):
            mbs.index_name = "Changed"


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_all_unchanged(self) -> None:
        snap = make_snapshot(advances=0, declines=0, unchanged=1000, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.advance_decline_ratio == 1.0
        assert result.breadth_strength is BreadthStrength.NEUTRAL

    def test_single_sector(self) -> None:
        sectors = (make_sector("Tech", advances=50, declines=50),)
        snap = make_snapshot(
            advances=500,
            declines=500,
            total=1000,
            sectors=sectors,
        )
        result = SectorBreadthAnalyzer().analyze(snap)
        assert result.confidence == 0.0

    def test_sector_empty_name(self) -> None:
        sectors = (
            make_sector("", advances=80, declines=20),
            make_sector("Finance", advances=50, declines=50),
            make_sector("Energy", advances=50, declines=50),
        )
        snap = make_snapshot(advances=500, declines=500, total=1000, sectors=sectors)
        result = SectorBreadthAnalyzer().analyze(snap)
        assert result.leading_sectors is not None

    def test_extreme_ad_ratio(self) -> None:
        snap = make_snapshot(advances=1000, declines=1, unchanged=0, total=1001)
        result = AdvanceDeclineAnalyzer().analyze(snap)
        assert result.ad_ratio == 1000.0

    def test_confidence_bounds(self) -> None:
        snap = make_snapshot(advances=500, declines=500, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert 0.0 <= result.confidence <= 1.0

    def test_market_health_default(self) -> None:
        snap = make_snapshot(advances=500, declines=500, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert result.market_health == "neutral"

    def test_institutional_interpretation_bullish(self) -> None:
        snap = make_snapshot(advances=800, declines=150, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert "bullish" in result.explanation.institutional_interpretation.lower()

    def test_institutional_interpretation_bearish(self) -> None:
        snap = make_snapshot(advances=150, declines=800, unchanged=50, total=1000)
        result = BreadthAnalyzer().analyze(snap)
        assert "bearish" in result.explanation.institutional_interpretation.lower()

    def test_institutional_interpretation_unavailable(self) -> None:
        snap = make_snapshot(advances=0, declines=0, total=0)
        result = BreadthAnalyzer().analyze(snap)
        assert "unavailable" in result.explanation.institutional_interpretation.lower()
