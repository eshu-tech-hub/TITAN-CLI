from dataclasses import dataclass, field
from datetime import datetime, timezone

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)

from titan.decision.models import TradeDecision
from titan.portfolio.allocation import CapitalAllocationAnalyzer
from titan.portfolio.correlation import CorrelationAnalyzer
from titan.portfolio.exceptions import PortfolioEngineError, PortfolioInputError
from titan.portfolio.exposure import ExposureAnalyzer
from titan.portfolio.hedging import HedgingAnalyzer
from titan.portfolio.models import (
    CorrelationAnalysis,
    CorrelationLevel,
    ExistingPortfolio,
    HedgingAction,
    HedgingRecommendation,
    PortfolioAnalysis,
    PortfolioDecisionContext,
    PortfolioExplanation,
    PortfolioExposure,
    PortfolioScoreBand,
    PortfolioSnapshot,
)
from titan.portfolio.positions import PositionAnalyzer
from titan.risk.models import RiskAnalysis

SCORE_BAND_THRESHOLDS: tuple[tuple[float, PortfolioScoreBand], ...] = (
    (20.0, PortfolioScoreBand.EXCELLENT),
    (40.0, PortfolioScoreBand.GOOD),
    (60.0, PortfolioScoreBand.MODERATE),
    (80.0, PortfolioScoreBand.POOR),
)


@dataclass(slots=True)
class PortfolioEngine:
    """Central Portfolio Intelligence Engine for TITAN OS.

    Evaluates every new trade in the context of the existing portfolio.
    It prevents capital concentration, excessive exposure, correlated
    positions, and over-leveraging.

    This engine does NOT:
        - Perform market analysis or qualify trades.
        - Execute orders or call broker APIs.
        - Fetch broker positions (consumes ExistingPortfolio).

    Its responsibility is to answer:
        "Given everything we already own, should this new trade be
         accepted, reduced, hedged, or rejected?"

    Internally orchestrates:
        - PositionAnalyzer
        - ExposureAnalyzer
        - CorrelationAnalyzer
        - CapitalAllocationAnalyzer
        - HedgingAnalyzer
    """

    _positions: PositionAnalyzer = field(default_factory=PositionAnalyzer)
    _exposure: ExposureAnalyzer = field(default_factory=ExposureAnalyzer)
    _correlation: CorrelationAnalyzer = field(default_factory=CorrelationAnalyzer)
    _allocation: CapitalAllocationAnalyzer = field(
        default_factory=CapitalAllocationAnalyzer
    )
    _hedging: HedgingAnalyzer = field(default_factory=HedgingAnalyzer)

    def analyze(
        self,
        trade_decision: TradeDecision,
        risk_analysis: RiskAnalysis,
        portfolio: ExistingPortfolio,
    ) -> PortfolioAnalysis:
        """Execute complete portfolio intelligence analysis.

        Args:
            trade_decision: Decision Engine output for the proposed trade.
            risk_analysis: Risk Intelligence Engine output for the proposed trade.
            portfolio: Current portfolio state supplied externally.

        Returns:
            Complete portfolio analysis with decision context.

        Raises:
            PortfolioInputError: If any input is invalid.
            PortfolioEngineError: If any sub-engine fails.
        """
        self._validate_inputs(trade_decision, risk_analysis, portfolio)

        try:
            snapshot = self._positions.analyze(portfolio)
            exposure, sector_exposures = self._exposure.analyze(portfolio)
            correlation = self._correlation.analyze(portfolio)
            (
                remaining_capital,
                max_new_allocation,
                capital_efficiency,
                concentration_headroom,
            ) = self._allocation.analyze(portfolio, snapshot)
            hedging = self._hedging.analyze(portfolio, snapshot, exposure, correlation)

            score_val = self._calculate_portfolio_score(
                snapshot=snapshot,
                exposure=exposure,
                correlation=correlation,
            )
            band = self._determine_band(score_val)
            decision_context = self._generate_decision_context(
                portfolio=portfolio,
                snapshot=snapshot,
                score_val=score_val,
                hedging=hedging,
                remaining_capital=remaining_capital,
                max_new_allocation=max_new_allocation,
                concentration_headroom=concentration_headroom,
                trade_decision=trade_decision,
            )
            allow_trade = (
                decision_context.allow_trade and not decision_context.block_trade
            )
            evidence = self._generate_evidence(
                score_val=score_val,
                band=band,
                decision_context=decision_context,
                trade_decision=trade_decision,
            )
            explanation = self._generate_explanation(
                snapshot=snapshot,
                exposure=exposure,
                correlation=correlation,
                hedging=hedging,
                decision_context=decision_context,
                remaining_capital=remaining_capital,
                capital_efficiency=capital_efficiency,
            )
            warnings = self._collect_warnings(
                snapshot=snapshot,
                exposure=exposure,
                correlation=correlation,
                hedging=hedging,
                trade_decision=trade_decision,
            )

            return PortfolioAnalysis(
                portfolio_name=portfolio.name,
                snapshot=snapshot,
                exposure=exposure,
                sector_exposures=sector_exposures,
                correlation=correlation,
                hedging=hedging,
                portfolio_score=round(score_val, 2),
                portfolio_band=band,
                decision_context=decision_context,
                allow_trade=allow_trade,
                evidence=evidence,
                explanation=explanation,
                warnings=tuple(warnings),
                metadata={
                    "trade_symbol": trade_decision.symbol,
                    "trade_action": trade_decision.decision.value,
                    "sub_engines": [
                        self._positions.name,
                        self._exposure.name,
                        self._correlation.name,
                        self._allocation.name,
                        self._hedging.name,
                    ],
                },
                timestamp=datetime.now(timezone.utc),
            )

        except PortfolioInputError:
            raise
        except Exception as exc:
            raise PortfolioEngineError(f"Portfolio analysis failed: {exc}") from exc

    def _validate_inputs(
        self,
        trade_decision: TradeDecision,
        risk_analysis: RiskAnalysis,
        portfolio: ExistingPortfolio,
    ) -> None:
        if not isinstance(trade_decision, TradeDecision):
            raise PortfolioInputError(
                "trade_decision must be a TradeDecision instance."
            )
        if not isinstance(risk_analysis, RiskAnalysis):
            raise PortfolioInputError("risk_analysis must be a RiskAnalysis instance.")
        if not isinstance(portfolio, ExistingPortfolio):
            raise PortfolioInputError(
                "portfolio must be an ExistingPortfolio instance."
            )
        if portfolio.total_capital < 0.0:
            raise PortfolioInputError("Total capital cannot be negative.")

    def _calculate_portfolio_score(
        self,
        snapshot: "PortfolioSnapshot",
        exposure: "PortfolioExposure",
        correlation: "CorrelationAnalysis",
    ) -> float:
        """Calculate portfolio health score (0 = best, 100 = worst)."""
        utilization_risk = snapshot.utilization * 40.0
        concentration_risk = (
            exposure.sector_concentration * 20.0 + exposure.symbol_concentration * 20.0
        )
        corr_map = {
            CorrelationLevel.VERY_LOW: 0.0,
            CorrelationLevel.LOW: 5.0,
            CorrelationLevel.MODERATE: 15.0,
            CorrelationLevel.HIGH: 25.0,
            CorrelationLevel.EXTREME: 30.0,
        }
        correlation_risk = corr_map.get(correlation.overall_correlation_level, 10.0)
        total = utilization_risk + concentration_risk + correlation_risk
        return max(0.0, min(100.0, total))

    def _determine_band(self, score: float) -> PortfolioScoreBand:
        for threshold, band in SCORE_BAND_THRESHOLDS:
            if score <= threshold:
                return band
        return PortfolioScoreBand.CRITICAL

    def _generate_decision_context(
        self,
        portfolio: "ExistingPortfolio",
        snapshot: "PortfolioSnapshot",
        score_val: float,
        hedging: "HedgingRecommendation",
        remaining_capital: float,
        max_new_allocation: float,
        concentration_headroom: float,
        trade_decision: TradeDecision,
    ) -> PortfolioDecisionContext:
        block = score_val >= 80.0 or snapshot.utilization >= 0.95
        reduce = snapshot.utilization >= 0.85 or (
            hedging.action == HedgingAction.REDUCE_EXPOSURE
        )
        allow = not block and not reduce and remaining_capital > 0.0
        hedge_required = hedging.action in (
            HedgingAction.INCREASE_HEDGE,
            HedgingAction.REDUCE_EXPOSURE,
        )

        max_contracts = 0
        if allow and trade_decision.metadata:
            if isinstance(trade_decision.metadata, dict):
                max_contracts = trade_decision.metadata.get("max_contracts", 0)

        if max_contracts == 0:
            max_contracts = int(
                min(
                    max_new_allocation / 10000.0,
                    concentration_headroom / 5000.0,
                )
            )
            max_contracts = max(0, max_contracts)

        conf = (
            0.9
            if score_val <= 20.0
            else (
                0.7
                if score_val <= 40.0
                else (0.5 if score_val <= 60.0 else (0.3 if score_val <= 80.0 else 0.1))
            )
        )

        return PortfolioDecisionContext(
            allow_trade=allow,
            reduce_position=reduce,
            block_trade=block,
            hedging_required=hedge_required,
            max_contracts=max_contracts,
            remaining_risk_capacity=round(concentration_headroom, 2),
            remaining_capital=round(remaining_capital, 2),
            confidence=conf,
        )

    def _generate_evidence(
        self,
        score_val: float,
        band: PortfolioScoreBand,
        decision_context: PortfolioDecisionContext,
        trade_decision: TradeDecision,
    ) -> Evidence:
        score_val_inv = 100.0 - score_val
        if decision_context.block_trade:
            signal = EvidenceSignal.VERY_BEARISH
        elif decision_context.reduce_position:
            signal = EvidenceSignal.BEARISH
        elif decision_context.allow_trade:
            signal = EvidenceSignal.BULLISH
        else:
            signal = EvidenceSignal.NEUTRAL

        reasons = [
            f"Portfolio Score: {score_val:.1f}/100 ({band.value})",
        ]
        if decision_context.block_trade:
            reasons.append("Trade blocked by portfolio intelligence.")
        if decision_context.reduce_position:
            reasons.append("Reduce position recommended by portfolio intelligence.")
        if decision_context.hedging_required:
            reasons.append("Hedging recommended by portfolio intelligence.")

        evidence_warnings: list[str] = []
        if band == PortfolioScoreBand.CRITICAL:
            evidence_warnings.append("Portfolio score is at critical level.")

        return Evidence(
            source="PortfolioIntelligence",
            category=EvidenceCategory.PORTFOLIO,
            signal=signal,
            score=Score(score_val_inv),
            confidence=Confidence(decision_context.confidence),
            weight=1.0,
            reasons=tuple(reasons),
            warnings=tuple(evidence_warnings),
            metadata={
                "portfolio_score": score_val,
                "portfolio_band": band.value,
                "block_trade": decision_context.block_trade,
                "allow_trade": decision_context.allow_trade,
                "hedging_required": decision_context.hedging_required,
            },
        )

    def _generate_explanation(
        self,
        snapshot: "PortfolioSnapshot",
        exposure: "PortfolioExposure",
        correlation: "CorrelationAnalysis",
        hedging: "HedgingRecommendation",
        decision_context: PortfolioDecisionContext,
        remaining_capital: float,
        capital_efficiency: float,
    ) -> PortfolioExplanation:
        portfolio_summary = (
            f"Portfolio: {snapshot.position_count} position(s), "
            f"capital used {snapshot.capital_used:.2f}, "
            f"available {snapshot.available_capital:.2f}, "
            f"utilisation {snapshot.utilization:.1%}, "
            f"P&L {snapshot.total_pnl:.2f}."
        )

        exposure_text = (
            f"Exposure: Net delta {exposure.net_delta or 'N/A'}, "
            f"net gamma {exposure.net_gamma or 'N/A'}, "
            f"sector concentration {exposure.sector_concentration:.1%}, "
            f"symbol concentration {exposure.symbol_concentration:.1%}."
        )

        correlation_text = (
            f"Correlation: {correlation.highly_correlated_pairs} highly correlated pair(s), "
            f"duplicate exposure {correlation.duplicate_exposure}, "
            f"overall level {correlation.overall_correlation_level.value}."
        )

        allocation_text = (
            f"Capital Allocation: {remaining_capital:.2f} remaining, "
            f"efficiency {capital_efficiency:.2%}."
        )

        hedging_text = (
            f"Hedging: {hedging.action.value.replace('_', ' ').title()}. "
            f"{hedging.reason}"
        )

        if decision_context.block_trade:
            rec = (
                "Recommendation: BLOCK this trade — portfolio limits exceeded. "
                "Reduce existing positions before adding new exposure."
            )
        elif decision_context.reduce_position:
            rec = (
                "Recommendation: REDUCE existing positions. "
                "Portfolio utilisation or concentration limits are near maximum."
            )
        elif decision_context.allow_trade:
            rec = f"Recommendation: ALLOW trade up to {decision_context.max_contracts} contract(s)."
        else:
            rec = "Recommendation: REVIEW portfolio before adding new positions."

        return PortfolioExplanation(
            portfolio_summary=portfolio_summary,
            exposure=exposure_text,
            correlation=correlation_text,
            capital_allocation=allocation_text,
            hedging=hedging_text,
            recommendation=rec,
        )

    def _collect_warnings(
        self,
        snapshot: "PortfolioSnapshot",
        exposure: "PortfolioExposure",
        correlation: "CorrelationAnalysis",
        hedging: "HedgingRecommendation",
        trade_decision: TradeDecision,
    ) -> list[str]:
        warnings: list[str] = []

        if snapshot.utilization >= 0.9:
            warnings.append("Portfolio utilisation is above 90%.")
        if exposure.sector_concentration >= 0.5:
            warnings.append("Sector concentration exceeds 50%.")
        if exposure.symbol_concentration >= 0.3:
            warnings.append("Symbol concentration exceeds 30%.")
        if correlation.overall_correlation_level in (
            CorrelationLevel.HIGH,
            CorrelationLevel.EXTREME,
        ):
            warnings.append("High correlation risk detected.")
        if hedging.action == HedgingAction.REDUCE_EXPOSURE:
            warnings.append("Hedging analysis recommends reducing exposure.")
        warnings.extend(list(trade_decision.warnings))
        return warnings
