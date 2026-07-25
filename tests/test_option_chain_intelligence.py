from datetime import datetime

import pytest

from titan.core.evidence import Evidence, EvidenceCategory, EvidenceSignal
from titan.options.analytics import (
    MarketBias,
    OpenInterestAnalyzer,
    OptionChainAnalysis,
    OptionChainAnalyzer,
    OptionChainExplanation,
    OptionChainSnapshot,
    OptionStrikeSnapshot,
    PCRAnalyzer,
    SupportResistanceAnalyzer,
)


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


def test_option_chain_analyzer_integrates_milestone_analyzers():
    analyzer = OptionChainAnalyzer()

    assert tuple(type(item) for item in analyzer.analyzers) == (
        PCRAnalyzer,
        SupportResistanceAnalyzer,
        OpenInterestAnalyzer,
    )


def test_option_chain_analyzer_returns_evidence_backed_analysis():
    analyzer = OptionChainAnalyzer()
    snapshot = make_snapshot(
        (
            OptionStrikeSnapshot(
                strike_price=23900.0,
                call_open_interest=100,
                put_open_interest=500,
                call_volume=10,
                put_volume=20,
                put_open_interest_change=30,
            ),
            OptionStrikeSnapshot(
                strike_price=24000.0,
                call_open_interest=100,
                put_open_interest=300,
                call_volume=12,
                put_volume=15,
                put_open_interest_change=40,
            ),
            OptionStrikeSnapshot(
                strike_price=24100.0,
                call_open_interest=150,
                put_open_interest=100,
                call_volume=20,
                put_volume=8,
            ),
        )
    )

    analysis = analyzer.analyze(snapshot)

    assert isinstance(analysis, OptionChainAnalysis)
    assert analysis.overall_bias is MarketBias.BULLISH
    assert analysis.confidence > 0.0
    assert analysis.pcr == pytest.approx(2.5714, rel=0.001)
    assert analysis.support == 23900.0
    assert analysis.resistance == 24100.0
    assert analysis.highest_put_strike == 23900.0
    assert analysis.highest_call_strike == 24100.0
    assert analysis.bullish_score > analysis.bearish_score
    assert len(analysis.evidence) == 3
    assert all(isinstance(item, Evidence) for item in analysis.evidence)
    assert {item.category for item in analysis.evidence} == {
        EvidenceCategory.OPTION_CHAIN
    }
    assert EvidenceSignal.BULLISH in {item.signal for item in analysis.evidence}
    assert isinstance(analysis.explanation, OptionChainExplanation)
    assert "bullish" in analysis.explanation.summary
    assert analysis.explanation.key_points


def test_option_chain_analyzer_handles_empty_snapshot_conservatively():
    analyzer = OptionChainAnalyzer()

    analysis = analyzer.analyze(make_snapshot(()))

    assert analysis.overall_bias is MarketBias.NEUTRAL
    assert analysis.confidence < 0.2
    assert analysis.support is None
    assert analysis.resistance is None
    assert analysis.pcr is None
    assert "Missing OI" in analysis.warnings
    assert analysis.explanation.warnings == analysis.warnings


def test_option_chain_analyzer_rejects_invalid_snapshot():
    analyzer = OptionChainAnalyzer()

    with pytest.raises(TypeError):
        analyzer.analyze(object())


def test_option_chain_analyzer_rejects_empty_underlying():
    analyzer = OptionChainAnalyzer()

    with pytest.raises(ValueError):
        analyzer.analyze(make_snapshot((), underlying=" "))
