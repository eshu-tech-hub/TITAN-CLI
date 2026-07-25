from datetime import datetime

import pytest

from titan.core.evidence import (
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    EvidenceValidationError,
)
from titan.options.analytics import AnalysisResult, MarketBias
from titan.options.analytics.models import OptionChainSnapshot, OptionStrikeSnapshot
from titan.options.analytics.oi import OpenInterestAnalyzer


def make_snapshot(
    strikes: tuple[OptionStrikeSnapshot, ...],
    *,
    underlying: str = "NIFTY",
) -> OptionChainSnapshot:
    return OptionChainSnapshot(
        underlying=underlying,
        expiry=datetime(2026, 6, 25),
        timestamp=datetime(2026, 6, 22, 9, 30),
        strikes=strikes,
    )


def test_open_interest_analyzer_rejects_invalid_snapshot():
    analyzer = OpenInterestAnalyzer()

    with pytest.raises(TypeError):
        analyzer.analyze(object())


def test_open_interest_analyzer_rejects_empty_underlying():
    analyzer = OpenInterestAnalyzer()
    snapshot = make_snapshot((), underlying=" ")

    with pytest.raises(ValueError):
        analyzer.analyze(snapshot)


def test_empty_snapshot_returns_unknown_conservative_result():
    analyzer = OpenInterestAnalyzer()
    result = analyzer.analyze(make_snapshot(()))

    assert isinstance(result, AnalysisResult)
    assert result.score == 50.0
    assert result.confidence == 0.1
    assert result.neutral
    assert result.metadata["market_bias"] is MarketBias.UNKNOWN
    assert result.metadata["total_call_oi"] == 0
    assert result.metadata["total_put_oi"] == 0
    assert result.metadata["support_strike"] is None
    assert result.metadata["resistance_strike"] is None
    assert "Incomplete Snapshot" in result.warnings


def test_single_strike_populates_metadata_with_low_confidence():
    analyzer = OpenInterestAnalyzer()
    snapshot = make_snapshot(
        (
            OptionStrikeSnapshot(
                strike_price=24000.0,
                call_open_interest=100,
                put_open_interest=200,
                call_volume=5,
                put_volume=8,
            ),
        )
    )

    result = analyzer.analyze(snapshot)

    assert result.bullish
    assert result.score > 50.0
    assert result.confidence == 0.25
    assert result.metadata["total_call_oi"] == 100
    assert result.metadata["total_put_oi"] == 200
    assert result.metadata["highest_call_oi_strike"] == 24000.0
    assert result.metadata["highest_put_oi_strike"] == 24000.0
    assert result.metadata["support_strike"] == 24000.0
    assert result.metadata["resistance_strike"] == 24000.0
    assert "Strong Put OI" in result.reasons
    assert "Incomplete Snapshot" in result.warnings


def test_multiple_strikes_detects_bullish_put_oi_bias():
    analyzer = OpenInterestAnalyzer()
    snapshot = make_snapshot(
        (
            OptionStrikeSnapshot(
                strike_price=23900.0,
                call_open_interest=100,
                put_open_interest=500,
                call_volume=10,
                put_volume=20,
                call_open_interest_change=5,
                put_open_interest_change=40,
            ),
            OptionStrikeSnapshot(
                strike_price=24000.0,
                call_open_interest=200,
                put_open_interest=300,
                call_volume=12,
                put_volume=15,
                call_open_interest_change=10,
                put_open_interest_change=60,
            ),
        )
    )

    result = analyzer.analyze(snapshot)

    assert result.bullish
    assert not result.bearish
    assert result.score > 50.0
    assert result.confidence == 0.35
    assert result.metadata["total_call_oi"] == 300
    assert result.metadata["total_put_oi"] == 800
    assert result.metadata["call_oi_change"] == 15
    assert result.metadata["put_oi_change"] == 100
    assert result.metadata["highest_call_change"] == 10
    assert result.metadata["highest_put_change"] == 60
    assert result.metadata["support_strike"] == 23900.0
    assert result.metadata["resistance_strike"] == 24000.0
    assert result.metadata["market_bias"] is MarketBias.BULLISH
    assert "Put OI Increasing" in result.reasons
    assert "Conflicting OI" in result.warnings


def test_multiple_strikes_detects_bearish_call_oi_bias():
    analyzer = OpenInterestAnalyzer()
    snapshot = make_snapshot(
        (
            OptionStrikeSnapshot(
                strike_price=24000.0,
                call_open_interest=600,
                put_open_interest=100,
                call_volume=20,
                put_volume=10,
            ),
            OptionStrikeSnapshot(
                strike_price=24100.0,
                call_open_interest=400,
                put_open_interest=200,
                call_volume=25,
                put_volume=12,
            ),
        )
    )

    result = analyzer.analyze(snapshot)

    assert result.bearish
    assert result.score < 50.0
    assert result.metadata["market_bias"] is MarketBias.BEARISH
    assert result.metadata["resistance_strike"] == 24000.0
    assert "Strong Call OI" in result.reasons


def test_missing_oi_change_values_are_placeholder_metadata():
    analyzer = OpenInterestAnalyzer()
    snapshot = make_snapshot(
        (
            OptionStrikeSnapshot(
                strike_price=24000.0,
                call_open_interest=100,
                put_open_interest=100,
                call_volume=1,
                put_volume=1,
            ),
            OptionStrikeSnapshot(
                strike_price=24100.0,
                call_open_interest=100,
                put_open_interest=100,
                call_volume=1,
                put_volume=1,
            ),
        )
    )

    result = analyzer.analyze(snapshot)

    assert result.neutral
    assert result.metadata["call_oi_change"] is None
    assert result.metadata["put_oi_change"] is None
    assert result.metadata["highest_call_change"] is None
    assert result.metadata["highest_put_change"] is None
    assert result.metadata["market_bias"] is MarketBias.NEUTRAL


def test_low_liquidity_warning_for_zero_volume_snapshot():
    analyzer = OpenInterestAnalyzer()
    snapshot = make_snapshot(
        (
            OptionStrikeSnapshot(
                strike_price=24000.0,
                call_open_interest=100,
                put_open_interest=100,
            ),
            OptionStrikeSnapshot(
                strike_price=24100.0,
                call_open_interest=100,
                put_open_interest=100,
            ),
        )
    )

    result = analyzer.analyze(snapshot)

    assert "Low Liquidity" in result.warnings


def test_to_evidence_converts_analysis_result():
    analyzer = OpenInterestAnalyzer()
    result = analyzer.analyze(
        make_snapshot(
            (
                OptionStrikeSnapshot(
                    strike_price=24000.0,
                    call_open_interest=100,
                    put_open_interest=300,
                    call_volume=10,
                    put_volume=20,
                ),
                OptionStrikeSnapshot(
                    strike_price=24100.0,
                    call_open_interest=100,
                    put_open_interest=200,
                    call_volume=10,
                    put_volume=20,
                ),
            )
        )
    )

    evidence = analyzer.to_evidence(result)

    assert isinstance(evidence, Evidence)
    assert evidence.source == "Open Interest"
    assert evidence.category is EvidenceCategory.OPTION_CHAIN
    assert evidence.signal is EvidenceSignal.BULLISH
    assert float(evidence.score) == result.score
    assert float(evidence.confidence) == result.confidence
    assert evidence.reasons == result.reasons
    assert evidence.warnings == result.warnings
    assert evidence.metadata == result.metadata


def test_to_evidence_rejects_invalid_result():
    analyzer = OpenInterestAnalyzer()

    with pytest.raises(TypeError):
        analyzer.to_evidence(object())


def test_to_evidence_validates_score_range():
    analyzer = OpenInterestAnalyzer()
    result = AnalysisResult(
        score=101.0,
        confidence=0.5,
        bullish=True,
        bearish=False,
        neutral=False,
        metadata={"market_bias": MarketBias.BULLISH},
    )

    with pytest.raises(EvidenceValidationError):
        analyzer.to_evidence(result)


def test_to_evidence_validates_confidence_range():
    analyzer = OpenInterestAnalyzer()
    result = AnalysisResult(
        score=50.0,
        confidence=1.1,
        bullish=False,
        bearish=False,
        neutral=True,
        metadata={"market_bias": MarketBias.NEUTRAL},
    )

    with pytest.raises(EvidenceValidationError):
        analyzer.to_evidence(result)
