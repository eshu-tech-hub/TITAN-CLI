import ast
from pathlib import Path

import pytest

from titan.options.analytics import (
    HVTrend,
    HVStability,
    IVHVRelation,
    IVLevel,
    IVRankLevel,
    IVTrend,
    MarketBias,
    VolatilityAnalysis,
    VolatilityExplanation,
    VolatilityRegime,
    VolatilitySnapshot,
)
from titan.options.analytics.hv import HVAnalyzer
from titan.options.analytics.iv import IVAnalyzer
from titan.options.analytics.iv_percentile import IVPercentileAnalyzer
from titan.options.analytics.iv_rank import IVRankAnalyzer
from titan.options.analytics.volatility import VolatilityAnalyzer
from titan.options.analytics.volatility_regime import (
    VolatilityRegimeAnalyzer,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def make_snapshot(
    *,
    implied_volatility: float | None = 0.25,
    historical_volatility: float | None = 0.20,
    iv_rank: float | None = 50.0,
    iv_percentile: float | None = 50.0,
    implied_volatilities: tuple[float, ...] = (),
    historical_volatilities: tuple[float, ...] = (),
) -> VolatilitySnapshot:
    return VolatilitySnapshot(
        implied_volatility=implied_volatility,
        historical_volatility=historical_volatility,
        iv_rank=iv_rank,
        iv_percentile=iv_percentile,
        implied_volatilities=implied_volatilities,
        historical_volatilities=historical_volatilities,
    )


# ---------------------------------------------------------------------------
# VolatilitySnapshot
# ---------------------------------------------------------------------------


class TestVolatilitySnapshot:
    def test_default_all_none(self) -> None:
        snapshot = VolatilitySnapshot()

        assert snapshot.implied_volatility is None
        assert snapshot.historical_volatility is None
        assert snapshot.iv_rank is None
        assert snapshot.iv_percentile is None
        assert snapshot.volatility_index is None

    def test_custom_values(self) -> None:
        snapshot = make_snapshot(implied_volatility=0.35)

        assert snapshot.implied_volatility == 0.35

    def test_frozen(self) -> None:
        snapshot = make_snapshot()

        with pytest.raises(AttributeError):
            snapshot.implied_volatility = 0.5


# ---------------------------------------------------------------------------
# VolatilityAnalysis
# ---------------------------------------------------------------------------


class TestVolatilityAnalysis:
    def test_neutral_placeholder(self) -> None:
        analysis = VolatilityAnalysis.neutral_placeholder()

        assert analysis.current_iv is None
        assert analysis.current_hv is None
        assert analysis.overall_bias is MarketBias.UNKNOWN
        assert analysis.confidence == 0.0
        assert "Volatility data unavailable" in analysis.warnings[0]

    def test_frozen(self) -> None:
        analysis = VolatilityAnalysis.neutral_placeholder()

        with pytest.raises(AttributeError):
            analysis.confidence = 0.5


# ---------------------------------------------------------------------------
# IVAnalyzer
# ---------------------------------------------------------------------------


class TestIVAnalyzer:
    def test_high_iv(self) -> None:
        analyzer = IVAnalyzer()
        level, trend, conf = analyzer.analyze(make_snapshot(implied_volatility=0.50))

        assert level is IVLevel.HIGH

    def test_low_iv(self) -> None:
        analyzer = IVAnalyzer()
        level, trend, conf = analyzer.analyze(make_snapshot(implied_volatility=0.10))

        assert level is IVLevel.LOW

    def test_normal_iv(self) -> None:
        analyzer = IVAnalyzer()
        level, trend, conf = analyzer.analyze(make_snapshot(implied_volatility=0.25))

        assert level is IVLevel.NORMAL

    def test_none_iv(self) -> None:
        analyzer = IVAnalyzer()
        level, trend, conf = analyzer.analyze(make_snapshot(implied_volatility=None))

        assert level is IVLevel.UNKNOWN
        assert trend is IVTrend.UNKNOWN
        assert conf == 0.0

    def test_rising_trend(self) -> None:
        analyzer = IVAnalyzer()
        values = (0.20, 0.22, 0.25, 0.30)
        level, trend, conf = analyzer.analyze(
            make_snapshot(implied_volatility=0.30, implied_volatilities=values)
        )

        assert trend is IVTrend.RISING

    def test_falling_trend(self) -> None:
        analyzer = IVAnalyzer()
        values = (0.30, 0.28, 0.25, 0.20)
        level, trend, conf = analyzer.analyze(
            make_snapshot(implied_volatility=0.20, implied_volatilities=values)
        )

        assert trend is IVTrend.FALLING

    def test_flat_trend(self) -> None:
        analyzer = IVAnalyzer()
        values = (0.25, 0.26, 0.25, 0.24)
        level, trend, conf = analyzer.analyze(
            make_snapshot(implied_volatility=0.24, implied_volatilities=values)
        )

        assert trend is IVTrend.FLAT


# ---------------------------------------------------------------------------
# HVAnalyzer
# ---------------------------------------------------------------------------


class TestHVAnalyzer:
    def test_returns_hv_value(self) -> None:
        analyzer = HVAnalyzer()
        hv, trend, stability, conf = analyzer.analyze(
            make_snapshot(historical_volatility=0.20)
        )

        assert hv == 0.20

    def test_none_hv(self) -> None:
        analyzer = HVAnalyzer()
        hv, trend, stability, conf = analyzer.analyze(
            make_snapshot(historical_volatility=None)
        )

        assert hv is None
        assert trend is HVTrend.UNKNOWN
        assert stability is HVStability.UNKNOWN
        assert conf == 0.0

    def test_rising_trend(self) -> None:
        analyzer = HVAnalyzer()
        values = (0.15, 0.18, 0.20, 0.25)
        hv, trend, stability, conf = analyzer.analyze(
            make_snapshot(
                historical_volatility=0.25,
                historical_volatilities=values,
            )
        )

        assert trend is HVTrend.RISING

    def test_falling_trend(self) -> None:
        analyzer = HVAnalyzer()
        values = (0.30, 0.28, 0.22, 0.18)
        hv, trend, stability, conf = analyzer.analyze(
            make_snapshot(
                historical_volatility=0.18,
                historical_volatilities=values,
            )
        )

        assert trend is HVTrend.FALLING

    def test_stable_hv(self) -> None:
        analyzer = HVAnalyzer()
        values = (0.20, 0.21, 0.19, 0.20)
        hv, trend, stability, conf = analyzer.analyze(
            make_snapshot(
                historical_volatility=0.20,
                historical_volatilities=values,
            )
        )

        assert stability is HVStability.STABLE

    def test_unstable_hv(self) -> None:
        analyzer = HVAnalyzer()
        values = (0.10, 0.30, 0.15, 0.40)
        hv, trend, stability, conf = analyzer.analyze(
            make_snapshot(
                historical_volatility=0.40,
                historical_volatilities=values,
            )
        )

        assert stability is HVStability.UNSTABLE


# ---------------------------------------------------------------------------
# IVRankAnalyzer
# ---------------------------------------------------------------------------


class TestIVRankAnalyzer:
    def test_very_high_rank(self) -> None:
        analyzer = IVRankAnalyzer()
        level, rank, conf = analyzer.analyze(make_snapshot(iv_rank=90.0))

        assert level is IVRankLevel.VERY_HIGH
        assert rank == 90.0

    def test_high_rank(self) -> None:
        analyzer = IVRankAnalyzer()
        level, rank, conf = analyzer.analyze(make_snapshot(iv_rank=70.0))

        assert level is IVRankLevel.HIGH

    def test_neutral_rank(self) -> None:
        analyzer = IVRankAnalyzer()
        level, rank, conf = analyzer.analyze(make_snapshot(iv_rank=50.0))

        assert level is IVRankLevel.NEUTRAL

    def test_very_low_rank(self) -> None:
        analyzer = IVRankAnalyzer()
        level, rank, conf = analyzer.analyze(make_snapshot(iv_rank=10.0))

        assert level is IVRankLevel.VERY_LOW

    def test_none_rank(self) -> None:
        analyzer = IVRankAnalyzer()
        level, rank, conf = analyzer.analyze(make_snapshot(iv_rank=None))

        assert level is IVRankLevel.UNKNOWN
        assert rank is None
        assert conf == 0.0

    def test_out_of_range_high(self) -> None:
        analyzer = IVRankAnalyzer()
        level, rank, conf = analyzer.analyze(make_snapshot(iv_rank=150.0))

        assert level is IVRankLevel.UNKNOWN


# ---------------------------------------------------------------------------
# IVPercentileAnalyzer
# ---------------------------------------------------------------------------


class TestIVPercentileAnalyzer:
    def test_very_high_percentile(self) -> None:
        analyzer = IVPercentileAnalyzer()
        level, pctl, conf = analyzer.analyze(make_snapshot(iv_percentile=90.0))

        assert level is IVRankLevel.VERY_HIGH

    def test_high_percentile(self) -> None:
        analyzer = IVPercentileAnalyzer()
        level, pctl, conf = analyzer.analyze(make_snapshot(iv_percentile=70.0))

        assert level is IVRankLevel.HIGH

    def test_neutral_percentile(self) -> None:
        analyzer = IVPercentileAnalyzer()
        level, pctl, conf = analyzer.analyze(make_snapshot(iv_percentile=50.0))

        assert level is IVRankLevel.NEUTRAL

    def test_low_percentile(self) -> None:
        analyzer = IVPercentileAnalyzer()
        level, pctl, conf = analyzer.analyze(make_snapshot(iv_percentile=10.0))

        assert level is IVRankLevel.LOW

    def test_none_percentile(self) -> None:
        analyzer = IVPercentileAnalyzer()
        level, pctl, conf = analyzer.analyze(make_snapshot(iv_percentile=None))

        assert level is IVRankLevel.UNKNOWN
        assert pctl is None
        assert conf == 0.0

    def test_out_of_range_negative(self) -> None:
        analyzer = IVPercentileAnalyzer()
        level, pctl, conf = analyzer.analyze(make_snapshot(iv_percentile=-10.0))

        assert level is IVRankLevel.UNKNOWN


# ---------------------------------------------------------------------------
# VolatilityRegimeAnalyzer
# ---------------------------------------------------------------------------


class TestVolatilityRegimeAnalyzer:
    def test_expansion(self) -> None:
        analyzer = VolatilityRegimeAnalyzer()
        regime, buy, sell, conf = analyzer.analyze(
            make_snapshot(
                implied_volatility=0.40,
                historical_volatility=0.20,
                implied_volatilities=(0.20, 0.25, 0.35, 0.40),
            ),
            iv_trend=IVTrend.RISING,
        )

        assert regime is VolatilityRegime.EXPANSION
        assert sell

    def test_compression(self) -> None:
        analyzer = VolatilityRegimeAnalyzer()
        regime, buy, sell, conf = analyzer.analyze(
            make_snapshot(
                implied_volatility=0.15,
                historical_volatility=0.30,
                implied_volatilities=(0.30, 0.25, 0.20, 0.15),
            ),
            iv_trend=IVTrend.FALLING,
        )

        assert regime is VolatilityRegime.COMPRESSION
        assert buy

    def test_stable(self) -> None:
        analyzer = VolatilityRegimeAnalyzer()
        regime, buy, sell, conf = analyzer.analyze(
            make_snapshot(
                implied_volatility=0.25,
                historical_volatility=0.25,
                implied_volatilities=(0.25, 0.26, 0.25, 0.24),
            ),
            iv_trend=IVTrend.FLAT,
        )

        assert regime is VolatilityRegime.STABLE

    def test_transition_rising(self) -> None:
        analyzer = VolatilityRegimeAnalyzer()
        regime, buy, sell, conf = analyzer.analyze(
            make_snapshot(
                implied_volatility=0.25,
                historical_volatility=0.25,
                implied_volatilities=(0.20, 0.22, 0.24, 0.25),
            ),
            iv_trend=IVTrend.RISING,
        )

        assert regime is VolatilityRegime.TRANSITION

    def test_none_values(self) -> None:
        analyzer = VolatilityRegimeAnalyzer()
        regime, buy, sell, conf = analyzer.analyze(
            make_snapshot(
                implied_volatility=None,
                historical_volatility=None,
            ),
            iv_trend=IVTrend.UNKNOWN,
        )

        assert regime is VolatilityRegime.UNKNOWN
        assert conf == 0.0


# ---------------------------------------------------------------------------
# VolatilityAnalyzer (orchestrator)
# ---------------------------------------------------------------------------


class TestVolatilityAnalyzer:
    def test_full_analysis(self) -> None:
        analyzer = VolatilityAnalyzer()
        snapshot = make_snapshot(
            implied_volatility=0.30,
            historical_volatility=0.20,
            iv_rank=65.0,
            iv_percentile=60.0,
        )
        analysis = analyzer.analyze(snapshot)

        assert analysis.current_iv == 0.30
        assert analysis.current_hv == 0.20
        assert analysis.iv_rank == 65.0
        assert analysis.iv_percentile == 60.0
        assert analysis.confidence > 0.0

    def test_all_none_values(self) -> None:
        analyzer = VolatilityAnalyzer()
        snapshot = make_snapshot(
            implied_volatility=None,
            historical_volatility=None,
            iv_rank=None,
            iv_percentile=None,
        )
        analysis = analyzer.analyze(snapshot)

        assert analysis.current_iv is None
        assert analysis.current_hv is None
        assert analysis.iv_rank is None
        assert analysis.confidence == 0.0
        assert analysis.overall_bias is MarketBias.NEUTRAL

    def test_rejects_non_volatility_snapshot(self) -> None:
        analyzer = VolatilityAnalyzer()

        with pytest.raises(TypeError):
            analyzer.analyze(object())

    def test_generates_evidence(self) -> None:
        analyzer = VolatilityAnalyzer()
        snapshot = make_snapshot(
            implied_volatility=0.35,
            historical_volatility=0.20,
        )
        analysis = analyzer.analyze(snapshot)

        assert analysis.evidence is not None
        assert analysis.evidence.source == "Volatility"
        assert analysis.evidence.category.value == "option_chain"
        assert float(analysis.evidence.score) > 0.0
        assert float(analysis.evidence.confidence) > 0.0

    def test_generates_explanation(self) -> None:
        analyzer = VolatilityAnalyzer()
        snapshot = make_snapshot(
            implied_volatility=0.35,
            historical_volatility=0.20,
        )
        analysis = analyzer.analyze(snapshot)

        assert analysis.explanation is not None
        assert "Current implied volatility" in analysis.explanation.current_volatility
        assert analysis.explanation.historical_comparison
        assert analysis.explanation.iv_vs_hv
        assert analysis.explanation.regime
        assert analysis.explanation.risk
        assert analysis.explanation.institutional_interpretation

    def test_high_iv_produces_bearish_bias(self) -> None:
        analyzer = VolatilityAnalyzer()
        snapshot = make_snapshot(
            implied_volatility=0.60,
            historical_volatility=0.20,
        )
        analysis = analyzer.analyze(snapshot)

        assert analysis.iv_level is IVLevel.HIGH
        assert analysis.iv_vs_hv is IVHVRelation.IV_PREMIUM

    def test_low_iv_produces_bullish_bias(self) -> None:
        analyzer = VolatilityAnalyzer()
        snapshot = make_snapshot(
            implied_volatility=0.12,
            historical_volatility=0.20,
        )
        analysis = analyzer.analyze(snapshot)

        assert analysis.iv_level is IVLevel.LOW
        assert analysis.iv_vs_hv is IVHVRelation.IV_DISCOUNT

    def test_warnings_for_missing_data(self) -> None:
        analyzer = VolatilityAnalyzer()
        snapshot = make_snapshot(implied_volatility=None, historical_volatility=None)
        analysis = analyzer.analyze(snapshot)

        assert len(analysis.warnings) >= 2
        assert any("Implied volatility" in w for w in analysis.warnings)
        assert any("Historical volatility" in w for w in analysis.warnings)

    def test_preserves_metadata(self) -> None:
        analyzer = VolatilityAnalyzer()
        snapshot = make_snapshot()
        analysis = analyzer.analyze(snapshot)

        assert analysis.metadata["analyzer"] == "VolatilityAnalyzer"
        assert analysis.metadata["has_iv"]

    def test_evidence_signal_matches_bias(self) -> None:
        analyzer = VolatilityAnalyzer()
        snapshot = make_snapshot(
            implied_volatility=0.15,
            historical_volatility=0.30,
            implied_volatilities=(0.30, 0.25, 0.20, 0.15),
        )
        analysis = analyzer.analyze(snapshot)

        assert analysis.evidence is not None
        assert analysis.overall_bias is MarketBias.BULLISH

    def test_normal_iv_neutral(self) -> None:
        analyzer = VolatilityAnalyzer()
        snapshot = make_snapshot(
            implied_volatility=0.25,
            historical_volatility=0.25,
        )
        analysis = analyzer.analyze(snapshot)

        assert analysis.iv_level is IVLevel.NORMAL
        assert analysis.overall_bias is not None


# ---------------------------------------------------------------------------
# VolatilityExplanation
# ---------------------------------------------------------------------------


class TestVolatilityExplanation:
    def test_all_fields(self) -> None:
        explanation = VolatilityExplanation(
            current_volatility="IV is normal.",
            historical_comparison="HV is stable.",
            iv_vs_hv="IV ≈ HV.",
            regime="Stable.",
            risk="No warnings.",
            institutional_interpretation="Neutral stance.",
        )

        assert explanation.current_volatility == "IV is normal."
        assert explanation.regime == "Stable."
        assert explanation.warnings == ()


# ---------------------------------------------------------------------------
# forbidden imports
# ---------------------------------------------------------------------------


def test_volatility_has_no_forbidden_imports():
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
    volatility_files = (
        "iv.py",
        "hv.py",
        "iv_rank.py",
        "iv_percentile.py",
        "volatility_regime.py",
        "volatility.py",
        "surface.py",
        "surface_models.py",
        "smile.py",
    )

    for filename in volatility_files:
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
            ), (f"Forbidden import found in {path}: " f"{imported_names}")
