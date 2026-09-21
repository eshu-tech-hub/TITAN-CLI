import ast
from datetime import datetime
from pathlib import Path

import pytest

from titan.core.evidence import Evidence, EvidenceCategory, EvidenceSignal
from titan.options.analytics import (
    OptionChainSnapshot,
    OptionStrikeSnapshot,
    SmileAnalysis,
    SmileAnalyzer,
    SmileExplanation,
    SmileQuality,
    SmileRegime,
    SmileShape,
    SmileSymmetry,
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
) -> OptionStrikeSnapshot:
    return OptionStrikeSnapshot(
        strike_price=strike_price,
        call_implied_volatility=call_iv,
        put_implied_volatility=put_iv,
        call_open_interest=0,
        put_open_interest=0,
        call_volume=0,
        put_volume=0,
    )


def symmetric_smile_chain(
    *, atm: float = 500.0, atm_iv: float = 0.20, wing_iv: float = 0.25
) -> OptionChainSnapshot:
    return make_chain(
        strikes=(
            make_strike(480.0, put_iv=wing_iv),
            make_strike(490.0, put_iv=wing_iv * 0.9),
            make_strike(500.0, call_iv=atm_iv, put_iv=atm_iv),
            make_strike(510.0, call_iv=wing_iv * 0.9),
            make_strike(520.0, call_iv=wing_iv),
        ),
        underlying_price=atm,
    )


def left_biased_chain() -> OptionChainSnapshot:
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


def right_biased_chain() -> OptionChainSnapshot:
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


def flat_smile_chain() -> OptionChainSnapshot:
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


def strong_smile_chain() -> OptionChainSnapshot:
    return make_chain(
        strikes=(
            make_strike(470.0, put_iv=0.26),
            make_strike(480.0, put_iv=0.24),
            make_strike(490.0, put_iv=0.22),
            make_strike(500.0, call_iv=0.18, put_iv=0.18),
            make_strike(510.0, call_iv=0.22),
            make_strike(520.0, call_iv=0.24),
            make_strike(530.0, call_iv=0.26),
        ),
        underlying_price=500.0,
    )


# ---------------------------------------------------------------------------
# SmileAnalysis model
# ---------------------------------------------------------------------------


class TestSmileAnalysisModel:
    def test_neutral_placeholder(self) -> None:
        analysis = SmileAnalysis.neutral_placeholder()

        assert analysis.atm_strike is None
        assert analysis.atm_iv is None
        assert analysis.smile_shape is SmileShape.UNKNOWN
        assert analysis.smile_symmetry is SmileSymmetry.UNKNOWN
        assert analysis.smile_regime is SmileRegime.UNKNOWN
        assert analysis.smile_quality is SmileQuality.UNKNOWN
        assert analysis.curvature is None
        assert analysis.confidence == 0.0
        assert "Smile data unavailable" in analysis.warnings[0]

    def test_frozen(self) -> None:
        analysis = SmileAnalysis.neutral_placeholder()

        with pytest.raises(AttributeError):
            analysis.confidence = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SmileAnalyzer
# ---------------------------------------------------------------------------


class TestSmileAnalyzer:
    def test_flat_smile(self) -> None:
        analyzer = SmileAnalyzer()
        chain = flat_smile_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.smile_shape is SmileShape.FLAT
        assert analysis.curvature is not None and analysis.curvature < 0.05

    def test_symmetric_smile(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.smile_symmetry is SmileSymmetry.SYMMETRIC

    def test_left_skew(self) -> None:
        analyzer = SmileAnalyzer()
        chain = left_biased_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.smile_symmetry is SmileSymmetry.LEFT_BIASED
        assert analysis.smile_regime is SmileRegime.PUT_SKEW

    def test_right_skew(self) -> None:
        analyzer = SmileAnalyzer()
        chain = right_biased_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.smile_symmetry is SmileSymmetry.RIGHT_BIASED
        assert analysis.smile_regime is SmileRegime.CALL_SKEW

    def test_normal_smile(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain(atm=500.0, atm_iv=0.20, wing_iv=0.24)

        analysis = analyzer.analyze(chain)

        assert analysis.smile_shape is SmileShape.NORMAL
        assert analysis.smile_symmetry is SmileSymmetry.SYMMETRIC
        assert analysis.smile_regime is SmileRegime.NORMAL_CONVEXITY

    def test_strong_smile(self) -> None:
        analyzer = SmileAnalyzer()
        chain = strong_smile_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.smile_shape is SmileShape.STRONG
        assert analysis.curvature is not None and analysis.curvature >= 0.20

    def test_extreme_smile(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(470.0, put_iv=0.50),
                make_strike(480.0, put_iv=0.45),
                make_strike(490.0, put_iv=0.40),
                make_strike(500.0, call_iv=0.18, put_iv=0.18),
                make_strike(510.0, call_iv=0.38),
                make_strike(520.0, call_iv=0.42),
                make_strike(530.0, call_iv=0.48),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.smile_shape is SmileShape.EXTREME
        assert analysis.curvature is not None and analysis.curvature >= 0.35

    def test_inverted_smile(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(490.0, put_iv=0.15),
                make_strike(500.0, call_iv=0.25, put_iv=0.25),
                make_strike(510.0, call_iv=0.15),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.smile_regime is SmileRegime.INVERTED

    def test_missing_atm(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(490.0, put_iv=0.25),
                make_strike(500.0),
                make_strike(510.0, call_iv=0.25),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.atm_strike == 500.0
        assert analysis.atm_iv is None
        assert analysis.smile_quality is SmileQuality.PARTIAL

    def test_sparse_strikes(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(490.0, put_iv=0.25),
                make_strike(500.0, call_iv=0.20, put_iv=0.20),
                make_strike(510.0, call_iv=0.30),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.strike_count == 3
        assert analysis.smile_quality is SmileQuality.PARTIAL

    def test_duplicate_strikes(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(500.0, call_iv=0.20, put_iv=0.20),
                make_strike(500.0, call_iv=0.20, put_iv=0.20),
                make_strike(510.0, call_iv=0.30),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.strike_count == 3
        assert analysis.smile_quality is SmileQuality.PARTIAL

    def test_invalid_iv(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(480.0, put_iv=-0.05),
                make_strike(490.0, put_iv=0.0),
                make_strike(500.0, call_iv=0.20, put_iv=0.20),
                make_strike(510.0, call_iv=15.0),
                make_strike(520.0, call_iv=0.30),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.iv_completeness < 1.0
        assert analysis.atm_iv == 0.20

    def test_empty_chain(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(strikes=())

        analysis = analyzer.analyze(chain)

        assert analysis.smile_shape is SmileShape.UNKNOWN
        assert analysis.confidence == 0.0
        assert "no strikes" in analysis.warnings[0].lower()

    def test_confidence_reliable(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.confidence > 0.7
        assert analysis.smile_quality is SmileQuality.RELIABLE

    def test_confidence_low_with_sparse_data(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(490.0, put_iv=0.25),
                make_strike(500.0, call_iv=0.20, put_iv=0.20),
                make_strike(510.0, call_iv=0.30),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.confidence <= 0.75

    def test_no_underlying_price(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(490.0, put_iv=0.25),
                make_strike(500.0, call_iv=0.20, put_iv=0.20),
                make_strike(510.0, call_iv=0.28),
            ),
            underlying_price=None,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.atm_strike == 500.0
        assert analysis.atm_iv is not None

    def test_non_chain_input_raises(self) -> None:
        analyzer = SmileAnalyzer()

        with pytest.raises(TypeError, match="chain must be an OptionChainSnapshot"):
            analyzer.analyze("not-a-chain")  # type: ignore[arg-type]

    def test_atm_iv_averages_call_and_put(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(500.0, call_iv=0.22, put_iv=0.18),
                make_strike(510.0, call_iv=0.28),
                make_strike(490.0, put_iv=0.28),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.atm_iv is not None
        assert analysis.atm_iv == 0.20


# ---------------------------------------------------------------------------
# evidence generation
# ---------------------------------------------------------------------------


class TestEvidenceGeneration:
    def test_evidence_produced(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.evidence is not None
        assert isinstance(analysis.evidence, Evidence)

    def test_evidence_source(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.source == "Volatility Smile"

    def test_evidence_category(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.category is EvidenceCategory.OPTION_CHAIN

    def test_evidence_signal_left_biased(self) -> None:
        analyzer = SmileAnalyzer()
        chain = left_biased_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.signal is EvidenceSignal.BEARISH

    def test_evidence_signal_right_biased(self) -> None:
        analyzer = SmileAnalyzer()
        chain = right_biased_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.signal is EvidenceSignal.BULLISH

    def test_evidence_signal_symmetric(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.signal is EvidenceSignal.NEUTRAL

    def test_evidence_score(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert 0.0 <= float(evidence.score) <= 100.0

    def test_evidence_confidence(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert 0.0 <= float(evidence.confidence) <= 1.0

    def test_evidence_reasons(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert len(evidence.reasons) > 0

    def test_evidence_metadata(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)
        evidence = analysis.evidence

        assert evidence is not None
        assert evidence.metadata["analyzer"] == "SmileAnalyzer"
        assert evidence.metadata["smile_shape"] == analysis.smile_shape.value


# ---------------------------------------------------------------------------
# explanation generation
# ---------------------------------------------------------------------------


class TestExplanationGeneration:
    def test_explanation_produced(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.explanation is not None
        assert isinstance(analysis.explanation, SmileExplanation)

    def test_explanation_sections(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)
        explanation = analysis.explanation

        assert explanation is not None
        assert explanation.overview
        assert explanation.curvature_assessment
        assert explanation.symmetry_assessment
        assert explanation.quality_assessment
        assert explanation.institutional_interpretation

    def test_explanation_flat_smile(self) -> None:
        analyzer = SmileAnalyzer()
        chain = flat_smile_chain()

        analysis = analyzer.analyze(chain)
        explanation = analysis.explanation

        assert explanation is not None
        assert "flat" in explanation.overview.lower()

    def test_explanation_left_biased(self) -> None:
        analyzer = SmileAnalyzer()
        chain = left_biased_chain()

        analysis = analyzer.analyze(chain)
        explanation = analysis.explanation

        assert explanation is not None
        assert (
            "left-biased" in explanation.symmetry_assessment.lower()
            or "left biased" in explanation.symmetry_assessment.lower()
        )
        assert "downside risk" in explanation.institutional_interpretation.lower()

    def test_explanation_insufficient_data(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(strikes=())

        analysis = analyzer.analyze(chain)
        explanation = analysis.explanation

        assert explanation is not None
        assert "insufficient" in explanation.overview.lower()


# ---------------------------------------------------------------------------
# serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_analysis_is_frozen(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)

        with pytest.raises(AttributeError):
            analysis.atm_iv = 0.5  # type: ignore[misc]

    def test_analysis_metadata(self) -> None:
        analyzer = SmileAnalyzer()
        chain = symmetric_smile_chain()

        analysis = analyzer.analyze(chain)

        assert analysis.metadata["analyzer"] == "SmileAnalyzer"
        assert analysis.metadata["underlying"] == "SPY"
        assert analysis.metadata["smile_shape"] == analysis.smile_shape.value


# ---------------------------------------------------------------------------
# backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_existing_chain_snapshot_unmodified(self) -> None:
        chain = make_chain(strikes=(make_strike(500.0, call_iv=0.20, put_iv=0.20),))

        assert chain.underlying == "SPY"
        assert chain.expiry == datetime(2026, 7, 31)
        assert chain.underlying_price == 500.0
        assert len(chain.strikes) == 1

    def test_existing_strike_snapshot_unmodified(self) -> None:
        strike = make_strike(500.0, call_iv=0.20, put_iv=0.20)

        assert strike.strike_price == 500.0
        assert strike.call_implied_volatility == 0.20
        assert strike.put_implied_volatility == 0.20

    def test_smile_analyzer_does_not_affect_other_analyzers(self) -> None:
        smile_analyzer = SmileAnalyzer()

        from titan.options.analytics.volatility import VolatilityAnalyzer

        vol_analyzer = VolatilityAnalyzer()

        assert isinstance(smile_analyzer, SmileAnalyzer)
        assert isinstance(vol_analyzer, VolatilityAnalyzer)
        assert smile_analyzer.name == "SmileAnalyzer"
        assert vol_analyzer.name == "VolatilityAnalyzer"


# ---------------------------------------------------------------------------
# forbidden imports
# ---------------------------------------------------------------------------


def test_smile_has_no_forbidden_imports():
    analytics_dir = Path("titan/options/analytics")
    forbidden_terms = (
        "yfinance",
        "yfinance",
        "smartconnect",
        "broker",
        "black_scholes",
        "numpy",
        "scipy",
    )
    smile_files = (
        "smile.py",
        "models.py",
    )

    for filename in smile_files:
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
        analyzer = SmileAnalyzer()
        chain = make_chain(
            strikes=(make_strike(500.0, call_iv=0.20, put_iv=0.20),),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.atm_strike == 500.0
        assert analysis.atm_iv == 0.20
        assert analysis.smile_quality is SmileQuality.UNRELIABLE
        assert analysis.smile_shape is SmileShape.UNKNOWN

    def test_all_ivs_none(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(480.0),
                make_strike(500.0),
                make_strike(520.0),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.atm_iv is None
        assert analysis.smile_shape is SmileShape.UNKNOWN
        assert analysis.smile_quality is SmileQuality.UNRELIABLE

    def test_only_puts_available(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(
            strikes=(
                make_strike(480.0, put_iv=0.28),
                make_strike(490.0, put_iv=0.25),
                make_strike(500.0, put_iv=0.20),
                make_strike(510.0, put_iv=0.23),
                make_strike(520.0, put_iv=0.27),
            ),
            underlying_price=500.0,
        )

        analysis = analyzer.analyze(chain)

        assert analysis.atm_iv == 0.20
        assert analysis.left_wing_iv is not None
        assert analysis.smile_symmetry is SmileSymmetry.LEFT_BIASED

    def test_only_calls_available(self) -> None:
        analyzer = SmileAnalyzer()
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

        assert analysis.atm_iv == 0.20
        assert analysis.right_wing_iv is not None
        assert analysis.smile_symmetry is SmileSymmetry.RIGHT_BIASED

    def test_chain_no_strikes_returns_placeholder(self) -> None:
        analyzer = SmileAnalyzer()
        chain = make_chain(strikes=())

        analysis = analyzer.analyze(chain)

        assert analysis.smile_shape is SmileShape.UNKNOWN
        assert analysis.smile_symmetry is SmileSymmetry.UNKNOWN
        assert analysis.smile_regime is SmileRegime.UNKNOWN
        assert analysis.smile_quality is SmileQuality.UNKNOWN
        assert analysis.strike_count == 0
