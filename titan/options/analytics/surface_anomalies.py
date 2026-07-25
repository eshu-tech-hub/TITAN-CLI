from titan.options.analytics.models import (
    MarketBias,
    SkewAnalysis,
    SkewStrength,
    SmileAnalysis,
    SmileShape,
    SurfaceAnomaly,
    SurfaceAnomalyResult,
    SurfaceAnomalyType,
    TermStructureAnalysis,
    TermStructureShape,
    TermStructureStrength,
    VolatilitySurfaceInput,
)

LOW_CONFIDENCE_THRESHOLD = 0.3


class SurfaceAnomalyAnalyzer:
    """Detect anomalies in the volatility surface.

    Checks for extreme smile curvature, extreme skew, broken term
    structure, conflicting volatility signals, missing intelligence
    components, and low-confidence components.
    """

    name = "SurfaceAnomalyAnalyzer"

    def analyze(self, surface: VolatilitySurfaceInput) -> SurfaceAnomalyResult:
        if not isinstance(surface, VolatilitySurfaceInput):
            raise TypeError("surface must be a VolatilitySurfaceInput.")

        anomalies: list[SurfaceAnomaly] = []

        self._check_extreme_smile(surface.smile, anomalies)
        self._check_extreme_skew(surface.skew, anomalies)
        self._check_broken_term_structure(surface.term_structure, anomalies)
        self._check_conflicting_signals(surface, anomalies)
        self._check_missing_intelligence(surface, anomalies)
        self._check_low_confidence(surface, anomalies)

        return SurfaceAnomalyResult(
            anomalies=tuple(anomalies),
            anomaly_count=len(anomalies),
        )

    def _check_extreme_smile(
        self,
        smile: SmileAnalysis | None,
        anomalies: list[SurfaceAnomaly],
    ) -> None:
        if smile is None:
            return
        if smile.smile_shape is SmileShape.EXTREME:
            anomalies.append(
                SurfaceAnomaly(
                    type=SurfaceAnomalyType.EXTREME_SMILE,
                    source="Smile",
                    description=(
                        f"Extreme smile curvature detected "
                        f"(shape: {smile.smile_shape.value}). "
                        f"Wing IV deviation from ATM is abnormally large."
                    ),
                )
            )

    def _check_extreme_skew(
        self,
        skew: SkewAnalysis | None,
        anomalies: list[SurfaceAnomaly],
    ) -> None:
        if skew is None:
            return
        if skew.strength is SkewStrength.EXTREME:
            anomalies.append(
                SurfaceAnomaly(
                    type=SurfaceAnomalyType.EXTREME_SKEW,
                    source="Skew",
                    description=(
                        f"Extreme skew detected "
                        f"(strength: {skew.strength.value}, direction: {skew.direction.value}). "
                        f"Risk reversal is at extreme levels."
                    ),
                )
            )

    def _check_broken_term_structure(
        self,
        term: TermStructureAnalysis | None,
        anomalies: list[SurfaceAnomaly],
    ) -> None:
        if term is None:
            return
        if term.shape is TermStructureShape.INVERTED and term.strength in (
            TermStructureStrength.HIGH,
            TermStructureStrength.EXTREME,
        ):
            anomalies.append(
                SurfaceAnomaly(
                    type=SurfaceAnomalyType.BROKEN_TERM_STRUCTURE,
                    source="Term Structure",
                    description=(
                        f"Broken term structure: curve is {term.shape.value} "
                        f"with {term.strength.value} strength. "
                        f"Near-term implied volatility substantially exceeds far-term, "
                        f"indicating acute market stress."
                    ),
                )
            )

    def _check_conflicting_signals(
        self,
        surface: VolatilitySurfaceInput,
        anomalies: list[SurfaceAnomaly],
    ) -> None:
        biases: list[tuple[str, MarketBias]] = []

        vol_bias = self._get_bias(surface.volatility)
        if vol_bias is not None:
            biases.append(("Volatility", vol_bias))

        smile_bias = self._get_smile_bias(surface.smile)
        if smile_bias is not None:
            biases.append(("Smile", smile_bias))

        skew_bias = self._get_bias(surface.skew)
        if skew_bias is not None:
            biases.append(("Skew", skew_bias))

        ts_bias = self._get_bias(surface.term_structure)
        if ts_bias is not None:
            biases.append(("Term Structure", ts_bias))

        if len(biases) < 2:
            return

        directions = [
            (n, b) for n, b in biases if b in (MarketBias.BULLISH, MarketBias.BEARISH)
        ]
        if len(directions) < 2:
            return

        bullish_sources = [n for n, b in directions if b is MarketBias.BULLISH]
        bearish_sources = [n for n, b in directions if b is MarketBias.BEARISH]

        if bullish_sources and bearish_sources:
            anomalies.append(
                SurfaceAnomaly(
                    type=SurfaceAnomalyType.CONFLICTING_SIGNALS,
                    source="Cross-Module",
                    description=(
                        f"Conflicting signals across components: "
                        f"bullish from {', '.join(bullish_sources)}, "
                        f"bearish from {', '.join(bearish_sources)}."
                    ),
                )
            )

    def _check_missing_intelligence(
        self,
        surface: VolatilitySurfaceInput,
        anomalies: list[SurfaceAnomaly],
    ) -> None:
        checks = [
            ("Volatility", surface.volatility),
            ("Smile", surface.smile),
            ("Skew", surface.skew),
            ("Term Structure", surface.term_structure),
        ]
        for name, comp in checks:
            if comp is None:
                anomalies.append(
                    SurfaceAnomaly(
                        type=SurfaceAnomalyType.MISSING_INTELLIGENCE,
                        source=name,
                        description=(
                            f"{name} intelligence is missing. "
                            f"Surface analysis is incomplete without this component."
                        ),
                    )
                )

    def _check_low_confidence(
        self,
        surface: VolatilitySurfaceInput,
        anomalies: list[SurfaceAnomaly],
    ) -> None:
        checks = [
            ("Volatility", surface.volatility),
            ("Smile", surface.smile),
            ("Skew", surface.skew),
            ("Term Structure", surface.term_structure),
        ]
        for name, comp in checks:
            if comp is not None and comp.confidence < LOW_CONFIDENCE_THRESHOLD:
                anomalies.append(
                    SurfaceAnomaly(
                        type=SurfaceAnomalyType.LOW_CONFIDENCE,
                        source=name,
                        description=(
                            f"{name} confidence is {comp.confidence:.0%}, "
                            f"below {LOW_CONFIDENCE_THRESHOLD:.0%} threshold. "
                            f"Analysis may be unreliable."
                        ),
                    )
                )

    def _get_bias(self, component: object | None) -> MarketBias | None:
        if component is None:
            return None
        bias: MarketBias | None = getattr(component, "overall_bias", None)
        if bias is MarketBias.UNKNOWN:
            return None
        return bias

    def _get_smile_bias(self, smile: SmileAnalysis | None) -> MarketBias | None:
        if smile is None:
            return None
        if smile.smile_regime and hasattr(smile.smile_regime, "value"):
            regime = smile.smile_regime.value
            if "put" in regime:
                return MarketBias.BEARISH
            if "call" in regime:
                return MarketBias.BULLISH
        return None
