from collections.abc import Sequence

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceAggregator,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.options.analytics.base import OptionAnalyzer
from titan.options.analytics.depth import DepthAnalyzer
from titan.options.analytics.executability import ExecutabilityAnalyzer
from titan.options.analytics.models import (
    AnalysisResult,
    DepthAnalysis,
    ExecutabilityAnalysis,
    LiquidityAnalysis,
    LiquidityExplanation,
    OptionChainSnapshot,
    OptionLiquiditySnapshot,
    SlippageAnalysis,
    SpreadAnalysis,
)
from titan.options.analytics.slippage import SlippageAnalyzer
from titan.options.analytics.spread import SpreadAnalyzer


class LiquidityAnalyzer(OptionAnalyzer):
    """Coordinate broker-independent Liquidity Intelligence."""

    name = "LiquidityAnalyzer"

    def __init__(
        self,
        spread_analyzer: SpreadAnalyzer | None = None,
        depth_analyzer: DepthAnalyzer | None = None,
        slippage_analyzer: SlippageAnalyzer | None = None,
        executability_analyzer: ExecutabilityAnalyzer | None = None,
    ) -> None:
        """Create the liquidity coordinator."""

        self._spread_analyzer = spread_analyzer or SpreadAnalyzer()
        self._depth_analyzer = depth_analyzer or DepthAnalyzer()
        self._slippage_analyzer = slippage_analyzer or SlippageAnalyzer()
        self._executability_analyzer = executability_analyzer or ExecutabilityAnalyzer()

    @property
    def components(
        self,
    ) -> tuple[SpreadAnalyzer, DepthAnalyzer, SlippageAnalyzer, ExecutabilityAnalyzer]:
        """Return configured component analyzers."""

        return (
            self._spread_analyzer,
            self._depth_analyzer,
            self._slippage_analyzer,
            self._executability_analyzer,
        )

    def analyze(self, snapshot: OptionChainSnapshot) -> AnalysisResult:
        """Return option-chain compatibility output.

        Liquidity Intelligence is contract-level. Option-chain callers should
        normalize a selected option contract into ``OptionLiquiditySnapshot``
        and call ``evaluate``.
        """

        self._validate_snapshot(snapshot)
        return AnalysisResult(
            score=0.0,
            confidence=0.0,
            bullish=False,
            bearish=False,
            neutral=True,
            reasons=("Liquidity analysis requires a single option contract.",),
            warnings=("No contract-level bid/ask fields were supplied.",),
            metadata={"analyzer": self.name, "contract_level": True},
        )

    def analyze_contract(self, snapshot: OptionLiquiditySnapshot) -> LiquidityAnalysis:
        """Analyze one option contract for execution quality."""

        return self.evaluate(snapshot)

    def evaluate(self, snapshot: OptionLiquiditySnapshot) -> LiquidityAnalysis:
        """Analyze one option contract for execution quality."""

        if not isinstance(snapshot, OptionLiquiditySnapshot):
            raise TypeError("snapshot must be an OptionLiquiditySnapshot.")

        spread = self._spread_analyzer.analyze(snapshot)
        depth = self._depth_analyzer.analyze(snapshot)
        slippage = self._slippage_analyzer.analyze(snapshot, spread, depth)
        executability = self._executability_analyzer.analyze(
            spread,
            depth,
            slippage,
        )
        component_evidence = self._component_evidence(
            spread,
            depth,
            slippage,
            executability,
        )
        aggregator = EvidenceAggregator()
        aggregator.extend(component_evidence)
        warnings = tuple(dict.fromkeys(executability.warnings))
        confidence = aggregator.overall_confidence()
        metadata = self._metadata(
            snapshot,
            spread,
            depth,
            slippage,
            executability,
            component_evidence,
        )
        evidence = Evidence(
            source="Liquidity",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=aggregator.overall_signal(),
            score=Score(aggregator.overall_score()),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._reasons(spread, depth, slippage, executability),
            warnings=warnings,
            metadata=metadata,
        )

        return LiquidityAnalysis(
            spread=spread.spread,
            spread_percent=spread.spread_percent,
            depth_score=depth.depth_score,
            slippage_score=slippage.slippage_score,
            execution_score=executability.execution_score,
            execution_grade=executability.execution_grade,
            confidence=confidence,
            warnings=warnings,
            metadata=metadata,
            evidence=evidence,
            explanation=self._explanation(spread, depth, slippage, executability),
        )

    def to_evidence(self, analysis: LiquidityAnalysis) -> Evidence:
        """Return aggregate Liquidity evidence from an analysis."""

        if not isinstance(analysis, LiquidityAnalysis):
            raise TypeError("analysis must be a LiquidityAnalysis.")
        if analysis.evidence is None:
            raise ValueError("LiquidityAnalysis does not contain evidence.")
        return analysis.evidence

    def _component_evidence(
        self,
        spread: SpreadAnalysis,
        depth: DepthAnalysis,
        slippage: SlippageAnalysis,
        executability: ExecutabilityAnalysis,
    ) -> tuple[Evidence, ...]:
        return (
            self._evidence("Liquidity.Spread", spread.score, spread.confidence, 0.35),
            self._evidence(
                "Liquidity.Depth", depth.depth_score, depth.confidence, 0.25
            ),
            self._evidence(
                "Liquidity.Slippage",
                slippage.slippage_score,
                slippage.confidence,
                0.25,
            ),
            self._evidence(
                "Liquidity.Executability",
                executability.execution_score,
                executability.confidence,
                0.15,
            ),
        )

    def _evidence(
        self,
        source: str,
        score: float,
        confidence: float,
        weight: float,
    ) -> Evidence:
        return Evidence(
            source=source,
            category=EvidenceCategory.OPTION_CHAIN,
            signal=self._signal_from_score(score),
            score=Score(score),
            confidence=Confidence(confidence),
            weight=weight,
        )

    def _signal_from_score(self, score: float) -> EvidenceSignal:
        if score >= 80.0:
            return EvidenceSignal.VERY_BULLISH
        if score >= 60.0:
            return EvidenceSignal.BULLISH
        if score <= 20.0:
            return EvidenceSignal.VERY_BEARISH
        if score <= 40.0:
            return EvidenceSignal.BEARISH
        return EvidenceSignal.NEUTRAL

    def _metadata(
        self,
        snapshot: OptionLiquiditySnapshot,
        spread: SpreadAnalysis,
        depth: DepthAnalysis,
        slippage: SlippageAnalysis,
        executability: ExecutabilityAnalysis,
        component_evidence: Sequence[Evidence],
    ) -> dict[str, object]:
        return {
            "input_fields": {
                "bid_price": snapshot.bid_price,
                "ask_price": snapshot.ask_price,
                "bid_quantity": snapshot.bid_quantity,
                "ask_quantity": snapshot.ask_quantity,
                "last_traded_price": snapshot.last_traded_price,
                "volume": snapshot.volume,
                "open_interest": snapshot.open_interest,
            },
            "components": {
                "spread": spread,
                "depth": depth,
                "slippage": slippage,
                "executability": executability,
            },
            "component_evidence": tuple(component_evidence),
            "source_metadata": dict(snapshot.metadata),
            "future_extensions": (
                "level_2_market_depth",
                "live_order_book",
                "vwap",
                "iceberg_detection",
                "hidden_liquidity",
                "broker_latency",
            ),
        }

    def _reasons(
        self,
        spread: SpreadAnalysis,
        depth: DepthAnalysis,
        slippage: SlippageAnalysis,
        executability: ExecutabilityAnalysis,
    ) -> tuple[str, ...]:
        return (
            self._spread_analyzer.explanation(spread),
            self._depth_analyzer.explanation(depth),
            self._slippage_analyzer.explanation(slippage),
            self._executability_analyzer.explanation(executability),
        )

    def _explanation(
        self,
        spread: SpreadAnalysis,
        depth: DepthAnalysis,
        slippage: SlippageAnalysis,
        executability: ExecutabilityAnalysis,
    ) -> LiquidityExplanation:
        return LiquidityExplanation(
            spread=self._spread_analyzer.explanation(spread),
            depth=self._depth_analyzer.explanation(depth),
            slippage=self._slippage_analyzer.explanation(slippage),
            execution=self._executability_analyzer.explanation(executability),
            warnings=tuple(dict.fromkeys(executability.warnings)),
        )
