from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)

from titan.options.analytics.models import (
    OptionChainSnapshot,
    SmileAnalysis,
    SmileExplanation,
    SmileQuality,
    SmileRegime,
    SmileShape,
    SmileSymmetry,
)

CURVATURE_FLAT_THRESHOLD = 0.05
CURVATURE_MILD_THRESHOLD = 0.10
CURVATURE_NORMAL_THRESHOLD = 0.20
CURVATURE_STRONG_THRESHOLD = 0.35
SYMMETRY_RATIO_LOWER = 0.9
SYMMETRY_RATIO_UPPER = 1.1
MIN_STRIKES_RELIABLE = 5
MIN_STRIKES_PARTIAL = 3
COMPLETENESS_RELIABLE = 0.7
COMPLETENESS_PARTIAL = 0.4
MAX_VALID_IV = 10.0
NEUTRAL_SCORE = 50.0


class SmileAnalyzer:
    """Analyze implied volatility smile from option chain data.

    Consumes supplied implied volatility data only. Never estimates IV.
    Never fits Black-Scholes, SABR, SVI, or any interpolation model.

    Analytics:
        1. ATM Implied Volatility
        2. Smile Curvature (Flat / Mild / Normal / Strong / Extreme)
        3. Smile Symmetry (Symmetric / Left-biased / Right-biased)
        4. Strike Coverage (count, completeness, missing data)
        5. Smile Quality (Reliable / Partial / Unreliable)
        6. Evidence Generation (Fusion Engine compatible)
        7. Human Explanation (institutional-grade)
    """

    name = "SmileAnalyzer"

    def analyze(self, chain: OptionChainSnapshot) -> SmileAnalysis:
        if not isinstance(chain, OptionChainSnapshot):
            raise TypeError("chain must be an OptionChainSnapshot.")

        if not chain.strikes:
            return self._empty_analysis("Chain has no strikes.")

        atm_strike, atm_call_iv, atm_put_iv = self._find_atm(chain)
        atm_iv = self._resolve_atm_iv(atm_call_iv, atm_put_iv)

        curvature, left_wing_iv, right_wing_iv, shape = self._measure_curvature(
            chain, atm_strike, atm_iv
        )

        symmetry = self._measure_symmetry(left_wing_iv, right_wing_iv)
        regime = self._determine_regime(shape, symmetry, curvature)
        strike_count, iv_completeness = self._evaluate_coverage(chain)
        quality = self._evaluate_quality(
            chain, atm_strike, strike_count, iv_completeness
        )
        confidence = self._calculate_confidence(quality, iv_completeness, shape)
        warnings = self._generate_warnings(
            chain, atm_strike, atm_iv, strike_count, quality
        )

        analysis = SmileAnalysis(
            atm_strike=atm_strike,
            atm_iv=atm_iv,
            smile_shape=shape,
            smile_symmetry=symmetry,
            smile_regime=regime,
            smile_quality=quality,
            curvature=curvature,
            left_wing_iv=left_wing_iv,
            right_wing_iv=right_wing_iv,
            strike_count=strike_count,
            iv_completeness=iv_completeness,
            confidence=confidence,
            warnings=warnings,
            metadata=self._metadata(chain, shape, symmetry, regime),
        )

        evidence = self._to_evidence(analysis)
        explanation = self._explanation(analysis)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    def _find_atm(
        self,
        chain: OptionChainSnapshot,
    ) -> tuple[float | None, float | None, float | None]:
        if not chain.strikes:
            return None, None, None

        underlying = chain.underlying_price
        if underlying is not None and underlying > 0:
            atm = min(chain.strikes, key=lambda s: abs(s.strike_price - underlying))
        else:
            sorted_strikes = sorted(chain.strikes, key=lambda s: s.strike_price)
            atm = sorted_strikes[len(sorted_strikes) // 2]

        atm_snapshot = next(
            (s for s in chain.strikes if s.strike_price == atm.strike_price), None
        )
        if atm_snapshot is None:
            return atm.strike_price, None, None

        call_iv = (
            atm_snapshot.call_implied_volatility
            if atm_snapshot.call_implied_volatility is not None
            and atm_snapshot.call_implied_volatility > 0
            and atm_snapshot.call_implied_volatility < MAX_VALID_IV
            else None
        )
        put_iv = (
            atm_snapshot.put_implied_volatility
            if atm_snapshot.put_implied_volatility is not None
            and atm_snapshot.put_implied_volatility > 0
            and atm_snapshot.put_implied_volatility < MAX_VALID_IV
            else None
        )

        return atm.strike_price, call_iv, put_iv

    def _resolve_atm_iv(
        self,
        call_iv: float | None,
        put_iv: float | None,
    ) -> float | None:
        if call_iv is not None and put_iv is not None:
            return (call_iv + put_iv) / 2.0
        if call_iv is not None:
            return call_iv
        if put_iv is not None:
            return put_iv
        return None

    def _measure_curvature(
        self,
        chain: OptionChainSnapshot,
        atm_strike: float | None,
        atm_iv: float | None,
    ) -> tuple[float | None, float | None, float | None, SmileShape]:
        if atm_strike is None or atm_iv is None or atm_iv <= 0:
            return None, None, None, SmileShape.UNKNOWN

        left_ivs: list[float] = []
        right_ivs: list[float] = []

        for s in chain.strikes:
            if s.strike_price < atm_strike:
                iv = self._safe_iv(s.put_implied_volatility)
                if iv is not None:
                    left_ivs.append(iv)
            elif s.strike_price > atm_strike:
                iv = self._safe_iv(s.call_implied_volatility)
                if iv is not None:
                    right_ivs.append(iv)

        left_avg = sum(left_ivs) / len(left_ivs) if left_ivs else None
        right_avg = sum(right_ivs) / len(right_ivs) if right_ivs else None

        wing_ivs = [v for v in (left_avg, right_avg) if v is not None]
        if not wing_ivs:
            return None, left_avg, right_avg, SmileShape.UNKNOWN

        wing_avg = sum(wing_ivs) / len(wing_ivs)
        curvature = (wing_avg - atm_iv) / atm_iv
        shape = self._classify_shape(curvature)

        return curvature, left_avg, right_avg, shape

    def _safe_iv(self, iv: float | None) -> float | None:
        if iv is None:
            return None
        if iv <= 0 or iv >= MAX_VALID_IV:
            return None
        return iv

    def _classify_shape(self, curvature: float) -> SmileShape:
        abs_curv = abs(curvature)
        if abs_curv < CURVATURE_FLAT_THRESHOLD:
            return SmileShape.FLAT
        if abs_curv < CURVATURE_MILD_THRESHOLD:
            return SmileShape.MILD
        if abs_curv < CURVATURE_NORMAL_THRESHOLD:
            return SmileShape.NORMAL
        if abs_curv < CURVATURE_STRONG_THRESHOLD:
            return SmileShape.STRONG
        return SmileShape.EXTREME

    def _measure_symmetry(
        self,
        left_wing_iv: float | None,
        right_wing_iv: float | None,
    ) -> SmileSymmetry:
        if left_wing_iv is None and right_wing_iv is None:
            return SmileSymmetry.UNKNOWN
        if left_wing_iv is None:
            return SmileSymmetry.RIGHT_BIASED
        if right_wing_iv is None:
            return SmileSymmetry.LEFT_BIASED
        if right_wing_iv <= 0:
            return SmileSymmetry.UNKNOWN

        ratio = left_wing_iv / right_wing_iv
        if SYMMETRY_RATIO_LOWER <= ratio <= SYMMETRY_RATIO_UPPER:
            return SmileSymmetry.SYMMETRIC
        if ratio > SYMMETRY_RATIO_UPPER:
            return SmileSymmetry.LEFT_BIASED
        return SmileSymmetry.RIGHT_BIASED

    def _determine_regime(
        self,
        shape: SmileShape,
        symmetry: SmileSymmetry,
        curvature: float | None,
    ) -> SmileRegime:
        if shape is SmileShape.UNKNOWN:
            return SmileRegime.UNKNOWN

        if curvature is not None and curvature < 0:
            return SmileRegime.INVERTED

        if symmetry is SmileSymmetry.LEFT_BIASED:
            return SmileRegime.PUT_SKEW
        if symmetry is SmileSymmetry.RIGHT_BIASED:
            return SmileRegime.CALL_SKEW

        if shape is SmileShape.FLAT:
            return SmileRegime.FLAT

        return SmileRegime.NORMAL_CONVEXITY

    def _evaluate_coverage(
        self,
        chain: OptionChainSnapshot,
    ) -> tuple[int, float]:
        total = len(chain.strikes)
        with_iv = sum(
            1
            for s in chain.strikes
            if self._safe_iv(s.call_implied_volatility) is not None
            or self._safe_iv(s.put_implied_volatility) is not None
        )
        completeness = with_iv / total if total > 0 else 0.0
        return total, completeness

    def _evaluate_quality(
        self,
        chain: OptionChainSnapshot,
        atm_strike: float | None,
        strike_count: int,
        iv_completeness: float,
    ) -> SmileQuality:
        if atm_strike is None or strike_count < MIN_STRIKES_PARTIAL:
            return SmileQuality.UNRELIABLE
        if (
            strike_count >= MIN_STRIKES_RELIABLE
            and iv_completeness >= COMPLETENESS_RELIABLE
        ):
            return SmileQuality.RELIABLE
        if iv_completeness >= COMPLETENESS_PARTIAL:
            return SmileQuality.PARTIAL
        return SmileQuality.UNRELIABLE

    def _calculate_confidence(
        self,
        quality: SmileQuality,
        iv_completeness: float,
        shape: SmileShape,
    ) -> float:
        if quality is SmileQuality.UNRELIABLE or quality is SmileQuality.UNKNOWN:
            return 0.0

        base = iv_completeness

        if quality is SmileQuality.RELIABLE:
            multiplier = 1.0
        elif quality is SmileQuality.PARTIAL:
            multiplier = 0.6
        else:
            multiplier = 0.0

        if shape is SmileShape.UNKNOWN:
            shape_bonus = 0.0
        elif shape is SmileShape.FLAT:
            shape_bonus = 0.0
        else:
            shape_bonus = 0.1

        return min(base * multiplier + shape_bonus, 1.0)

    def _generate_warnings(
        self,
        chain: OptionChainSnapshot,
        atm_strike: float | None,
        atm_iv: float | None,
        strike_count: int,
        quality: SmileQuality,
    ) -> tuple[str, ...]:
        warnings: list[str] = []

        if strike_count < MIN_STRIKES_RELIABLE:
            warnings.append(
                f"Insufficient strikes for reliable smile analysis "
                f"({strike_count} available, {MIN_STRIKES_RELIABLE}+ recommended)."
            )
        if atm_strike is None:
            warnings.append("Could not determine ATM strike.")
        elif atm_iv is None:
            warnings.append("ATM implied volatility is unavailable.")
        if quality is SmileQuality.PARTIAL:
            warnings.append(
                "Smile data is partially complete. Results may be less reliable."
            )
        elif quality is SmileQuality.UNRELIABLE:
            warnings.append("Smile data is insufficient for reliable analysis.")

        return tuple(warnings)

    def _metadata(
        self,
        chain: OptionChainSnapshot,
        shape: SmileShape,
        symmetry: SmileSymmetry,
        regime: SmileRegime,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "underlying": chain.underlying,
            "expiry": chain.expiry.isoformat() if chain.expiry else None,
            "smile_shape": shape.value,
            "smile_symmetry": symmetry.value,
            "smile_regime": regime.value,
        }

    def _evidence_signal(self, analysis: SmileAnalysis) -> EvidenceSignal:
        symmetry = analysis.smile_symmetry

        if symmetry is SmileSymmetry.LEFT_BIASED:
            return EvidenceSignal.BEARISH
        if symmetry is SmileSymmetry.RIGHT_BIASED:
            return EvidenceSignal.BULLISH
        return EvidenceSignal.NEUTRAL

    def _evidence_score(self, analysis: SmileAnalysis) -> float:
        symmetry = analysis.smile_symmetry
        shape = analysis.smile_shape

        if (
            symmetry is SmileSymmetry.LEFT_BIASED
            or symmetry is SmileSymmetry.RIGHT_BIASED
        ):
            if shape in (SmileShape.STRONG, SmileShape.EXTREME):
                return NEUTRAL_SCORE + (analysis.confidence * 40.0)
            return NEUTRAL_SCORE + (analysis.confidence * 25.0)

        return NEUTRAL_SCORE

    def _evidence_reasons(self, analysis: SmileAnalysis) -> tuple[str, ...]:
        reasons: list[str] = []

        if analysis.smile_shape is not SmileShape.UNKNOWN:
            reasons.append(f"Smile curvature is {analysis.smile_shape.value}.")

        if analysis.smile_symmetry is not SmileSymmetry.UNKNOWN:
            reasons.append(
                f"Smile is {analysis.smile_symmetry.value.replace('_', ' ')}."
            )

        if analysis.smile_regime is not SmileRegime.UNKNOWN:
            reasons.append(
                f"Smile regime: {analysis.smile_regime.value.replace('_', ' ')}."
            )

        if analysis.atm_iv is not None:
            reasons.append(f"ATM IV is {analysis.atm_iv:.2%}.")

        if analysis.curvature is not None:
            reasons.append(f"Curvature: {analysis.curvature:.2f}.")

        if analysis.smile_quality is SmileQuality.RELIABLE:
            reasons.append("Smile data quality is reliable.")

        return tuple(reasons)

    def _to_evidence(self, analysis: SmileAnalysis) -> Evidence:
        return Evidence(
            source="Volatility Smile",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=self._evidence_signal(analysis),
            score=Score(self._evidence_score(analysis)),
            confidence=Confidence(analysis.confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "smile_shape": analysis.smile_shape.value,
                "smile_symmetry": analysis.smile_symmetry.value,
                "smile_regime": analysis.smile_regime.value,
                "atm_iv": analysis.atm_iv,
                "curvature": analysis.curvature,
            },
        )

    def _explanation(self, analysis: SmileAnalysis) -> SmileExplanation:
        return SmileExplanation(
            overview=self._overview_section(analysis),
            curvature_assessment=self._curvature_section(analysis),
            symmetry_assessment=self._symmetry_section(analysis),
            quality_assessment=self._quality_section(analysis),
            institutional_interpretation=self._institutional_section(analysis),
            warnings=analysis.warnings,
        )

    def _overview_section(self, analysis: SmileAnalysis) -> str:
        shape_desc = {
            SmileShape.FLAT: "The volatility smile is flat, with minimal curvature across strikes.",
            SmileShape.MILD: "The volatility smile shows mild convexity.",
            SmileShape.NORMAL: "The volatility smile exhibits moderate convexity.",
            SmileShape.STRONG: "The volatility smile is strongly convex.",
            SmileShape.EXTREME: "The volatility smile shows extreme convexity.",
            SmileShape.UNKNOWN: "Volatility smile shape cannot be determined.",
        }

        wing_info = ""
        if analysis.left_wing_iv is not None and analysis.right_wing_iv is not None:
            wing_info = (
                f" OTM put IV averages {analysis.left_wing_iv:.2%} "
                f"and OTM call IV averages {analysis.right_wing_iv:.2%}."
            )
        elif analysis.left_wing_iv is not None:
            wing_info = f" OTM put IV averages {analysis.left_wing_iv:.2%}."
        elif analysis.right_wing_iv is not None:
            wing_info = f" OTM call IV averages {analysis.right_wing_iv:.2%}."

        base = shape_desc.get(
            analysis.smile_shape,
            "Volatility smile data is insufficient for analysis.",
        )
        return base + wing_info

    def _curvature_section(self, analysis: SmileAnalysis) -> str:
        if analysis.curvature is None:
            return "Curvature could not be measured due to insufficient data."

        descriptions = {
            SmileShape.FLAT: (
                "Wing IVs are within 5% of ATM IV, indicating minimal "
                "volatility premium for out-of-the-money strikes."
            ),
            SmileShape.MILD: (
                "Wing IVs are 5-10% above ATM IV, suggesting slightly "
                "elevated demand for out-of-the-money options."
            ),
            SmileShape.NORMAL: (
                "Wing IVs are 10-20% above ATM IV, reflecting typical "
                "market pricing for tail risk."
            ),
            SmileShape.STRONG: (
                "Wing IVs are 20-35% above ATM IV, indicating heightened "
                "demand for out-of-the-money protection or speculation."
            ),
            SmileShape.EXTREME: (
                "Wing IVs exceed ATM IV by more than 35%, reflecting "
                "significant tail-risk premium in option prices."
            ),
            SmileShape.UNKNOWN: "Curvature classification is unavailable.",
        }

        base = descriptions.get(
            analysis.smile_shape,
            "Curvature assessment is unavailable.",
        )
        return f"Curvature: {analysis.curvature:.2f}. " + base

    def _symmetry_section(self, analysis: SmileAnalysis) -> str:
        descriptions = {
            SmileSymmetry.SYMMETRIC: (
                "The smile is symmetric with balanced implied volatility "
                "on both the put and call sides."
            ),
            SmileSymmetry.LEFT_BIASED: (
                "The smile is left-biased with elevated OTM put implied "
                "volatility, suggesting stronger demand for downside "
                "protection."
            ),
            SmileSymmetry.RIGHT_BIASED: (
                "The smile is right-biased with elevated OTM call implied "
                "volatility, suggesting stronger demand for upside "
                "speculation."
            ),
            SmileSymmetry.UNKNOWN: "Smile symmetry could not be determined.",
        }

        return descriptions.get(
            analysis.smile_symmetry,
            "Symmetry assessment is unavailable.",
        )

    def _quality_section(self, analysis: SmileAnalysis) -> str:
        descriptions = {
            SmileQuality.RELIABLE: (
                f"Analysis is based on {analysis.strike_count} strikes "
                f"with {analysis.iv_completeness:.0%} IV completeness."
            ),
            SmileQuality.PARTIAL: (
                f"Analysis is based on {analysis.strike_count} strikes "
                f"with {analysis.iv_completeness:.0%} IV completeness. "
                f"Results may be less reliable."
            ),
            SmileQuality.UNRELIABLE: (
                f"Insufficient data: {analysis.strike_count} strikes, "
                f"{analysis.iv_completeness:.0%} IV completeness."
            ),
            SmileQuality.UNKNOWN: "Data quality could not be assessed.",
        }

        return descriptions.get(
            analysis.smile_quality,
            "Quality assessment is unavailable.",
        )

    def _institutional_section(self, analysis: SmileAnalysis) -> str:
        parts: list[str] = ["Institutional Interpretation:"]

        if analysis.smile_regime is SmileRegime.PUT_SKEW:
            parts.append(
                "Elevated OTM put implied volatility indicates market "
                "participants are pricing in heightened downside risk. "
                "Consider tail-risk hedging strategies."
            )
        elif analysis.smile_regime is SmileRegime.CALL_SKEW:
            parts.append(
                "Elevated OTM call implied volatility indicates "
                "speculative demand for upside exposure. Monitor for "
                "potential short-squeeze or momentum-driven moves."
            )
        elif analysis.smile_regime is SmileRegime.NORMAL_CONVEXITY:
            parts.append(
                "The volatility smile exhibits typical convexity with "
                "balanced tail-risk pricing across strikes."
            )
        elif analysis.smile_regime is SmileRegime.FLAT:
            parts.append(
                "The flat smile suggests market participants are not "
                "pricing significant tail risk at current levels."
            )
        elif analysis.smile_regime is SmileRegime.INVERTED:
            parts.append(
                "The inverted smile pattern is unusual and may indicate "
                "market stress or dislocated option pricing."
            )

        if analysis.atm_iv is not None:
            parts.append(f"ATM implied volatility is {analysis.atm_iv:.2%}.")

        return " ".join(parts)

    def _empty_analysis(self, reason: str) -> SmileAnalysis:
        """Return a neutral placeholder when the chain has no usable data."""
        analysis = SmileAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = SmileExplanation(
            overview="Volatility smile data is insufficient for analysis.",
            curvature_assessment="Curvature could not be measured due to insufficient data.",
            symmetry_assessment="Smile symmetry could not be determined.",
            quality_assessment="Data quality could not be assessed.",
            institutional_interpretation="Institutional Interpretation: Smile data is unavailable.",
            warnings=(reason,),
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
