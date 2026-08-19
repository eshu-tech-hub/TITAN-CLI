import ast
from datetime import datetime
from pathlib import Path

import pytest

from titan.options.analytics import (
    AnalysisResult,
    AnalysisSignal,
    BuildUpAnalyzer,
    DeltaAnalyzer,
    GammaAnalyzer,
    GreeksAnalysis,
    GreeksAnalyzer,
    GreeksExplanation,
    LiquidityAnalyzer,
    MarketBias,
    MaxPainAnalyzer,
    OpenInterestAnalyzer,
    OptionAnalyzer,
    OptionChainAnalysis,
    OptionChainAnalyzer,
    OptionChainExplanation,
    OptionChainSnapshot,
    OptionStrikeSnapshot,
    PCRAnalyzer,
    SentimentAnalyzer,
    StrikeRankAnalyzer,
    SupportResistanceAnalyzer,
    ThetaAnalyzer,
    VegaAnalyzer,
    WritingAnalyzer,
)

ANALYZER_CLASSES = (
    OpenInterestAnalyzer,
    PCRAnalyzer,
    DeltaAnalyzer,
    GammaAnalyzer,
    ThetaAnalyzer,
    VegaAnalyzer,
    MaxPainAnalyzer,
    BuildUpAnalyzer,
    WritingAnalyzer,
    LiquidityAnalyzer,
    StrikeRankAnalyzer,
    SentimentAnalyzer,
    SupportResistanceAnalyzer,
)

PLACEHOLDER_ANALYZER_CLASSES = (
    MaxPainAnalyzer,
    BuildUpAnalyzer,
    WritingAnalyzer,
    StrikeRankAnalyzer,
    SentimentAnalyzer,
)


def make_snapshot() -> OptionChainSnapshot:
    return OptionChainSnapshot(
        underlying="NIFTY",
        expiry=datetime(2026, 6, 25),
        timestamp=datetime(2026, 6, 22, 9, 30),
        strikes=(
            OptionStrikeSnapshot(
                strike_price=24000.0,
                call_open_interest=1000,
                put_open_interest=1200,
                call_volume=100,
                put_volume=120,
            ),
        ),
    )


def test_option_analyzer_is_abstract():
    with pytest.raises(TypeError):
        OptionAnalyzer()


def test_option_strike_snapshot_defaults():
    strike = OptionStrikeSnapshot(strike_price=24000.0)

    assert strike.call_open_interest == 0
    assert strike.put_open_interest == 0
    assert strike.call_volume == 0
    assert strike.put_volume == 0
    assert strike.call_last_price is None
    assert strike.put_last_price is None


def test_option_chain_snapshot_defaults_to_empty_strikes():
    snapshot = OptionChainSnapshot(
        underlying="NIFTY",
        expiry=datetime(2026, 6, 25),
        timestamp=datetime(2026, 6, 22, 9, 30),
    )

    assert snapshot.strikes == ()


def test_analysis_result_model_fields():
    result = AnalysisResult(
        score=0.25,
        confidence=0.5,
        bullish=True,
        bearish=False,
        neutral=False,
        reasons=("reason",),
        warnings=("warning",),
        metadata={"source": "test"},
    )

    assert result.score == 0.25
    assert result.confidence == 0.5
    assert result.bullish
    assert not result.bearish
    assert not result.neutral
    assert result.reasons == ("reason",)
    assert result.warnings == ("warning",)
    assert result.metadata["source"] == "test"


def test_option_chain_analysis_model_fields():
    explanation = OptionChainExplanation(
        summary="Option chain bias is neutral.",
        key_points=("PCR is balanced.",),
    )
    analysis = OptionChainAnalysis(
        overall_bias=MarketBias.NEUTRAL,
        confidence=0.5,
        support=24000.0,
        resistance=24200.0,
        pcr=1.0,
        highest_put_strike=24000.0,
        highest_call_strike=24200.0,
        bullish_score=50.0,
        bearish_score=50.0,
        neutral_score=100.0,
        explanation=explanation,
    )

    assert analysis.overall_bias is MarketBias.NEUTRAL
    assert analysis.explanation is explanation
    assert analysis.evidence == ()


def test_greeks_analysis_model_fields():
    explanation = GreeksExplanation(
        delta="Delta section.",
        gamma="Gamma section.",
        theta="Theta section.",
        vega="Vega section.",
        overall="Overall section.",
    )
    analysis = GreeksAnalysis(
        net_delta=0.25,
        net_gamma=0.02,
        net_theta=-1.2,
        net_vega=1.8,
        average_delta=0.12,
        average_gamma=0.01,
        average_theta=-0.6,
        average_vega=0.9,
        overall_bias=MarketBias.NEUTRAL,
        confidence=0.5,
        explanation=explanation,
    )

    assert analysis.net_delta == 0.25
    assert analysis.explanation is explanation
    assert analysis.evidence is None


def test_neutral_placeholder_result():
    result = AnalysisResult.neutral_placeholder("PCRAnalyzer")

    assert result.score == 0.0
    assert result.confidence == 0.0
    assert not result.bullish
    assert not result.bearish
    assert result.neutral
    assert result.reasons
    assert result.warnings
    assert result.metadata["analyzer"] == "PCRAnalyzer"
    assert result.metadata["signal"] is AnalysisSignal.NEUTRAL


@pytest.mark.parametrize("analyzer_class", ANALYZER_CLASSES)
def test_analyzer_initialization(analyzer_class: type[OptionAnalyzer]):
    analyzer = analyzer_class()

    assert isinstance(analyzer, OptionAnalyzer)
    assert analyzer.name == analyzer_class.__name__


@pytest.mark.parametrize("analyzer_class", ANALYZER_CLASSES)
def test_analyzer_returns_analysis_result(analyzer_class: type[OptionAnalyzer]):
    analyzer = analyzer_class()
    result = analyzer.analyze(make_snapshot())

    assert isinstance(result, AnalysisResult)


@pytest.mark.parametrize("analyzer_class", PLACEHOLDER_ANALYZER_CLASSES)
def test_placeholder_analyzer_returns_neutral_result(
    analyzer_class: type[OptionAnalyzer],
):
    analyzer = analyzer_class()
    result = analyzer.analyze(make_snapshot())

    assert result.neutral
    assert not result.bullish
    assert not result.bearish
    assert result.metadata["analyzer"] == analyzer.name


@pytest.mark.parametrize("analyzer_class", ANALYZER_CLASSES)
def test_analyzer_rejects_invalid_snapshot_type(
    analyzer_class: type[OptionAnalyzer],
):
    analyzer = analyzer_class()

    with pytest.raises(TypeError):
        analyzer.analyze(object())


@pytest.mark.parametrize("analyzer_class", ANALYZER_CLASSES)
def test_analyzer_rejects_empty_underlying(analyzer_class: type[OptionAnalyzer]):
    analyzer = analyzer_class()
    snapshot = OptionChainSnapshot(
        underlying=" ",
        expiry=datetime(2026, 6, 25),
        timestamp=datetime(2026, 6, 22, 9, 30),
    )

    with pytest.raises(ValueError):
        analyzer.analyze(snapshot)


def test_analytics_package_exports_all_analyzers():
    assert len(ANALYZER_CLASSES) == 13
    assert OptionChainAnalyzer
    assert GreeksAnalyzer


def test_option_analytics_has_no_broker_imports():
    analytics_dir = Path("titan/options/analytics")
    forbidden_terms = ("angel_one", "smartapi", "smartconnect", "broker")

    for path in analytics_dir.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names = {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported_names = {node.module or ""}
            else:
                continue

            assert all(
                term not in imported_name.lower()
                for imported_name in imported_names
                for term in forbidden_terms
            )
