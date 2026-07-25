import pytest

from titan.core.evidence import Evidence, EvidenceCategory, EvidenceSignal
from titan.options.analytics import (
    DepthAnalyzer,
    ExecutionGrade,
    LiquidityAnalysis,
    LiquidityAnalyzer,
    LiquidityExplanation,
    LiquidityQuality,
    LiquidityRisk,
    OptionLiquiditySnapshot,
    SlippageAnalyzer,
    SpreadAnalyzer,
)


def test_missing_values_remain_robust():
    analysis = LiquidityAnalyzer().evaluate(OptionLiquiditySnapshot())

    assert isinstance(analysis, LiquidityAnalysis)
    assert analysis.spread is None
    assert analysis.spread_percent is None
    assert analysis.depth_score == 0.0
    assert analysis.slippage_score == 0.0
    assert analysis.execution_score == 0.0
    assert analysis.execution_grade is ExecutionGrade.F
    assert analysis.confidence == pytest.approx(0.1)
    assert "Bid price is missing." in analysis.warnings
    assert "Ask quantity is missing." in analysis.warnings


def test_tight_spread_scores_high_quality():
    result = SpreadAnalyzer().analyze(
        OptionLiquiditySnapshot(bid_price=99.5, ask_price=100.0)
    )

    assert result.spread == pytest.approx(0.5)
    assert result.spread_percent == pytest.approx(0.5012531328)
    assert result.score > 90.0
    assert result.quality is LiquidityQuality.HIGH


def test_wide_spread_scores_low_quality():
    result = SpreadAnalyzer().analyze(
        OptionLiquiditySnapshot(bid_price=90.0, ask_price=110.0)
    )

    assert result.spread == pytest.approx(20.0)
    assert result.spread_percent == pytest.approx(20.0)
    assert result.score == 0.0
    assert result.quality is LiquidityQuality.LOW


def test_low_depth_generates_low_depth_score():
    result = DepthAnalyzer().analyze(
        OptionLiquiditySnapshot(bid_quantity=25, ask_quantity=10)
    )

    assert result.depth_score < 15.0
    assert result.quality is LiquidityQuality.LOW
    assert result.order_book_balance == pytest.approx(0.4)


def test_high_depth_generates_high_depth_score():
    result = DepthAnalyzer().analyze(
        OptionLiquiditySnapshot(bid_quantity=1250, ask_quantity=1200)
    )

    assert result.depth_score > 95.0
    assert result.quality is LiquidityQuality.HIGH
    assert result.order_book_balance == pytest.approx(0.96)


def test_slippage_estimates_liquidity_risk():
    snapshot = OptionLiquiditySnapshot(
        bid_price=99.5,
        ask_price=100.0,
        bid_quantity=1250,
        ask_quantity=1200,
        volume=5000,
        open_interest=10000,
    )
    spread = SpreadAnalyzer().analyze(snapshot)
    depth = DepthAnalyzer().analyze(snapshot)
    result = SlippageAnalyzer().analyze(snapshot, spread, depth)

    assert result.expected_slippage is not None
    assert result.expected_slippage < 1.0
    assert result.slippage_score > 90.0
    assert result.liquidity_risk is LiquidityRisk.LOW


def test_execution_score_and_grade_are_combined_from_components():
    snapshot = OptionLiquiditySnapshot(
        bid_price=99.5,
        ask_price=100.0,
        bid_quantity=1250,
        ask_quantity=1200,
        volume=5000,
        open_interest=10000,
    )

    analysis = LiquidityAnalyzer().evaluate(snapshot)

    assert analysis.execution_score > 90.0
    assert analysis.execution_grade is ExecutionGrade.A
    assert analysis.confidence > 0.75
    assert not analysis.warnings


def test_liquidity_evidence_uses_option_chain_category_and_weighted_values():
    analysis = LiquidityAnalyzer().evaluate(
        OptionLiquiditySnapshot(
            bid_price=99.5,
            ask_price=100.0,
            bid_quantity=1250,
            ask_quantity=1200,
            volume=5000,
            open_interest=10000,
        )
    )
    evidence = LiquidityAnalyzer().to_evidence(analysis)

    assert isinstance(evidence, Evidence)
    assert evidence.source == "Liquidity"
    assert evidence.category is EvidenceCategory.OPTION_CHAIN
    assert evidence.signal in (EvidenceSignal.BULLISH, EvidenceSignal.VERY_BULLISH)
    assert float(evidence.score) > 90.0
    assert float(evidence.confidence) == pytest.approx(analysis.confidence)
    assert evidence.metadata["future_extensions"] == (
        "level_2_market_depth",
        "live_order_book",
        "vwap",
        "iceberg_detection",
        "hidden_liquidity",
        "broker_latency",
    )


def test_structured_explanation_contains_required_sections():
    analysis = LiquidityAnalyzer().evaluate(
        OptionLiquiditySnapshot(
            bid_price=90.0,
            ask_price=110.0,
            bid_quantity=25,
            ask_quantity=10,
            volume=0,
            open_interest=0,
        )
    )

    assert isinstance(analysis.explanation, LiquidityExplanation)
    assert "Spread is" in analysis.explanation.spread
    assert "Displayed depth score" in analysis.explanation.depth
    assert "Expected slippage" in analysis.explanation.slippage
    assert "Execution score" in analysis.explanation.execution
    assert analysis.warnings
