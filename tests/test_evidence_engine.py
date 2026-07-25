import ast
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceAggregator,
    EvidenceCategory,
    EvidenceSignal,
    EvidenceValidationError,
    Score,
)


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


def test_score_accepts_valid_range():
    assert float(Score(0)) == 0
    assert float(Score(100)) == 100
    assert float(Score(55.5)) == 55.5


@pytest.mark.parametrize("value", [-0.1, 100.1])
def test_score_rejects_invalid_range(value: float):
    with pytest.raises(EvidenceValidationError):
        Score(value)


def test_confidence_accepts_valid_range():
    assert float(Confidence(0.0)) == 0.0
    assert float(Confidence(1.0)) == 1.0
    assert float(Confidence(0.75)) == 0.75


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_confidence_rejects_invalid_range(value: float):
    with pytest.raises(EvidenceValidationError):
        Confidence(value)


def test_evidence_model_fields():
    timestamp = datetime(2026, 6, 22, 9, 15)
    evidence = make_evidence(timestamp=timestamp)

    assert evidence.source == "test"
    assert evidence.category is EvidenceCategory.INDICATOR
    assert evidence.signal is EvidenceSignal.NEUTRAL
    assert evidence.score == Score(50.0)
    assert evidence.confidence == Confidence(0.5)
    assert evidence.weight == 1.0
    assert evidence.reasons == ("reason",)
    assert evidence.warnings == ("warning",)
    assert evidence.metadata["source"] == "test"
    assert evidence.timestamp == timestamp


def test_evidence_rejects_empty_source():
    with pytest.raises(EvidenceValidationError):
        make_evidence(source=" ")


def test_evidence_rejects_negative_weight():
    with pytest.raises(EvidenceValidationError):
        make_evidence(weight=-1.0)


def test_evidence_requires_score_object():
    with pytest.raises(EvidenceValidationError):
        Evidence(
            source="test",
            category=EvidenceCategory.INDICATOR,
            signal=EvidenceSignal.NEUTRAL,
            score=50.0,
            confidence=Confidence(0.5),
        )


def test_evidence_requires_confidence_object():
    with pytest.raises(EvidenceValidationError):
        Evidence(
            source="test",
            category=EvidenceCategory.INDICATOR,
            signal=EvidenceSignal.NEUTRAL,
            score=Score(50.0),
            confidence=0.5,
        )


def test_aggregator_add_extend_and_clear():
    aggregator = EvidenceAggregator()
    first = make_evidence(source="first")
    second = make_evidence(source="second")

    aggregator.add(first)
    aggregator.extend((second,))

    assert aggregator.summary().metadata["count"] == 2

    aggregator.clear()

    assert aggregator.summary().metadata["count"] == 0


def test_aggregator_rejects_non_evidence():
    aggregator = EvidenceAggregator()

    with pytest.raises(EvidenceValidationError):
        aggregator.add(object())


def test_empty_aggregation_defaults():
    aggregator = EvidenceAggregator()
    summary = aggregator.summary()

    assert aggregator.overall_score() == 50.0
    assert aggregator.overall_confidence() == 0.0
    assert aggregator.overall_signal() is EvidenceSignal.UNKNOWN
    assert summary.signal is EvidenceSignal.UNKNOWN
    assert summary.score == Score(50.0)
    assert summary.confidence == Confidence(0.0)
    assert summary.warnings == ("No evidence items available.",)


def test_overall_score_is_weighted_average():
    aggregator = EvidenceAggregator()
    aggregator.extend(
        (
            make_evidence(score=80.0, weight=3.0),
            make_evidence(score=20.0, weight=1.0),
        )
    )

    assert aggregator.overall_score() == 65.0


def test_overall_score_defaults_when_total_weight_is_zero():
    aggregator = EvidenceAggregator()
    aggregator.extend(
        (
            make_evidence(score=80.0, weight=0.0),
            make_evidence(score=20.0, weight=0.0),
        )
    )

    assert aggregator.overall_score() == 50.0


def test_overall_confidence_is_weighted_average():
    aggregator = EvidenceAggregator()
    aggregator.extend(
        (
            make_evidence(confidence=0.9, weight=3.0),
            make_evidence(confidence=0.1, weight=1.0),
        )
    )

    assert aggregator.overall_confidence() == pytest.approx(0.7)


def test_overall_confidence_defaults_when_total_weight_is_zero():
    aggregator = EvidenceAggregator()
    aggregator.extend(
        (
            make_evidence(confidence=0.9, weight=0.0),
            make_evidence(confidence=0.1, weight=0.0),
        )
    )

    assert aggregator.overall_confidence() == 0.0


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (85.0, EvidenceSignal.VERY_BULLISH),
        (65.0, EvidenceSignal.BULLISH),
        (50.0, EvidenceSignal.NEUTRAL),
        (35.0, EvidenceSignal.BEARISH),
        (15.0, EvidenceSignal.VERY_BEARISH),
    ],
)
def test_overall_signal_determination(score: float, expected: EvidenceSignal):
    aggregator = EvidenceAggregator()
    aggregator.add(make_evidence(score=score))

    assert aggregator.overall_signal() is expected


def test_group_by_category_sorts_newest_first():
    older = datetime(2026, 6, 22, 9, 15)
    newer = older + timedelta(minutes=5)
    aggregator = EvidenceAggregator()
    indicator = make_evidence(
        source="indicator",
        category=EvidenceCategory.INDICATOR,
        timestamp=older,
    )
    news = make_evidence(
        source="news",
        category=EvidenceCategory.NEWS,
        timestamp=older,
    )
    newer_indicator = make_evidence(
        source="newer_indicator",
        category=EvidenceCategory.INDICATOR,
        timestamp=newer,
    )

    aggregator.extend((indicator, news, newer_indicator))
    grouped = aggregator.group_by_category()

    assert set(grouped) == {EvidenceCategory.INDICATOR, EvidenceCategory.NEWS}
    assert grouped[EvidenceCategory.INDICATOR] == (newer_indicator, indicator)
    assert grouped[EvidenceCategory.NEWS] == (news,)


def test_summary_returns_evidence_object():
    aggregator = EvidenceAggregator()
    aggregator.add(make_evidence(score=85.0, confidence=0.8))

    summary = aggregator.summary()

    assert isinstance(summary, Evidence)
    assert summary.source == "EvidenceAggregator"
    assert summary.category is EvidenceCategory.SYSTEM
    assert summary.signal is EvidenceSignal.VERY_BULLISH
    assert summary.score == Score(85.0)
    assert summary.confidence == Confidence(0.8)
    assert summary.metadata["count"] == 1


def test_evidence_engine_has_no_forbidden_imports():
    evidence_dir = Path("titan/core/evidence")
    forbidden_terms = (
        "angel_one",
        "smartapi",
        "smartconnect",
        "broker",
        "options",
        "market",
        "analysis",
    )

    for path in evidence_dir.glob("*.py"):
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
