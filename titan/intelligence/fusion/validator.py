from collections.abc import Sequence

from titan.core.evidence.evidence import Evidence
from titan.core.evidence.models import EvidenceCategory

from titan.intelligence.fusion.exceptions import FusionValidationError
from titan.intelligence.fusion.models import EvidenceWeight

MIN_CONFIDENCE_THRESHOLD = 0.1
MAX_CONFIDENCE_WARNING = 0.99


def validate_evidence(evidence: Evidence) -> None:
    """Validate a single evidence item for fusion.

    Args:
        evidence: The evidence item to validate.

    Raises:
        FusionValidationError: If the evidence item is invalid.
    """

    if not isinstance(evidence, Evidence):
        raise FusionValidationError("Fusion requires Evidence objects.")

    if not evidence.source.strip():
        raise FusionValidationError("Evidence source must not be empty.")


def validate_evidence_list(evidence_items: Sequence[Evidence]) -> None:
    """Validate a list of evidence items.

    Args:
        evidence_items: The evidence items to validate.

    Raises:
        FusionValidationError: If any evidence item is invalid.
    """

    for evidence in evidence_items:
        validate_evidence(evidence)


def validate_weights(weights: Sequence[EvidenceWeight]) -> None:
    """Validate weight configuration.

    Args:
        weights: The weight configurations to validate.

    Raises:
        FusionValidationError: If any weight is invalid.
    """

    for w in weights:
        if w.weight < 0.0:
            raise FusionValidationError(
                f"Weight for {w.category} must be non-negative."
            )


def check_missing_categories(
    evidence_items: Sequence[Evidence],
    required_categories: Sequence[EvidenceCategory],
) -> tuple[EvidenceCategory, ...]:
    """Identify required categories missing from the evidence set.

    Args:
        evidence_items: Available evidence items.
        required_categories: Categories that are required.

    Returns:
        Tuple of missing categories.
    """

    present: set[EvidenceCategory] = {e.category for e in evidence_items}
    return tuple(cat for cat in required_categories if cat not in present)


def has_low_confidence(evidence: Evidence) -> bool:
    """Check if an evidence item has low confidence.

    Args:
        evidence: The evidence item to check.

    Returns:
        True if confidence is below the threshold.
    """

    return float(evidence.confidence) < MIN_CONFIDENCE_THRESHOLD


def has_excessive_confidence(evidence: Evidence) -> bool:
    """Check if an evidence item has unrealistically high confidence.

    Args:
        evidence: The evidence item to check.

    Returns:
        True if confidence exceeds the warning threshold.
    """

    return float(evidence.confidence) > MAX_CONFIDENCE_WARNING
