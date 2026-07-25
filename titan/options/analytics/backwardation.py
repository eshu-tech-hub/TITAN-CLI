from titan.options.analytics.models import (
    BackwardationResult,
    CalendarResult,
    TermStructureStrength,
)

BACKWARDATION_THRESHOLD = 0.01
BACKWARDATION_MEDIUM = 0.03
BACKWARDATION_HIGH = 0.06
BACKWARDATION_EXTREME = 0.10
STRESS_THRESHOLD = 0.06


class BackwardationAnalyzer:
    """Analyze whether the volatility term structure is in backwardation.

    Backwardation occurs when near-term implied volatility is higher than
    far-term implied volatility (downward-sloping or inverted curve).
    """

    name = "BackwardationAnalyzer"

    def analyze(self, calendar: CalendarResult) -> BackwardationResult:
        if not isinstance(calendar, CalendarResult):
            raise TypeError("calendar must be a CalendarResult.")

        if calendar.calendar_spread is None:
            return BackwardationResult(
                interpretation="Backwardation cannot be determined: calendar spread unavailable.",
            )

        spread = calendar.calendar_spread
        abs_spread = abs(spread)

        if spread >= 0:
            return BackwardationResult(
                is_backwardation=False,
                interpretation=(
                    "Term structure is not in backwardation. "
                    "Near-term implied volatility is not above far-term."
                ),
            )

        strength = self._classify_strength(abs_spread)
        stress_indicator = abs_spread >= STRESS_THRESHOLD
        confidence = self._confidence(abs_spread, calendar.confidence)
        interpretation = self._interpretation(strength, spread, stress_indicator)

        return BackwardationResult(
            is_backwardation=True,
            strength=strength,
            interpretation=interpretation,
            confidence=confidence,
            stress_indicator=stress_indicator,
        )

    def _classify_strength(self, abs_spread: float) -> TermStructureStrength:
        if abs_spread >= BACKWARDATION_EXTREME:
            return TermStructureStrength.EXTREME
        if abs_spread >= BACKWARDATION_HIGH:
            return TermStructureStrength.HIGH
        if abs_spread >= BACKWARDATION_MEDIUM:
            return TermStructureStrength.MEDIUM
        if abs_spread >= BACKWARDATION_THRESHOLD:
            return TermStructureStrength.LOW
        return TermStructureStrength.UNKNOWN

    def _confidence(self, abs_spread: float, calendar_confidence: float) -> float:
        magnitude_bonus = min(abs_spread / BACKWARDATION_HIGH, 1.0) * 0.3
        return min(calendar_confidence * 0.7 + magnitude_bonus, 1.0)

    def _interpretation(
        self,
        strength: TermStructureStrength,
        spread: float,
        stress_indicator: bool,
    ) -> str:
        interpretations = {
            TermStructureStrength.LOW: (
                f"Mild backwardation detected (spread {spread:+.2%}). "
                "Near-term implied volatility is slightly above "
                "far-term, which may indicate near-term uncertainty."
            ),
            TermStructureStrength.MEDIUM: (
                f"Moderate backwardation detected (spread {spread:+.2%}). "
                "The inverted volatility curve suggests elevated "
                "near-term risk perception among market participants."
            ),
            TermStructureStrength.HIGH: (
                f"Strong backwardation detected (spread {spread:+.2%}). "
                "The volatility curve is sharply inverted, indicating "
                "significant near-term stress or event-driven uncertainty."
            ),
            TermStructureStrength.EXTREME: (
                f"Extreme backwardation detected (spread {spread:+.2%}). "
                "The volatility curve is severely inverted, suggesting "
                "acute near-term market stress or a potential crisis "
                "scenario unfolding."
            ),
            TermStructureStrength.UNKNOWN: (
                "Backwardation strength cannot be determined."
            ),
        }

        base = interpretations.get(
            strength,
            "Backwardation analysis is unavailable.",
        )

        if stress_indicator:
            base += (
                " STRESS INDICATOR: Backwardation magnitude exceeds "
                "normal thresholds. Monitor for potential market stress "
                "or dislocations."
            )

        return base
