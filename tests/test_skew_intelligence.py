import ast
from datetime import datetime
from pathlib import Path

import pytest

from titan.core.evidence import Evidence, EvidenceCategory, EvidenceSignal
from titan.options.analytics import (
    ButterflyAnalyzer,
    ButterflyResult,
    MarketBias,
    OptionChainSnapshot,
    OptionStrikeSnapshot,
    RiskReversalAnalyzer,
    RiskReversalResult,
    SkewAnalysis,
    SkewAnalyzer,
    SkewDirection,
    SkewExplanation,
    SkewStrength,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def make_chain(
    strikes: tuple[OptionStrikeSnapshot, ...],
    *,
    underlying: str = "SPY",
    underlying_price: float | None = 500.0,
) -> OptionChainSnapshot:
    return OptionChainSnapshot(
        underlying=underlying,
        expiry=datetime(2026, 7, 31),
        timestamp=datetime(2026, 7, 2, 9, 30),
        strikes=strikes,
        underlying_price=underlying_price,
    )


def make_strike(
    strike_price: float,
    *,
    call_iv: float | None = None,
    put_iv: float | None = None,
    call_delta: float | None = None,
    put_delta: float | None = None,
) -> OptionStrikeSnapshot:
    return OptionStrikeSnapshot(
        strike_price=strike_price,
        call_implied_volatility=call_iv,
        put_implied_volatility=put_iv,
        call_delta=call_delta,
        put_delta=put_delta,
        call_open_interest=0,
        put_open_interest=0,
        call_volume=0,
        put_volume=0,
    )


def flat_skew_chain() -> OptionChainSnapshot:
    return make_chain(
        strikes=(
            make_strike(480.0, put_iv=0.205),
            make_strike(490.0, put_iv=0.203),
            make_strike(500.0, call_iv=0.20, put_iv=0.20),
            make_strike(510.0, call_iv=0.203),
            make_strike(520.0, call_iv=0.205),
        ),
        underlying_price=500.0,
    )


def put_skew_chain() -> OptionChainSnapshot:
    return make_chain(
        strikes=(
            make_strike(480.0, put_iv=0.35),
            make_strike(490.0, put_iv=0.28),
            make_strike(500.0, call_iv=0.20, put_iv=0.20),
            make_strike(510.0, call_iv=0.22),
            make_strike(520.0, call_iv=0.24),
        ),
        underlying_price=500.0,
    )


def call_skew_chain() -> OptionChainSnapshot:
    return make_chain(
        strikes=(
            make_strike(480.0, put_iv=0.22),
            make_strike(490.0, put_iv=0.24),
            make_strike(500.0, call_iv=0.20, put_iv=0.20),
            make_strike(510.0, call_iv=0.28),
            make_strike(520.0, call_iv=0.35),
        ),
        underlying_price=500.0,
    )


def delta_skew_chain() -> OptionChainSnapshot:
    return make_chain(
        strikes=(
            make_strike(470.0, put_iv=0.32, put_delta=-0.20),
            make_strike(480.0, put_iv=0.30, put_delta=-0.25),
            make_strike(490.0, put_iv=0.26, put_delta=-0.35),
            make_strike(
                500.0, call_iv=0.20, put_iv=0.20, call_delta=0.05, put_delta=-0.50
            ),
            make_strike(510.0, call_iv=0.22, call_delta=0.35),
            make_strike(520.0, call_iv=0.24, call_delta=0.25),
            make_strike(530.0, call_iv=0.30, call_delta=0.20),
        ),
        underlying_price=500.0,
    )


def strong_put_skew_chain() -> OptionChainSnapshot:
    return make_chain(
        strikes=(
            make_strike(470.0, put_iv=0.45),
            make_strike(480.0, put_iv=0.40),
            make_strike(490.0, put_iv=0.35),
            make_strike(500.0, call_iv=0.18, put_iv=0.18),
            make_strike(510.0, call_iv=0.20),
            make_strike(520.0, call_iv=0.22),
            make_strike(530.0, call_iv=0.24),
        ),
        underlying_price=500.0,
    )


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestSkewAnalysisModel:
    def test_neutral_placeholder(self) -> None:
        analysis = SkewAnalysis.neutral_placeholder()

        assert analysis.direction is SkewDirection.UNKNOWN
        assert analysis.strength is SkewStrength.UNKNOWN
        assert analysis.risk_reversal is None
        assert analysis.butterfly is None
        assert analysis.overall_bias is MarketBias.UNKNOWN
        assert analysis.confidence == 0.0
        assert "Skew data unavailable" in analysis.warnings[0]

    def test_frozen(self) -> None:
        analysis = SkewAnalysis.neutral_placeholder()

        with pytest.raises(AttributeError):
            analysis.confidence = 0.5  # type: ignore[misc]

    def test_skew_direction_values(self) -> None:
        assert SkewDirection.LEFT.value == "left"
        assert SkewDirection.RIGHT.value == "right"
        assert SkewDirection.SYMMETRIC.value == "symmetric"
        assert SkewDirection.UNKNOWN.value == "unknown"

    def test_skew_strength_values(self) -> None:
        assert SkewStrength.LOW.value == "low"
        assert SkewStrength.MEDIUM.value == "medium"
        assert SkewStrength.HIGH.value == "high"
        assert SkewStrength.EXTREME.value == "extreme"
        assert SkewStrength.UNKNOWN.value == "unknown"


class TestRiskReversalResultModel:
    def test_defaults(self) -> None:
        result = RiskReversalResult()

        assert result.twenty_five_delta_rr is None
        assert result.general_rr is None
        assert result.bias is MarketBias.UNKNOWN
        assert result.confidence == 0.0
        assert result.warnings == ()

    def test_frozen(self) -> None:
        result = RiskReversalResult()

        with pytest.raises(AttributeError):
            result.bias = MarketBias.BULLISH  # type: ignore[misc]


class TestButterflyResultModel:
    def test_defaults(self) -> None:
        result = ButterflyResult()

        assert result.atm_richness is None
        assert result.wing_richness is None
        assert result.relative_curvature is None

    def test_frozen(self) -> None:
        result = ButterflyResult()

        with pytest.raises(AttributeError):
            result.atm_richness = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RiskReversalAnalyzer tests
# ---------------------------------------------------------------------------


class TestRiskReversalAnalyzer:
    def test_missing_iv(self) -> None:
        analyzer = RiskReversalAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(480.0),
                make_strike(500.0),
                make_strike(520.0),
            ),
            underlying_price=500.0,
        )

        result = analyzer.analyze(chain)

        assert result.twenty_five_delta_rr is None
        assert result.general_rr is None
        assert result.bias is MarketBias.UNKNOWN

    def test_missing_strikes(self) -> None:
        analyzer = RiskReversalAnalyzer()
        chain = make_chain(strikes=())

        result = analyzer.analyze(chain)

        assert result.twenty_five_delta_rr is None
        assert result.general_rr is None
        assert "no strikes" in result.warnings[0].lower()

    def test_flat_skew(self) -> None:
        analyzer = RiskReversalAnalyzer()
        chain = flat_skew_chain()

        result = analyzer.analyze(chain)

        assert result.general_rr is not None
        assert abs(result.general_rr) < 0.01
        assert result.bias is MarketBias.NEUTRAL

    def test_put_skew_general_rr(self) -> None:
        analyzer = RiskReversalAnalyzer()
        chain = put_skew_chain()

        result = analyzer.analyze(chain)

        assert result.general_rr is not None
        assert result.general_rr > 0
        assert result.bias is MarketBias.BEARISH

    def test_call_skew_general_rr(self) -> None:
        analyzer = RiskReversalAnalyzer()
        chain = call_skew_chain()

        result = analyzer.analyze(chain)

        assert result.general_rr is not None
        assert result.general_rr < 0
        assert result.bias is MarketBias.BULLISH

    def test_twenty_five_delta_rr(self) -> None:
        analyzer = RiskReversalAnalyzer()
        chain = delta_skew_chain()

        result = analyzer.analyze(chain)

        assert result.twenty_five_delta_rr is not None
        assert result.twenty_five_delta_put_strike == 480.0
        assert result.twenty_five_delta_call_strike == 520.0
        assert result.twenty_five_delta_rr > 0
        assert result.bias is MarketBias.BEARISH

    def test_strong_put_skew(self) -> None:
        analyzer = RiskReversalAnalyzer()
        chain = strong_put_skew_chain()

        result = analyzer.analyze(chain)

        assert result.general_rr is not None
        assert result.general_rr > 0.05
        assert result.confidence > 0.5

    def test_empty_chain_returns_placeholder(self) -> None:
        analyzer = RiskReversalAnalyzer()
        chain = make_chain(strikes=())

        result = analyzer.analyze(chain)

        assert result.bias is MarketBias.UNKNOWN
        assert result.confidence == 0.0

    def test_non_chain_input_raises(self) -> None:
        analyzer = RiskReversalAnalyzer()

        with pytest.raises(TypeError, match="chain must be an OptionChainSnapshot"):
            analyzer.analyze("not-a-chain")  # type: ignore[arg-type]

    def test_no_underlying_price_uses_median(self) -> None:
        analyzer = RiskReversalAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(490.0, put_iv=0.25),
                make_strike(500.0, call_iv=0.20, put_iv=0.20),
                make_strike(510.0, call_iv=0.28),
            ),
            underlying_price=None,
        )

        result = analyzer.analyze(chain)

        assert result.general_rr is not None

    def test_warning_when_25d_unavailable(self) -> None:
        analyzer = RiskReversalAnalyzer()
        chain = flat_skew_chain()

        result = analyzer.analyze(chain)

        assert any("25-delta" in w.lower() for w in result.warnings)

    def test_warning_for_few_strikes(self) -> None:
        analyzer = RiskReversalAnalyzer()
        chain = make_chain(
            strikes=(make_strike(500.0, call_iv=0.20, put_iv=0.20),),
            underlying_price=500.0,
        )

        result = analyzer.analyze(chain)

        assert any("insufficient strikes" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# ButterflyAnalyzer tests
# ---------------------------------------------------------------------------


class TestButterflyAnalyzer:
    def test_missing_iv(self) -> None:
        analyzer = ButterflyAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(480.0),
                make_strike(500.0),
                make_strike(520.0),
            ),
            underlying_price=500.0,
        )

        result = analyzer.analyze(chain)

        assert result.atm_richness is None
        assert result.wing_richness is None

    def test_missing_strikes(self) -> None:
        analyzer = ButterflyAnalyzer()
        chain = make_chain(strikes=())

        result = analyzer.analyze(chain)

        assert result.atm_iv is None
        assert "no strikes" in result.warnings[0].lower()

    def test_flat_skew_butterfly(self) -> None:
        analyzer = ButterflyAnalyzer()
        chain = flat_skew_chain()

        result = analyzer.analyze(chain)

        assert result.atm_iv is not None
        assert result.atm_richness is not None
        assert abs(result.atm_richness) < 0.03

    def test_put_skew_butterfly(self) -> None:
        analyzer = ButterflyAnalyzer()
        chain = put_skew_chain()

        result = analyzer.analyze(chain)

        assert result.atm_richness is not None
        assert result.wing_richness is not None
        assert result.relative_curvature is not None

    def test_strong_put_skew_butterfly_curvature(self) -> None:
        analyzer = ButterflyAnalyzer()
        chain = strong_put_skew_chain()

        result = analyzer.analyze(chain)

        assert result.atm_richness is not None
        assert result.relative_curvature is not None
        assert result.relative_curvature > 0

    def test_confidence_with_rich_data(self) -> None:
        analyzer = ButterflyAnalyzer()
        chain = put_skew_chain()

        result = analyzer.analyze(chain)

        assert result.confidence > 0.7

    def test_low_confidence_with_sparse_data(self) -> None:
        analyzer = ButterflyAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(490.0, put_iv=0.25),
                make_strike(500.0, call_iv=0.20, put_iv=0.20),
                make_strike(510.0, call_iv=0.30),
            ),
            underlying_price=500.0,
        )

        result = analyzer.analyze(chain)

        assert result.confidence <= 0.85

    def test_empty_chain_returns_placeholder(self) -> None:
        analyzer = ButterflyAnalyzer()
        chain = make_chain(strikes=())

        result = analyzer.analyze(chain)

        assert result.confidence == 0.0

    def test_non_chain_input_raises(self) -> None:
        analyzer = ButterflyAnalyzer()

        with pytest.raises(TypeError, match="chain must be an OptionChainSnapshot"):
            analyzer.analyze("not-a-chain")  # type: ignore[arg-type]

    def test_no_underlying_price(self) -> None:
        analyzer = ButterflyAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(490.0, put_iv=0.25),
                make_strike(500.0, call_iv=0.20, put_iv=0.20),
                make_strike(510.0, call_iv=0.28),
            ),
            underlying_price=None,
        )

        result = analyzer.analyze(chain)

        assert result.atm_iv is not None


# ---------------------------------------------------------------------------
# SkewAnalyzer tests
# ---------------------------------------------------------------------------


class TestSkewAnalyzer:
    def test_flat_skew(self) -> None:
        analyzer = SkewAnalyzer()
        chain = flat_skew_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.direction is SkewDirection.SYMMETRIC
        assert analysis.strength is SkewStrength.LOW
        assert analysis.overall_bias is MarketBias.NEUTRAL

    def test_strong_put_skew(self) -> None:
        analyzer = SkewAnalyzer()
        chain = strong_put_skew_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.direction is SkewDirection.LEFT
        assert analysis.overall_bias is MarketBias.BEARISH
        assert analysis.confidence > 0.3

    def test_put_skew_from_general_rr(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.direction is SkewDirection.LEFT
        assert analysis.overall_bias is MarketBias.BEARISH

    def test_call_skew(self) -> None:
        analyzer = SkewAnalyzer()
        chain = call_skew_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.direction is SkewDirection.RIGHT
        assert analysis.overall_bias is MarketBias.BULLISH

    def test_delta_skew(self) -> None:
        analyzer = SkewAnalyzer()
        chain = delta_skew_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.direction is SkewDirection.LEFT
        assert analysis.risk_reversal is not None
        assert analysis.risk_reversal.twenty_five_delta_rr is not None

    def test_missing_iv(self) -> None:
        analyzer = SkewAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(480.0),
                make_strike(500.0),
                make_strike(520.0),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.direction is SkewDirection.UNKNOWN
        assert analysis.strength is SkewStrength.UNKNOWN
        assert analysis.confidence == 0.0

    def test_missing_strikes(self) -> None:
        analyzer = SkewAnalyzer()
        chain = make_chain(strikes=())

        analysis = analyzer.analyze(chain)

        assert analysis.direction is SkewDirection.UNKNOWN
        assert analysis.confidence == 0.0
        assert "no strikes" in analysis.warnings[0].lower()

    def test_risk_reversal_sub_analysis(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.risk_reversal is not None
        assert isinstance(analysis.risk_reversal, RiskReversalResult)
        assert analysis.risk_reversal.general_rr is not None

    def test_butterfly_sub_analysis(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.butterfly is not None
        assert isinstance(analysis.butterfly, ButterflyResult)
        assert analysis.butterfly.atm_richness is not None

    def test_non_chain_input_raises(self) -> None:
        analyzer = SkewAnalyzer()

        with pytest.raises(TypeError, match="chain must be an OptionChainSnapshot"):
            analyzer.analyze("not-a-chain")  # type: ignore[arg-type]

    def test_confidence_calculation(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)

        assert 0.0 <= analysis.confidence <= 1.0

    def test_warnings_aggregated(self) -> None:
        analyzer = SkewAnalyzer()
        chain = make_chain(
            strikes=(make_strike(500.0, call_iv=0.20, put_iv=0.20),),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert len(analysis.warnings) > 0

    def test_steep_skew_strength(self) -> None:
        analyzer = SkewAnalyzer()
        chain = strong_put_skew_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.strength in (SkewStrength.HIGH, SkewStrength.EXTREME)


# ---------------------------------------------------------------------------
# Evidence generation
# ---------------------------------------------------------------------------


class TestEvidenceGeneration:
    def test_evidence_produced(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.evidence is not None
        assert isinstance(analysis.evidence, Evidence)

    def test_evidence_source(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.source == "Volatility Skew"

    def test_evidence_category(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.category is EvidenceCategory.OPTION_CHAIN

    def test_evidence_signal_put_skew(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.signal is EvidenceSignal.BEARISH

    def test_evidence_signal_call_skew(self) -> None:
        analyzer = SkewAnalyzer()
        chain = call_skew_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.signal is EvidenceSignal.BULLISH

    def test_evidence_signal_flat(self) -> None:
        analyzer = SkewAnalyzer()
        chain = flat_skew_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.signal is EvidenceSignal.NEUTRAL

    def test_evidence_score_in_range(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert 0.0 <= float(evidence.score) <= 100.0

    def test_evidence_confidence_in_range(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert 0.0 <= float(evidence.confidence) <= 1.0

    def test_evidence_reasons_present(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert len(evidence.reasons) > 0

    def test_evidence_metadata(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.metadata["analyzer"] == "SkewAnalyzer"
        assert evidence.metadata["skew_direction"] == analysis.direction.value


# ---------------------------------------------------------------------------
# Explanation generation
# ---------------------------------------------------------------------------


class TestExplanationGeneration:
    def test_explanation_produced(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.explanation is not None
        assert isinstance(analysis.explanation, SkewExplanation)

    def test_explanation_sections(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)
        explanation = analysis.explanation

        assert explanation is not None
        assert explanation.skew_direction
        assert explanation.risk_reversal
        assert explanation.butterfly
        assert explanation.institutional_interpretation
        assert explanation.risk_assessment

    def test_explanation_put_skew_direction(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)
        explanation = analysis.explanation

        assert explanation is not None
        assert "left-sided" in explanation.skew_direction.lower()

    def test_explanation_call_skew_direction(self) -> None:
        analyzer = SkewAnalyzer()
        chain = call_skew_chain()

        analysis = analyzer.analyze(chain)
        explanation = analysis.explanation

        assert explanation is not None
        assert "right-sided" in explanation.skew_direction.lower()

    def test_explanation_flat_skew(self) -> None:
        analyzer = SkewAnalyzer()
        chain = flat_skew_chain()

        analysis = analyzer.analyze(chain)
        explanation = analysis.explanation

        assert explanation is not None
        assert "symmetric" in explanation.skew_direction.lower()

    def test_explanation_institutional_interpretation(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)
        explanation = analysis.explanation

        assert explanation is not None
        assert "downside risk" in explanation.institutional_interpretation.lower()

    def test_explanation_risk_assessment(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)
        explanation = analysis.explanation

        assert explanation is not None
        assert "tail risk" in explanation.risk_assessment.lower()

    def test_explanation_insufficient_data(self) -> None:
        analyzer = SkewAnalyzer()
        chain = make_chain(strikes=())

        analysis = analyzer.analyze(chain)
        explanation = analysis.explanation

        assert explanation is not None
        assert "unavailable" in explanation.skew_direction.lower()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_chain_type_validated(self) -> None:
        analyzer = SkewAnalyzer()

        with pytest.raises(TypeError):
            analyzer.analyze(None)  # type: ignore[arg-type]

    def test_rr_chain_type_validated(self) -> None:
        analyzer = RiskReversalAnalyzer()

        with pytest.raises(TypeError):
            analyzer.analyze(None)  # type: ignore[arg-type]

    def test_bf_chain_type_validated(self) -> None:
        analyzer = ButterflyAnalyzer()

        with pytest.raises(TypeError):
            analyzer.analyze(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# forbidden imports
# ---------------------------------------------------------------------------


def test_skew_has_no_forbidden_imports():
    analytics_dir = Path("titan/options/analytics")
    forbidden_terms = (
        "angel_one",
        "smartapi",
        "smartconnect",
        "broker",
        "black_scholes",
        "numpy",
        "scipy",
    )
    skew_files = (
        "skew.py",
        "risk_reversal.py",
        "butterfly.py",
    )

    for filename in skew_files:
        path = analytics_dir / filename
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
            ), f"Forbidden import found in {path}: {imported_names}"


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_single_strike(self) -> None:
        analyzer = SkewAnalyzer()
        chain = make_chain(
            strikes=(make_strike(500.0, call_iv=0.20, put_iv=0.20),),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.direction is SkewDirection.UNKNOWN
        assert analysis.strength is SkewStrength.UNKNOWN

    def test_all_ivs_none(self) -> None:
        analyzer = SkewAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(480.0),
                make_strike(500.0),
                make_strike(520.0),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.direction is SkewDirection.UNKNOWN
        assert analysis.strength is SkewStrength.UNKNOWN

    def test_only_puts_available(self) -> None:
        analyzer = SkewAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(480.0, put_iv=0.30),
                make_strike(490.0, put_iv=0.25),
                make_strike(500.0, put_iv=0.20),
                make_strike(510.0, put_iv=0.23),
                make_strike(520.0, put_iv=0.27),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.risk_reversal is not None
        assert analysis.butterfly is not None

    def test_only_calls_available(self) -> None:
        analyzer = SkewAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(480.0, call_iv=0.27),
                make_strike(490.0, call_iv=0.23),
                make_strike(500.0, call_iv=0.20),
                make_strike(510.0, call_iv=0.25),
                make_strike(520.0, call_iv=0.28),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.risk_reversal is not None
        assert analysis.butterfly is not None

    def test_extreme_put_skew_strength(self) -> None:
        analyzer = SkewAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(470.0, put_iv=0.60),
                make_strike(480.0, put_iv=0.55),
                make_strike(490.0, put_iv=0.50),
                make_strike(500.0, call_iv=0.15, put_iv=0.15),
                make_strike(510.0, call_iv=0.17),
                make_strike(520.0, call_iv=0.19),
                make_strike(530.0, call_iv=0.21),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.strength is SkewStrength.EXTREME
        assert analysis.direction is SkewDirection.LEFT

    def test_analysis_is_frozen(self) -> None:
        analyzer = SkewAnalyzer()
        chain = put_skew_chain()

        analysis = analyzer.analyze(chain)

        with pytest.raises(AttributeError):
            analysis.confidence = 0.5  # type: ignore[misc]
