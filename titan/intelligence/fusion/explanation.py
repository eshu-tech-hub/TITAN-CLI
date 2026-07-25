from typing import Final

from titan.core.evidence.evidence import Evidence
from titan.core.evidence.models import EvidenceCategory

from titan.intelligence.fusion.models import (
    EvidenceConflict,
    IntelligenceFusion,
)

MIN_SUPPORTING_SCORE: Final = 50.0
MAX_WEAK_SCORE: Final = 30.0


class FusionExplainer:
    """Generates structured explanations for fusion results."""

    MIN_CONFIDENCE_EXPLANATION: Final = 0.3

    def explain(self, fusion: IntelligenceFusion) -> str:
        """Generate a structured explanation from a fusion result.

        Args:
            fusion: The completed intelligence fusion.

        Returns:
            A structured multi-section explanation string.
        """

        sections: list[str] = [
            "=== INTELLIGENCE FUSION EXPLANATION ===",
            "",
            self._format_overall(fusion),
            "",
            self._strongest_section(fusion.supporting_evidence),
            "",
            self._weakest_section(fusion.supporting_evidence),
            "",
            self._conflicts_section(fusion.conflicting_evidence),
            "",
            self._missing_section(fusion.missing_categories),
            "",
            self._assessment_section(fusion),
        ]

        return "\n".join(sections)

    def _format_overall(self, fusion: IntelligenceFusion) -> str:
        return (
            f"Overall Signal: {fusion.overall_signal.value}\n"
            f"Overall Score: {float(fusion.overall_score):.1f}/100\n"
            f"Overall Confidence: {float(fusion.overall_confidence):.2f}\n"
            f"Evidence Count: {fusion.evidence_count}\n"
            f"Conflicts Detected: {len(fusion.conflicting_evidence)}"
        )

    def _strongest_section(self, evidence_items: tuple[Evidence, ...]) -> str:
        best = self._strongest(evidence_items)

        if best is None:
            return "Strongest Evidence: None"

        return (
            f"Strongest Evidence:\n"
            f"  Source: {best.source}\n"
            f"  Category: {best.category.value}\n"
            f"  Score: {float(best.score):.1f}/100\n"
            f"  Confidence: {float(best.confidence):.2f}\n"
            f"  Signal: {best.signal.value}"
        )

    def _weakest_section(self, evidence_items: tuple[Evidence, ...]) -> str:
        worst = self._weakest(evidence_items)

        if worst is None:
            return "Weakest Evidence: None"

        return (
            f"Weakest Evidence:\n"
            f"  Source: {worst.source}\n"
            f"  Category: {worst.category.value}\n"
            f"  Score: {float(worst.score):.1f}/100\n"
            f"  Confidence: {float(worst.confidence):.2f}\n"
            f"  Signal: {worst.signal.value}"
        )

    def _conflicts_section(self, conflicts: tuple[EvidenceConflict, ...]) -> str:
        if not conflicts:
            return "Conflicts: None detected"

        lines: list[str] = ["Conflicts:"]

        for i, conflict in enumerate(conflicts, 1):
            lines.append(f"  {i}. {conflict.reason}")
            lines.append(f"     Type: {conflict.conflict_type.value}")
            lines.append(
                f"     Involves: {len(conflict.evidence_items)} evidence items"
            )

        return "\n".join(lines)

    def _missing_section(self, missing: tuple[EvidenceCategory, ...]) -> str:
        if not missing:
            return "Missing Information: All expected categories present"

        categories = ", ".join(cat.value for cat in missing)
        return f"Missing Information: {categories}"

    def _assessment_section(self, fusion: IntelligenceFusion) -> str:
        score = float(fusion.overall_score)
        confidence = float(fusion.overall_confidence)

        if score >= 60.0 and confidence >= self.MIN_CONFIDENCE_EXPLANATION:
            assessment = (
                "The fused intelligence shows a bullish bias with "
                f"{'high' if confidence > 0.7 else 'moderate'} confidence. "
                f"{len(fusion.supporting_evidence)} evidence items contribute "
                "to this assessment."
            )
        elif score <= 40.0 and confidence >= self.MIN_CONFIDENCE_EXPLANATION:
            assessment = (
                "The fused intelligence shows a bearish bias with "
                f"{'high' if confidence > 0.7 else 'moderate'} confidence. "
                f"{len(fusion.supporting_evidence)} evidence items contribute "
                "to this assessment."
            )
        else:
            assessment = (
                "The fused intelligence is neutral or uncertain. "
                "Confidence is too low or evidence is evenly balanced. "
                "Consider adding more evidence sources."
            )

        if fusion.conflicting_evidence:
            assessment += (
                f" {len(fusion.conflicting_evidence)} conflict(s) "
                "were detected and should be reviewed."
            )

        return f"Overall Assessment: {assessment}"

    def _strongest(self, evidence_items: tuple[Evidence, ...]) -> Evidence | None:
        if not evidence_items:
            return None

        return max(
            evidence_items,
            key=lambda e: (
                float(e.score) * float(e.confidence),
                float(e.confidence),
            ),
        )

    def _weakest(self, evidence_items: tuple[Evidence, ...]) -> Evidence | None:
        if not evidence_items:
            return None

        return min(
            evidence_items,
            key=lambda e: (
                float(e.score) * float(e.confidence),
                float(e.confidence),
            ),
        )
