from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from titan.core.evidence.confidence import Confidence
from titan.core.evidence.evidence import Evidence
from titan.core.evidence.models import EvidenceCategory, EvidenceSignal
from titan.core.evidence.score import Score


class ConflictType(str, Enum):
    """Categories of evidence conflicts detected during fusion."""

    BULLISH_VS_BEARISH = "bullish_vs_bearish"
    LOW_CONFIDENCE = "low_confidence"
    DUPLICATE_SOURCE = "duplicate_source"
    MISSING_CATEGORY = "missing_category"


@dataclass(frozen=True, slots=True)
class EvidenceWeight:
    """Weight configuration for an evidence category.

    Attributes:
        category: Target evidence category.
        weight: Aggregation weight multiplier.
        enabled: Whether this category is active in fusion.
    """

    category: EvidenceCategory
    weight: float = 1.0
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class EvidenceConflict:
    """A detected conflict between evidence items.

    Attributes:
        conflict_type: Classification of the conflict.
        reason: Human-readable description.
        evidence_items: The conflicting evidence items.
    """

    conflict_type: ConflictType
    reason: str
    evidence_items: tuple[Evidence, ...]


@dataclass(frozen=True, slots=True)
class IntelligenceFusion:
    """The unified intelligence output from the Fusion Engine.

    Attributes:
        overall_score: Weighted aggregate score (0-100).
        overall_confidence: Weighted aggregate confidence (0.0-1.0).
        overall_signal: Aggregate directional signal.
        supporting_evidence: Evidence items that support the overall signal.
        conflicting_evidence: Detected conflicts between evidence items.
        missing_categories: Categories expected but not present.
        warnings: Non-fatal fusion warnings.
        metadata: Producer-owned context.
        timestamp: Fusion computation timestamp.
        evidence_count: Total number of evidence items fused.
        explanation: Structured explanation string, populated by to_explanation().
    """

    overall_score: Score
    overall_confidence: Confidence
    overall_signal: EvidenceSignal
    supporting_evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    conflicting_evidence: tuple[EvidenceConflict, ...] = field(default_factory=tuple)
    missing_categories: tuple[EvidenceCategory, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    evidence_count: int = 0
    explanation: str | None = None
