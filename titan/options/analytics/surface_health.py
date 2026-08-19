from titan.options.analytics.models import (
    SurfaceHealth,
    SurfaceHealthLevel,
    VolatilitySurfaceInput,
)

HEALTHY_CONFIDENCE = 0.7
GOOD_CONFIDENCE = 0.5
CAUTION_CONFIDENCE = 0.3


class SurfaceHealthAnalyzer:
    """Evaluate overall volatility surface health.

    Assesses data availability, component confidence, and quality
    indicators to classify surface health as HEALTHY, GOOD, CAUTION,
    UNHEALTHY, or UNKNOWN.
    """

    name = "SurfaceHealthAnalyzer"

    def analyze(self, surface: VolatilitySurfaceInput) -> SurfaceHealth:
        if not isinstance(surface, VolatilitySurfaceInput):
            raise TypeError("surface must be a VolatilitySurfaceInput.")

        status: dict[str, str] = {}
        confidences: list[float] = []

        components = [
            ("Volatility", surface.volatility),
            ("Smile", surface.smile),
            ("Skew", surface.skew),
            ("Term Structure", surface.term_structure),
        ]

        for name, analysis in components:
            available = analysis is not None
            quality = self._component_quality(name, analysis)
            status[name] = quality
            if available and analysis is not None:
                confidences.append(analysis.confidence)

        available_count = sum(1 for _, a in components if a is not None)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        level, reason = self._classify(available_count, avg_confidence, confidences)

        return SurfaceHealth(level=level, reason=reason, component_status=status)

    def _component_quality(
        self,
        name: str,
        analysis: object | None,
    ) -> str:
        if analysis is None:
            return "missing"
        if hasattr(analysis, "confidence") and analysis.confidence is not None:
            if analysis.confidence >= HEALTHY_CONFIDENCE:
                return "healthy"
            if analysis.confidence >= GOOD_CONFIDENCE:
                return "good"
            if analysis.confidence >= CAUTION_CONFIDENCE:
                return "caution"
            return "low_confidence"
        return "unknown"

    def _classify(
        self,
        available_count: int,
        avg_confidence: float,
        confidences: list[float],
    ) -> tuple[SurfaceHealthLevel, str]:
        if available_count == 0:
            return (
                SurfaceHealthLevel.UNKNOWN,
                "No volatility intelligence components available.",
            )

        if available_count == 4 and avg_confidence >= HEALTHY_CONFIDENCE:
            min_conf = min(confidences)
            if min_conf >= HEALTHY_CONFIDENCE:
                return (
                    SurfaceHealthLevel.HEALTHY,
                    (f"All {available_count} components healthy "
                    f"(avg confidence {avg_confidence:.0%})."),
                )

        if available_count >= 3 and avg_confidence >= GOOD_CONFIDENCE:
            return (
                SurfaceHealthLevel.GOOD,
                (f"Surface is functional with {available_count}/4 components "
                f"(avg confidence {avg_confidence:.0%})."),
            )

        if available_count >= 2:
            return (
                SurfaceHealthLevel.CAUTION,
                (f"Surface quality is degraded: {available_count}/4 components, "
                f"avg confidence {avg_confidence:.0%}. Review component warnings."),
            )

        return (
            SurfaceHealthLevel.UNHEALTHY,
            (f"Surface is compromised: only {available_count}/4 components "
            f"available with avg confidence {avg_confidence:.0%}."),
        )
