from titan.options.analytics.models import (
    CalendarResult,
    ContangoResult,
    TermStructureStrength,
)

CONTANGO_THRESHOLD = 0.01
CONTANGO_MEDIUM = 0.03
CONTANGO_HIGH = 0.06
CONTANGO_EXTREME = 0.10


class ContangoAnalyzer:
    """Analyze whether the volatility term structure is in contango.

    Contango occurs when far-term implied volatility is higher than
    near-term implied volatility (upward-sloping curve).
    """

    name = "ContangoAnalyzer"

    def analyze(self, calendar: CalendarResult) -> ContangoResult:
        if not isinstance(calendar, CalendarResult):
            raise TypeError("calendar must be a CalendarResult.")

        if calendar.calendar_spread is None:
            return ContangoResult(
                interpretation="Contango cannot be determined: calendar spread unavailable.",
            )

        spread = calendar.calendar_spread

        if spread <= 0:
            return ContangoResult(
                is_contango=False,
                interpretation=(
                    "Term structure is not in contango. "
                    "Far-term implied volatility is not above near-term."
                ),
            )

        strength = self._classify_strength(spread)
        confidence = self._confidence(spread, calendar.confidence)
        interpretation = self._interpretation(strength, spread)

        return ContangoResult(
            is_contango=True,
            strength=strength,
            interpretation=interpretation,
            confidence=confidence,
        )

    def _classify_strength(self, spread: float) -> TermStructureStrength:
        if spread >= CONTANGO_EXTREME:
            return TermStructureStrength.EXTREME
        if spread >= CONTANGO_HIGH:
            return TermStructureStrength.HIGH
        if spread >= CONTANGO_MEDIUM:
            return TermStructureStrength.MEDIUM
        if spread >= CONTANGO_THRESHOLD:
            return TermStructureStrength.LOW
        return TermStructureStrength.UNKNOWN

    def _confidence(self, spread: float, calendar_confidence: float) -> float:
        magnitude_bonus = min(abs(spread) / CONTANGO_HIGH, 1.0) * 0.3
        return min(calendar_confidence * 0.7 + magnitude_bonus, 1.0)

    def _interpretation(self, strength: TermStructureStrength, spread: float) -> str:
        interpretations = {
            TermStructureStrength.LOW: (
                f"Mild contango detected (spread {spread:+.2%}). "
                "The volatility curve is slightly upward-sloping, "
                "which is consistent with normal market conditions."
            ),
            TermStructureStrength.MEDIUM: (
                f"Moderate contango detected (spread {spread:+.2%}). "
                "The volatility curve is upward-sloping, suggesting "
                "healthy demand for longer-dated protection."
            ),
            TermStructureStrength.HIGH: (
                f"Strong contango detected (spread {spread:+.2%}). "
                "Far-term volatility is significantly higher than "
                "near-term, which may indicate elevated uncertainty "
                "over longer horizons."
            ),
            TermStructureStrength.EXTREME: (
                f"Extreme contango detected (spread {spread:+.2%}). "
                "Far-term volatility is substantially above near-term, "
                "potentially signaling structural uncertainty or "
                "dislocation in the volatility market."
            ),
            TermStructureStrength.UNKNOWN: ("Contango strength cannot be determined."),
        }

        return interpretations.get(
            strength,
            "Contango analysis is unavailable.",
        )
