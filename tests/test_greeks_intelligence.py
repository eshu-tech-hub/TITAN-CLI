from datetime import datetime

import pytest

from titan.core.evidence import Evidence, EvidenceCategory, EvidenceSignal
from titan.options.analytics import (
    DeltaAnalyzer,
    GammaAnalyzer,
    GreeksAnalysis,
    GreeksAnalyzer,
    GreeksExplanation,
    MarketBias,
    OptionChainSnapshot,
    OptionStrikeSnapshot,
    ThetaAnalyzer,
    VegaAnalyzer,
)


def make_snapshot(
    strikes: tuple[OptionStrikeSnapshot, ...],
    *,
    underlying: str = "NIFTY",
    underlying_price: float | None = 24025.0,
) -> OptionChainSnapshot:
    return OptionChainSnapshot(
        underlying=underlying,
        expiry=datetime(2026, 6, 25),
        timestamp=datetime(2026, 6, 22, 9, 30),
        strikes=strikes,
        underlying_price=underlying_price,
    )


def test_greeks_analyzer_integrates_component_analyzers():
    analyzer = GreeksAnalyzer()

    assert tuple(type(item) for item in analyzer.analyzers) == (
        DeltaAnalyzer,
        GammaAnalyzer,
        ThetaAnalyzer,
        VegaAnalyzer,
    )


def test_missing_greeks_do_not_crash_analysis():
    analyzer = GreeksAnalyzer()
    analysis = analyzer.analyze(make_snapshot((OptionStrikeSnapshot(24000.0),)))

    assert isinstance(analysis, GreeksAnalysis)
    assert analysis.net_delta is None
    assert analysis.net_gamma is None
    assert analysis.net_theta is None
    assert analysis.net_vega is None
    assert analysis.overall_bias is MarketBias.NEUTRAL
    assert analysis.confidence == 0.1
    assert "Missing Delta" in analysis.warnings
    assert "Missing Gamma" in analysis.warnings
    assert "Missing Theta" in analysis.warnings
    assert "Missing Vega" in analysis.warnings


def test_none_values_are_ignored_without_crashing():
    analyzer = GreeksAnalyzer()
    snapshot = make_snapshot(
        (
            OptionStrikeSnapshot(
                24000.0,
                call_delta=None,
                put_delta=-0.4,
                call_gamma=None,
                put_gamma=0.03,
                call_theta=None,
                put_theta=-0.8,
                call_vega=None,
                put_vega=0.45,
            ),
        )
    )

    analysis = analyzer.analyze(snapshot)

    assert analysis.net_delta == pytest.approx(-0.4)
    assert analysis.net_gamma == pytest.approx(0.03)
    assert analysis.net_theta == pytest.approx(-0.8)
    assert analysis.net_vega == pytest.approx(0.45)


def test_zero_greeks_are_valid_values():
    analyzer = GreeksAnalyzer()
    snapshot = make_snapshot(
        (
            OptionStrikeSnapshot(
                24000.0,
                call_delta=0.0,
                put_delta=0.0,
                call_gamma=0.0,
                put_gamma=0.0,
                call_theta=0.0,
                put_theta=0.0,
                call_vega=0.0,
                put_vega=0.0,
            ),
        )
    )

    analysis = analyzer.analyze(snapshot)

    assert analysis.net_delta == 0.0
    assert analysis.net_gamma == 0.0
    assert analysis.net_theta == 0.0
    assert analysis.net_vega == 0.0
    assert analysis.confidence > 0.1


def test_single_strike_greeks_generate_explanation_and_evidence():
    analyzer = GreeksAnalyzer()
    snapshot = make_snapshot(
        (
            OptionStrikeSnapshot(
                24000.0,
                call_delta=0.55,
                put_delta=-0.35,
                call_gamma=0.04,
                put_gamma=0.03,
                call_theta=-0.5,
                put_theta=-0.4,
                call_vega=0.7,
                put_vega=0.65,
            ),
        )
    )

    analysis = analyzer.analyze(snapshot)

    assert isinstance(analysis.evidence, Evidence)
    assert analysis.evidence.source == "Greeks"
    assert analysis.evidence.category is EvidenceCategory.OPTION_CHAIN
    assert isinstance(analysis.explanation, GreeksExplanation)
    assert "Net delta" in analysis.explanation.delta
    assert "Net gamma" in analysis.explanation.gamma
    assert "Net theta" in analysis.explanation.theta
    assert "Net vega" in analysis.explanation.vega
    assert "Overall Greeks bias" in analysis.explanation.overall


def test_multiple_strikes_calculate_net_and_average_greeks():
    analyzer = GreeksAnalyzer()
    snapshot = make_snapshot(
        (
            OptionStrikeSnapshot(
                24000.0,
                call_delta=0.6,
                put_delta=-0.2,
                call_gamma=0.03,
                put_gamma=0.02,
                call_theta=-0.2,
                put_theta=-0.3,
                call_vega=0.4,
                put_vega=0.5,
            ),
            OptionStrikeSnapshot(
                24100.0,
                call_delta=0.4,
                put_delta=-0.1,
                call_gamma=0.01,
                put_gamma=0.01,
                call_theta=-0.1,
                put_theta=-0.2,
                call_vega=0.3,
                put_vega=0.2,
            ),
        )
    )

    analysis = analyzer.analyze(snapshot)

    assert analysis.net_delta == pytest.approx(0.7)
    assert analysis.average_delta == pytest.approx(0.175)
    assert analysis.net_gamma == pytest.approx(0.07)
    assert analysis.average_gamma == pytest.approx(0.0175)
    assert analysis.net_theta == pytest.approx(-0.8)
    assert analysis.average_theta == pytest.approx(-0.2)
    assert analysis.net_vega == pytest.approx(1.4)
    assert analysis.average_vega == pytest.approx(0.35)
    assert analysis.overall_bias in (MarketBias.NEUTRAL, MarketBias.BULLISH)


def test_mixed_greeks_generate_warnings_and_partial_confidence():
    analyzer = GreeksAnalyzer()
    snapshot = make_snapshot(
        (
            OptionStrikeSnapshot(
                24000.0,
                call_delta=0.6,
                call_gamma=0.05,
                call_theta=-1.0,
                call_vega=1.2,
            ),
            OptionStrikeSnapshot(24100.0),
        ),
        underlying_price=None,
    )

    analysis = analyzer.analyze(snapshot)

    assert analysis.net_delta == pytest.approx(0.6)
    assert 0.1 < analysis.confidence < 0.7
    assert "ATM Delta Unavailable" in analysis.warnings
    assert "High Time Decay Risk" in analysis.warnings
    assert "High Vega Risk" in analysis.warnings


def test_component_analyzers_generate_evidence():
    snapshot = make_snapshot(
        (
            OptionStrikeSnapshot(
                24000.0,
                call_delta=0.6,
                put_delta=-0.1,
                call_gamma=0.02,
                put_gamma=0.02,
                call_theta=-0.2,
                put_theta=-0.2,
                call_vega=0.2,
                put_vega=0.2,
            ),
        )
    )

    for analyzer_class in (DeltaAnalyzer, GammaAnalyzer, ThetaAnalyzer, VegaAnalyzer):
        analyzer = analyzer_class()
        result = analyzer.analyze(snapshot)
        evidence = analyzer.to_evidence(result)

        assert evidence.source == "Greeks"
        assert evidence.category is EvidenceCategory.OPTION_CHAIN
        assert evidence.signal in {
            EvidenceSignal.BULLISH,
            EvidenceSignal.BEARISH,
            EvidenceSignal.NEUTRAL,
            EvidenceSignal.UNKNOWN,
        }
        assert evidence.reasons


def test_greeks_analysis_to_evidence_returns_aggregate_evidence():
    analyzer = GreeksAnalyzer()
    analysis = analyzer.analyze(
        make_snapshot(
            (
                OptionStrikeSnapshot(
                    24000.0,
                    call_delta=0.6,
                    put_delta=-0.2,
                    call_gamma=0.02,
                    put_gamma=0.02,
                    call_theta=-0.2,
                    put_theta=-0.2,
                    call_vega=0.2,
                    put_vega=0.2,
                ),
            )
        )
    )

    evidence = analyzer.to_evidence(analysis)

    assert evidence is analysis.evidence
    assert evidence.source == "Greeks"
    assert evidence.metadata["component_count"] == 4


def test_greeks_analyzer_rejects_invalid_snapshot():
    analyzer = GreeksAnalyzer()

    with pytest.raises(TypeError):
        analyzer.analyze(object())


def test_greeks_analyzer_rejects_empty_underlying():
    analyzer = GreeksAnalyzer()

    with pytest.raises(ValueError):
        analyzer.analyze(make_snapshot((), underlying=" "))
