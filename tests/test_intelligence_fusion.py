import ast
from datetime import datetime
from pathlib import Path

import pytest

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    EvidenceValidationError,
    Score,
)
from titan.intelligence.fusion import (
    ConflictType,
    EqualWeightProvider,
    EvidenceConflict,
    EvidenceWeight,
    FusionEngine,
    FusionEngineError,
    FusionError,
    FusionExplainer,
    FusionValidationError,
    IntelligenceFusion,
    StaticWeightProvider,
    check_missing_categories,
    validate_evidence,
    validate_evidence_list,
    validate_weights,
)
from titan.intelligence.fusion.weighting import WeightProvider

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def make_evidence(
    *,
    source: str = "test",
    category: EvidenceCategory = EvidenceCategory.INDICATOR,
    signal: EvidenceSignal = EvidenceSignal.NEUTRAL,
    score: float = 50.0,
    confidence: float = 0.5,
    weight: float = 1.0,
    timestamp: datetime | None = None,
) -> Evidence:
    return Evidence(
        source=source,
        category=category,
        signal=signal,
        score=Score(score),
        confidence=Confidence(confidence),
        weight=weight,
        reasons=("reason",),
        warnings=("warning",),
        metadata={"source": source},
        timestamp=timestamp or datetime(2026, 6, 22, 9, 15),
    )


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------


class TestIntelligenceFusion:
    def test_default_fields(self) -> None:
        fusion = IntelligenceFusion(
            overall_score=Score(50.0),
            overall_confidence=Confidence(0.5),
            overall_signal=EvidenceSignal.NEUTRAL,
        )

        assert float(fusion.overall_score) == 50.0
        assert float(fusion.overall_confidence) == 0.5
        assert fusion.overall_signal is EvidenceSignal.NEUTRAL
        assert fusion.supporting_evidence == ()
        assert fusion.conflicting_evidence == ()
        assert fusion.missing_categories == ()
        assert fusion.warnings == ()
        assert fusion.metadata == {}
        assert fusion.evidence_count == 0
        assert fusion.explanation is None

    def test_frozen(self) -> None:
        fusion = IntelligenceFusion(
            overall_score=Score(50.0),
            overall_confidence=Confidence(0.5),
            overall_signal=EvidenceSignal.NEUTRAL,
        )

        with pytest.raises(AttributeError):
            fusion.overall_score = Score(60.0)


class TestEvidenceWeight:
    def test_default_weight_is_one(self) -> None:
        w = EvidenceWeight(category=EvidenceCategory.INDICATOR)

        assert w.category is EvidenceCategory.INDICATOR
        assert w.weight == 1.0
        assert w.enabled

    def test_custom_weight(self) -> None:
        w = EvidenceWeight(category=EvidenceCategory.NEWS, weight=2.5, enabled=False)

        assert w.weight == 2.5
        assert not w.enabled

    def test_frozen(self) -> None:
        w = EvidenceWeight(category=EvidenceCategory.INDICATOR)

        with pytest.raises(AttributeError):
            w.weight = 2.0


class TestEvidenceConflict:
    def test_fields(self) -> None:
        e1 = make_evidence()
        e2 = make_evidence(source="other")
        conflict = EvidenceConflict(
            conflict_type=ConflictType.BULLISH_VS_BEARISH,
            reason="test conflict",
            evidence_items=(e1, e2),
        )

        assert conflict.conflict_type is ConflictType.BULLISH_VS_BEARISH
        assert conflict.reason == "test conflict"
        assert conflict.evidence_items == (e1, e2)


# ---------------------------------------------------------------------------
# exceptions
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_fusion_error_is_base(self) -> None:
        assert issubclass(FusionValidationError, FusionError)
        assert issubclass(FusionEngineError, FusionError)

    def test_fusion_validation_error_is_value_error(self) -> None:
        assert issubclass(FusionValidationError, ValueError)


# ---------------------------------------------------------------------------
# validator
# ---------------------------------------------------------------------------


class TestValidator:
    def test_validate_evidence_passes_for_valid(self) -> None:
        validate_evidence(make_evidence())

    def test_validate_evidence_rejects_non_evidence(self) -> None:
        with pytest.raises(FusionValidationError):
            validate_evidence(object())

    def test_validate_evidence_rejects_empty_source(self) -> None:
        with pytest.raises(EvidenceValidationError):
            validate_evidence(make_evidence(source=" "))

    def test_validate_evidence_list_passes(self) -> None:
        validate_evidence_list([make_evidence(source="a"), make_evidence(source="b")])

    def test_validate_evidence_list_rejects_invalid_item(self) -> None:
        with pytest.raises(EvidenceValidationError):
            validate_evidence_list([make_evidence(source=" ")])

    def test_validate_weights_passes(self) -> None:
        validate_weights(
            [
                EvidenceWeight(category=EvidenceCategory.INDICATOR, weight=1.0),
                EvidenceWeight(category=EvidenceCategory.NEWS, weight=0.5),
            ]
        )

    def test_validate_weights_rejects_negative(self) -> None:
        with pytest.raises(FusionValidationError):
            validate_weights(
                [EvidenceWeight(category=EvidenceCategory.INDICATOR, weight=-1.0)]
            )

    def test_check_missing_categories_none_missing(self) -> None:
        items = [
            make_evidence(category=EvidenceCategory.OPTION_CHAIN),
            make_evidence(category=EvidenceCategory.INDICATOR),
            make_evidence(category=EvidenceCategory.PRICE_ACTION),
        ]
        missing = check_missing_categories(
            items,
            [EvidenceCategory.OPTION_CHAIN, EvidenceCategory.INDICATOR],
        )

        assert missing == ()

    def test_check_missing_categories_some_missing(self) -> None:
        items = [make_evidence(category=EvidenceCategory.INDICATOR)]
        missing = check_missing_categories(
            items,
            [
                EvidenceCategory.OPTION_CHAIN,
                EvidenceCategory.INDICATOR,
                EvidenceCategory.PRICE_ACTION,
            ],
        )

        assert EvidenceCategory.OPTION_CHAIN in missing
        assert EvidenceCategory.PRICE_ACTION in missing
        assert EvidenceCategory.INDICATOR not in missing


# ---------------------------------------------------------------------------
# weighting
# ---------------------------------------------------------------------------


class TestEqualWeightProvider:
    def test_always_returns_one(self) -> None:
        provider = EqualWeightProvider()

        assert provider.get_weight(make_evidence()) == 1.0
        assert (
            provider.get_weight(make_evidence(category=EvidenceCategory.OPTION_CHAIN))
            == 1.0
        )

    def test_is_weight_provider(self) -> None:
        assert isinstance(EqualWeightProvider(), WeightProvider)


class TestStaticWeightProvider:
    def test_returns_configured_weight(self) -> None:
        provider = StaticWeightProvider(
            [
                EvidenceWeight(category=EvidenceCategory.INDICATOR, weight=2.0),
                EvidenceWeight(category=EvidenceCategory.NEWS, weight=0.5),
            ]
        )

        assert (
            provider.get_weight(make_evidence(category=EvidenceCategory.INDICATOR))
            == 2.0
        )
        assert provider.get_weight(make_evidence(category=EvidenceCategory.NEWS)) == 0.5

    def test_returns_zero_for_unconfigured_category(self) -> None:
        provider = StaticWeightProvider([])

        assert (
            provider.get_weight(make_evidence(category=EvidenceCategory.OPTION_CHAIN))
            == 0.0
        )

    def test_returns_zero_for_disabled_category(self) -> None:
        provider = StaticWeightProvider(
            [
                EvidenceWeight(
                    category=EvidenceCategory.INDICATOR,
                    weight=2.0,
                    enabled=False,
                )
            ]
        )

        assert (
            provider.get_weight(make_evidence(category=EvidenceCategory.INDICATOR))
            == 0.0
        )

    def test_is_weight_provider(self) -> None:
        assert isinstance(
            StaticWeightProvider([EvidenceWeight(category=EvidenceCategory.INDICATOR)]),
            WeightProvider,
        )


# ---------------------------------------------------------------------------
# FusionEngine — evidence management
# ---------------------------------------------------------------------------


class TestFusionEngineEvidenceManagement:
    def test_add_evidence(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence())

        assert engine.summary().metadata["count"] == 1

    def test_add_evidence_rejects_non_evidence(self) -> None:
        engine = FusionEngine()

        with pytest.raises(FusionEngineError):
            engine.add_evidence(object())

    def test_add_evidence_rejects_duplicate_source_and_category(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(
            make_evidence(
                source="src",
                category=EvidenceCategory.INDICATOR,
            )
        )

        with pytest.raises(FusionEngineError, match="Duplicate"):
            engine.add_evidence(
                make_evidence(
                    source="src",
                    category=EvidenceCategory.INDICATOR,
                )
            )

    def test_add_evidence_allows_same_source_different_category(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(
            make_evidence(
                source="src",
                category=EvidenceCategory.INDICATOR,
            )
        )
        engine.add_evidence(
            make_evidence(
                source="src",
                category=EvidenceCategory.NEWS,
            )
        )

        assert engine.summary().metadata["count"] == 2

    def test_remove_evidence_by_source(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence(source="keep"))
        engine.add_evidence(
            make_evidence(source="remove", category=EvidenceCategory.OPTION_CHAIN)
        )
        engine.add_evidence(
            make_evidence(source="remove", category=EvidenceCategory.NEWS)
        )

        removed = engine.remove_evidence("remove")

        assert removed == 2
        assert engine.summary().metadata["count"] == 1

    def test_remove_evidence_by_source_and_category(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(
            make_evidence(source="src", category=EvidenceCategory.INDICATOR)
        )
        engine.add_evidence(make_evidence(source="src", category=EvidenceCategory.NEWS))

        removed = engine.remove_evidence("src", EvidenceCategory.INDICATOR)

        assert removed == 1
        assert engine.summary().metadata["count"] == 1

    def test_remove_evidence_returns_zero_when_no_match(self) -> None:
        engine = FusionEngine()

        assert engine.remove_evidence("nonexistent") == 0

    def test_clear(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence())
        engine.add_evidence(make_evidence(source="other"))
        engine.clear()

        assert engine.summary().metadata["count"] == 0


# ---------------------------------------------------------------------------
# FusionEngine — validation
# ---------------------------------------------------------------------------


class TestFusionEngineValidation:
    def test_validate_returns_empty_when_all_good(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence(confidence=0.8, score=75.0))

        assert engine.validate() == []

    def test_validate_detects_low_confidence(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence(confidence=0.05))

        warnings = engine.validate()

        assert len(warnings) == 1
        assert "low confidence" in warnings[0].lower()

    def test_validate_detects_excessive_confidence(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence(confidence=0.995))

        warnings = engine.validate()

        assert len(warnings) == 1
        assert "excessive confidence" in warnings[0].lower()

    def test_validate_no_evidence_no_warnings(self) -> None:
        engine = FusionEngine()

        assert engine.validate() == []


# ---------------------------------------------------------------------------
# FusionEngine — fusion
# ---------------------------------------------------------------------------


class TestFusionEngineFuse:
    def test_empty_fusion(self) -> None:
        engine = FusionEngine()
        fusion = engine.fuse()

        assert float(fusion.overall_score) == 50.0
        assert float(fusion.overall_confidence) == 0.0
        assert fusion.overall_signal is EvidenceSignal.UNKNOWN
        assert fusion.evidence_count == 0
        assert "No evidence" in fusion.warnings[0]

    def test_single_evidence(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(
            make_evidence(
                source="src",
                score=75.0,
                confidence=0.8,
                signal=EvidenceSignal.BULLISH,
            )
        )
        fusion = engine.fuse()

        assert float(fusion.overall_score) == pytest.approx(75.0)
        assert float(fusion.overall_confidence) == pytest.approx(0.8)
        assert fusion.overall_signal is EvidenceSignal.BULLISH
        assert fusion.evidence_count == 1
        assert len(fusion.supporting_evidence) == 1

    def test_multiple_evidence_weighted_average(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(
            make_evidence(
                source="bullish",
                score=90.0,
                confidence=0.9,
                signal=EvidenceSignal.VERY_BULLISH,
            )
        )
        engine.add_evidence(
            make_evidence(
                source="bearish",
                score=10.0,
                confidence=0.1,
                signal=EvidenceSignal.VERY_BEARISH,
            )
        )
        fusion = engine.fuse()

        assert float(fusion.overall_score) == pytest.approx(50.0)
        assert float(fusion.overall_confidence) == pytest.approx(0.5)
        assert fusion.overall_signal is EvidenceSignal.NEUTRAL

    def test_conflicting_evidence_detected(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(
            make_evidence(
                source="bull",
                score=85.0,
                signal=EvidenceSignal.BULLISH,
                confidence=0.7,
            )
        )
        engine.add_evidence(
            make_evidence(
                source="bear",
                score=15.0,
                signal=EvidenceSignal.BEARISH,
                confidence=0.7,
            )
        )
        fusion = engine.fuse()

        assert len(fusion.conflicting_evidence) >= 1
        assert any(
            c.conflict_type is ConflictType.BULLISH_VS_BEARISH
            for c in fusion.conflicting_evidence
        )

    def test_missing_categories_detected(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence(category=EvidenceCategory.INDICATOR))
        fusion = engine.fuse()

        assert EvidenceCategory.OPTION_CHAIN in fusion.missing_categories
        assert EvidenceCategory.PRICE_ACTION in fusion.missing_categories

    def test_static_weights_affect_score(self) -> None:
        provider = StaticWeightProvider(
            [
                EvidenceWeight(category=EvidenceCategory.INDICATOR, weight=3.0),
                EvidenceWeight(category=EvidenceCategory.NEWS, weight=1.0),
            ]
        )
        engine = FusionEngine(weight_provider=provider)
        engine.add_evidence(
            make_evidence(
                source="indicator",
                category=EvidenceCategory.INDICATOR,
                score=100.0,
                confidence=1.0,
                signal=EvidenceSignal.VERY_BULLISH,
            )
        )
        engine.add_evidence(
            make_evidence(
                source="news",
                category=EvidenceCategory.NEWS,
                score=0.0,
                confidence=1.0,
                signal=EvidenceSignal.VERY_BEARISH,
            )
        )
        fusion = engine.fuse()

        assert float(fusion.overall_score) == pytest.approx(75.0)

    def test_fusion_includes_warnings_from_validation(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence(confidence=0.05))

        fusion = engine.fuse()

        assert len(fusion.warnings) >= 1

    def test_fuse_is_idempotent(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence(score=75.0, confidence=0.8))

        first = engine.fuse()
        second = engine.fuse()

        assert float(first.overall_score) == float(second.overall_score)


# ---------------------------------------------------------------------------
# FusionEngine — summary
# ---------------------------------------------------------------------------


class TestFusionEngineSummary:
    def test_summary_returns_evidence(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence(score=85.0, confidence=0.8))

        summary = engine.summary()

        assert isinstance(summary, Evidence)
        assert summary.source == "FusionEngine"
        assert summary.category is EvidenceCategory.SYSTEM
        assert summary.metadata["count"] == 1

    def test_summary_empty(self) -> None:
        engine = FusionEngine()
        summary = engine.summary()

        assert summary.signal is EvidenceSignal.UNKNOWN
        assert float(summary.score) == 50.0
        assert float(summary.confidence) == 0.0
        assert summary.metadata["count"] == 0
        assert "No evidence" in summary.reasons[0]

    def test_summary_includes_conflict_count(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(
            make_evidence(
                source="a",
                score=80.0,
                signal=EvidenceSignal.BULLISH,
                confidence=0.7,
            )
        )
        engine.add_evidence(
            make_evidence(
                source="b",
                score=20.0,
                signal=EvidenceSignal.BEARISH,
                confidence=0.7,
            )
        )

        summary = engine.summary()

        assert summary.metadata["conflicts"] >= 1


# ---------------------------------------------------------------------------
# FusionEngine — explanation
# ---------------------------------------------------------------------------


class TestFusionEngineExplanation:
    def test_to_explanation_returns_string(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence(score=75.0, confidence=0.8))

        explanation = engine.to_explanation()

        assert isinstance(explanation, str)
        assert "INTELLIGENCE FUSION EXPLANATION" in explanation
        assert "Overall Signal" in explanation
        assert "Strongest Evidence" in explanation
        assert "Weakest Evidence" in explanation
        assert "Conflicts" in explanation
        assert "Overall Assessment" in explanation

    def test_to_explanation_empty(self) -> None:
        engine = FusionEngine()

        explanation = engine.to_explanation()

        assert "Evidence Count: 0" in explanation
        assert "Strongest Evidence: None" in explanation
        assert "Weakest Evidence: None" in explanation


# ---------------------------------------------------------------------------
# FusionExplainer
# ---------------------------------------------------------------------------


class TestFusionExplainer:
    def test_explain_returns_all_sections(self) -> None:
        explainer = FusionExplainer()
        fusion = IntelligenceFusion(
            overall_score=Score(75.0),
            overall_confidence=Confidence(0.8),
            overall_signal=EvidenceSignal.BULLISH,
            supporting_evidence=(
                make_evidence(
                    source="src",
                    score=75.0,
                    confidence=0.8,
                    signal=EvidenceSignal.BULLISH,
                ),
            ),
            evidence_count=1,
        )
        result = explainer.explain(fusion)

        assert "Strongest Evidence" in result
        assert "Weakest Evidence" in result
        assert "Overall Assessment" in result

    def test_explain_bullish_assessment(self) -> None:
        explainer = FusionExplainer()
        fusion = IntelligenceFusion(
            overall_score=Score(85.0),
            overall_confidence=Confidence(0.9),
            overall_signal=EvidenceSignal.VERY_BULLISH,
            supporting_evidence=(
                make_evidence(
                    score=85.0, confidence=0.9, signal=EvidenceSignal.BULLISH
                ),
            ),
            evidence_count=1,
        )
        result = explainer.explain(fusion)

        assert "bullish" in result.lower()

    def test_explain_bearish_assessment(self) -> None:
        explainer = FusionExplainer()
        fusion = IntelligenceFusion(
            overall_score=Score(15.0),
            overall_confidence=Confidence(0.8),
            overall_signal=EvidenceSignal.VERY_BEARISH,
            supporting_evidence=(
                make_evidence(
                    score=15.0, confidence=0.8, signal=EvidenceSignal.BEARISH
                ),
            ),
            evidence_count=1,
        )
        result = explainer.explain(fusion)

        assert "bearish" in result.lower()

    def test_explain_neutral_assessment(self) -> None:
        explainer = FusionExplainer()
        fusion = IntelligenceFusion(
            overall_score=Score(50.0),
            overall_confidence=Confidence(0.1),
            overall_signal=EvidenceSignal.NEUTRAL,
            evidence_count=0,
        )
        result = explainer.explain(fusion)

        assert "neutral" in result.lower() or "uncertain" in result.lower()

    def test_explain_mentions_conflicts(self) -> None:
        explainer = FusionExplainer()
        conflict = EvidenceConflict(
            conflict_type=ConflictType.BULLISH_VS_BEARISH,
            reason="Test conflict",
            evidence_items=(),
        )
        fusion = IntelligenceFusion(
            overall_score=Score(50.0),
            overall_confidence=Confidence(0.5),
            overall_signal=EvidenceSignal.NEUTRAL,
            conflicting_evidence=(conflict,),
            evidence_count=0,
        )
        result = explainer.explain(fusion)

        assert "Conflicts" in result
        assert "Test conflict" in result


# ---------------------------------------------------------------------------
# conflict detection edge cases
# ---------------------------------------------------------------------------


class TestConflictDetection:
    def test_no_conflict_when_all_same_direction(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(
            make_evidence(
                source="a",
                signal=EvidenceSignal.BULLISH,
                score=70.0,
                confidence=0.6,
            )
        )
        engine.add_evidence(
            make_evidence(
                source="b",
                signal=EvidenceSignal.BULLISH,
                score=80.0,
                confidence=0.7,
            )
        )
        fusion = engine.fuse()

        assert all(
            c.conflict_type is not ConflictType.BULLISH_VS_BEARISH
            for c in fusion.conflicting_evidence
        )

    def test_low_confidence_conflict(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence(confidence=0.05))

        fusion = engine.fuse()

        assert any(
            c.conflict_type is ConflictType.LOW_CONFIDENCE
            for c in fusion.conflicting_evidence
        )

    def test_no_low_confidence_conflict_when_all_good(self) -> None:
        engine = FusionEngine()
        engine.add_evidence(make_evidence(confidence=0.5))

        fusion = engine.fuse()

        assert not any(
            c.conflict_type is ConflictType.LOW_CONFIDENCE
            for c in fusion.conflicting_evidence
        )


# ---------------------------------------------------------------------------
# WeightProvider interface
# ---------------------------------------------------------------------------


class TestWeightProviderInterface:
    def test_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            WeightProvider()


# ---------------------------------------------------------------------------
# forbidden imports — fusion must not depend on broker, options, market, etc.
# ---------------------------------------------------------------------------


def test_fusion_has_no_forbidden_imports():
    fusion_dir = Path("titan/intelligence/fusion")
    forbidden_terms = (
        "yfinance",
        "yfinance",
        "smartconnect",
        "broker",
        "options",
        "market",
        "analysis",
        "indicator",
        "portfolio",
        "risk",
    )

    for path in fusion_dir.glob("*.py"):
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
