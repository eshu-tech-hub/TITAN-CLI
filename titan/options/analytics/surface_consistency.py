from titan.core.evidence import EvidenceSignal

from titan.options.analytics.models import (
    MarketBias,
    SurfaceConsistency,
    SurfaceConsistencyLevel,
    VolatilitySurfaceInput,
)


class SurfaceConsistencyAnalyzer:
    """Evaluate cross-module signal consistency across the volatility surface.

    Compares directional signals from Volatility, Smile, Skew, and
    Term Structure analyzers to determine whether they agree,
    partially agree, or conflict.
    """

    name = "SurfaceConsistencyAnalyzer"

    def analyze(self, surface: VolatilitySurfaceInput) -> SurfaceConsistency:
        if not isinstance(surface, VolatilitySurfaceInput):
            raise TypeError("surface must be a VolatilitySurfaceInput.")

        signals: list[tuple[str, EvidenceSignal | None]] = []

        signals.append(("Volatility", self._get_signal(surface.volatility)))
        signals.append(("Smile", self._get_signal(surface.smile)))
        signals.append(("Skew", self._get_signal(surface.skew)))
        signals.append(("Term Structure", self._get_signal(surface.term_structure)))

        available: list[tuple[str, EvidenceSignal]] = [
            (n, s)
            for n, s in signals
            if s is not None and s is not EvidenceSignal.UNKNOWN
        ]

        if not available:
            return SurfaceConsistency(
                level=SurfaceConsistencyLevel.UNKNOWN,
                details="No component signals available for consistency check.",
            )

        level, details, conflicts = self._assess(available)
        return SurfaceConsistency(level=level, details=details, conflicts=conflicts)

    def _get_signal(self, component: object | None) -> EvidenceSignal | None:
        if component is None:
            return None
        evidence = getattr(component, "evidence", None)
        if evidence is None:
            return None
        signal: EvidenceSignal | None = getattr(evidence, "signal", None)
        return signal

    def _bias_from_signal(self, signal: EvidenceSignal) -> MarketBias:
        if signal in (EvidenceSignal.VERY_BULLISH, EvidenceSignal.BULLISH):
            return MarketBias.BULLISH
        if signal in (EvidenceSignal.VERY_BEARISH, EvidenceSignal.BEARISH):
            return MarketBias.BEARISH
        return MarketBias.NEUTRAL

    def _assess(
        self,
        available: list[tuple[str, EvidenceSignal]],
    ) -> tuple[SurfaceConsistencyLevel, str, tuple[str, ...]]:
        biases = [self._bias_from_signal(s) for _, s in available]
        bullish_count = biases.count(MarketBias.BULLISH)
        bearish_count = biases.count(MarketBias.BEARISH)
        neutral_count = biases.count(MarketBias.NEUTRAL)
        total = len(biases)

        conflicts: list[str] = []

        if neutral_count == total:
            return (
                SurfaceConsistencyLevel.CONSISTENT,
                "All components agree: neutral signal across the surface.",
                (),
            )

        if bullish_count > 0 and bearish_count > 0:
            conflicts.append(
                f"Bullish signal from {bullish_count} component(s) conflicts with "
                f"bearish signal from {bearish_count} component(s)."
            )
            return (
                SurfaceConsistencyLevel.INCONSISTENT,
                f"Conflicting signals: {bullish_count} bullish vs {bearish_count} bearish "
                f"({neutral_count} neutral).",
                tuple(conflicts),
            )

        non_neutral = [
            n for n, s in available if self._bias_from_signal(s) != MarketBias.NEUTRAL
        ]
        source_list = ", ".join(non_neutral)
        direction = "bullish" if bullish_count > bearish_count else "bearish"

        return (
            SurfaceConsistencyLevel.CONSISTENT,
            f"All directional components agree: {direction} bias from {source_list}.",
            (),
        )
