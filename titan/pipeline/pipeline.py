from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from titan.brokers.models import Exchange
from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.decision import DecisionEngine, DecisionInput
from titan.decision.journal import DecisionJournal
from titan.events import EventIntelligenceAnalyzer, NewsIntelligenceAnalyzer
from titan.events.models import ArticleCollection
from titan.execution.orchestrator import ExecutionOrchestrator
from titan.intelligence.fusion import FusionEngine
from titan.market.intelligence import (
    BreadthAnalyzer,
    MarketRegimeAnalyzer,
    MarketStructureAnalyzer,
    VolumeAnalyzer,
    VWAPAnalyzer,
)
from titan.market.intelligence.models import MarketBreadthSnapshot
from titan.market.series import MarketDataSeries
from titan.options.analytics import (
    CharmExposureAnalyzer,
    DealerPositioningAnalyzer,
    GammaExposureAnalyzer,
    GreeksAnalyzer,
    LiquidityAnalyzer,
    OptionChainAnalyzer,
    VannaExposureAnalyzer,
    VolatilityAnalyzer,
)
from titan.options.analytics.models import (
    CharmExposureInput,
    DealerPositioningInput,
    GammaExposureInput,
    OptionChainSnapshot,
    VannaExposureInput,
    VolatilitySnapshot,
)
from titan.pipeline.context import PipelineContext
from titan.pipeline.exceptions import (
    PipelineAbortedError,
    PipelineFatalError,
    PipelineRecoverableError,
    PipelineValidationError,
)
from titan.pipeline.hooks import PipelineHooks
from titan.pipeline.models import PipelineReport, PipelineStatus, StageTiming
from titan.pipeline.stages import PipelineStage
from titan.portfolio import PortfolioEngine
from titan.portfolio.models import ExistingPortfolio, PortfolioSnapshot
from titan.risk import RiskEngine
from titan.risk.models import RiskInput, RiskProfile
from titan.trading import TradeQualificationEngine
from titan.trading.models import TradeQualificationInput


def _collect_evidence(
    source: str, category: EvidenceCategory, obj: Any
) -> Evidence | None:
    """Extract or create an Evidence object from a stage result."""
    if obj is None:
        return None
    if hasattr(obj, "evidence") and obj.evidence is not None:
        return obj.evidence  # type: ignore[no-any-return]
    return None


def _default_placeholder(name: str, cat: EvidenceCategory) -> Evidence:
    return Evidence(
        source=name,
        category=cat,
        signal=EvidenceSignal.NEUTRAL,
        score=Score(50.0),
        confidence=Confidence(0.0),
        weight=0.0,
        reasons=(f"{name} stage skipped — no input data.",),
    )


@dataclass(slots=True)
class TradePipeline:
    """Institutional trade pipeline that coordinates all TITAN engines.

    Every intelligence engine is injected as a dependency with sensible
    defaults. The pipeline never duplicates logic — it only orchestrates
    the flow from market data to broker execution.
    """

    # --- market intelligence ---
    _structure_analyzer: MarketStructureAnalyzer = field(
        default_factory=MarketStructureAnalyzer
    )
    _vwap_analyzer: VWAPAnalyzer = field(default_factory=VWAPAnalyzer)
    _volume_analyzer: VolumeAnalyzer = field(default_factory=VolumeAnalyzer)
    _breadth_analyzer: BreadthAnalyzer = field(default_factory=BreadthAnalyzer)
    _regime_analyzer: MarketRegimeAnalyzer = field(default_factory=MarketRegimeAnalyzer)

    # --- options intelligence ---
    _option_chain_analyzer: OptionChainAnalyzer = field(
        default_factory=OptionChainAnalyzer
    )
    _greeks_analyzer: GreeksAnalyzer = field(default_factory=GreeksAnalyzer)
    _liquidity_analyzer: LiquidityAnalyzer = field(default_factory=LiquidityAnalyzer)

    # --- volatility intelligence ---
    _volatility_analyzer: VolatilityAnalyzer = field(default_factory=VolatilityAnalyzer)

    # --- dealer intelligence ---
    _dealer_analyzer: DealerPositioningAnalyzer = field(
        default_factory=DealerPositioningAnalyzer
    )
    _gamma_analyzer: GammaExposureAnalyzer = field(
        default_factory=GammaExposureAnalyzer
    )
    _vanna_analyzer: VannaExposureAnalyzer = field(
        default_factory=VannaExposureAnalyzer
    )
    _charm_analyzer: CharmExposureAnalyzer = field(
        default_factory=CharmExposureAnalyzer
    )

    # --- news & events ---
    _news_analyzer: NewsIntelligenceAnalyzer = field(
        default_factory=NewsIntelligenceAnalyzer
    )
    _event_analyzer: EventIntelligenceAnalyzer = field(
        default_factory=EventIntelligenceAnalyzer
    )

    # --- fusion ---
    _fusion_engine: FusionEngine = field(default_factory=FusionEngine)

    # --- qualification ---
    _qualification_engine: TradeQualificationEngine = field(
        default_factory=TradeQualificationEngine
    )

    # --- risk ---
    _risk_engine: RiskEngine = field(default_factory=RiskEngine)

    # --- decision ---
    _decision_engine: DecisionEngine = field(default_factory=DecisionEngine)

    # --- portfolio ---
    _portfolio_engine: PortfolioEngine = field(default_factory=PortfolioEngine)

    # --- execution ---
    _orchestrator: ExecutionOrchestrator | None = None

    # --- journal ---
    _decision_journal: DecisionJournal | None = None

    # --- lifecycle ---
    _hooks: PipelineHooks = field(default_factory=PipelineHooks)
    _max_retries: int = 0

    def run(
        self,
        symbol: str,
        exchange: Exchange,
        market_data: MarketDataSeries | None = None,
        breadth_snapshot: MarketBreadthSnapshot | None = None,
        option_chain_snapshot: OptionChainSnapshot | None = None,
        volatility_snapshot: VolatilitySnapshot | None = None,
        gamma_exposure_input: GammaExposureInput | None = None,
        dealer_input: DealerPositioningInput | None = None,
        charm_input: CharmExposureInput | None = None,
        vanna_input: VannaExposureInput | None = None,
        articles: ArticleCollection | None = None,
        portfolio: ExistingPortfolio | None = None,
        risk_profile: RiskProfile = RiskProfile.MODERATE,
        total_capital: float = 1_000_000.0,
        underlying_price: float | None = None,
        entry_price: float | None = None,
        abort_on_fatal: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> PipelineReport:
        """Execute the full trade pipeline for a symbol.

        Args:
            symbol: Instrument symbol (e.g. "NIFTY").
            exchange: Target exchange.
            market_data: Pre-fetched OHLCV candle series.
            breadth_snapshot: Market breadth snapshot (optional).
            option_chain_snapshot: Option chain data (optional).
            volatility_snapshot: Volatility snapshot (optional).
            gamma_exposure_input: Gamma exposure input (optional).
            dealer_input: Dealer positioning input (optional).
            charm_input: Charm exposure input (optional).
            vanna_input: Vanna exposure input (optional).
            articles: News articles for analysis (optional).
            portfolio: Current portfolio state (optional).
            risk_profile: Risk tolerance profile.
            total_capital: Total portfolio capital for risk calculations.
            underlying_price: Current underlying price.
            entry_price: Proposed entry price.
            abort_on_fatal: Whether to abort on fatal errors.
            metadata: Optional runtime metadata.

        Returns:
            Complete pipeline report with stage timings and results.
        """
        if not symbol or not symbol.strip():
            raise PipelineValidationError("Symbol must be a non-empty string.")

        context = PipelineContext(
            pipeline_id=str(uuid4()),
            symbol=symbol,
            exchange=exchange,
            start_time=datetime.now(timezone.utc),
            market_data=market_data,
            existing_portfolio=portfolio,
            max_retries=self._max_retries,
            metadata=metadata or {},
        )

        if option_chain_snapshot is not None:
            context.metadata["option_chain_snapshot"] = option_chain_snapshot
        if volatility_snapshot is not None:
            context.metadata["volatility_snapshot"] = volatility_snapshot
        if gamma_exposure_input is not None:
            context.metadata["gamma_exposure_input"] = gamma_exposure_input
        if dealer_input is not None:
            context.metadata["dealer_input"] = dealer_input
        if charm_input is not None:
            context.metadata["charm_input"] = charm_input
        if vanna_input is not None:
            context.metadata["vanna_input"] = vanna_input
        if articles is not None:
            context.metadata["articles"] = articles
        if breadth_snapshot is not None:
            context.metadata["breadth_snapshot"] = breadth_snapshot
        if underlying_price is not None:
            context.metadata["underlying_price"] = underlying_price
        if entry_price is not None:
            context.metadata["entry_price"] = entry_price

        if portfolio is not None:
            ps = PortfolioSnapshot(
                total_capital=portfolio.total_capital,
                cash_reserve=portfolio.cash_reserve,
                capital_used=portfolio.total_capital
                - portfolio.cash_reserve
                - sum(
                    p.market_value for p in portfolio.positions if p.market_value >= 0
                ),
                available_capital=portfolio.cash_reserve,
            )
            context.portfolio_snapshot = ps

        stages = PipelineStage.execution_order()

        for stage in stages:
            if context.aborted:
                break
            if stage == PipelineStage.COMPLETE:
                self._handle_complete(context)
                break

            context.current_stage = stage
            self._execute_stage(context, stage, risk_profile)

            if context.stage_errors.get(stage.value) and abort_on_fatal:
                break

        return self._build_report(context)

    def _execute_stage(
        self, context: PipelineContext, stage: PipelineStage, risk_profile: RiskProfile
    ) -> None:
        handler = self._get_handler(stage)
        attempt = 0
        max_attempts = 1 + context.max_retries
        stage_key = stage.value
        context.stage_attempts[stage_key] = 0

        while attempt < max_attempts:
            attempt += 1
            context.stage_attempts[stage_key] = attempt
            start = datetime.now(timezone.utc)

            try:
                self._hooks.run_before_stage(stage, context)
                result = handler(context, risk_profile)
                duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000.0

                context.stage_results[stage_key] = result
                self._hooks.run_after_stage(stage, context, result, duration)

                timing = StageTiming(
                    stage=stage,
                    start_time=start,
                    end_time=datetime.now(timezone.utc),
                    duration_ms=duration,
                    success=True,
                )
                context.stage_timings[stage_key] = timing

                if stage_key in context.stage_errors:
                    del context.stage_errors[stage_key]
                return

            except PipelineAbortedError:
                context.aborted = True
                timing = StageTiming(
                    stage=stage,
                    start_time=start,
                    end_time=datetime.now(timezone.utc),
                    duration_ms=(datetime.now(timezone.utc) - start).total_seconds()
                    * 1000.0,
                    success=False,
                    error="Pipeline aborted",
                )
                context.stage_timings[stage_key] = timing
                self._hooks.run_on_abort(context)
                return

            except PipelineRecoverableError as exc:
                self._hooks.run_on_retry(stage, context, exc, attempt)
                if attempt >= max_attempts:
                    msg = f"Stage {stage.value} failed after {attempt} attempts: {exc}"
                    context.stage_errors[stage_key] = msg
                    timing = StageTiming(
                        stage=stage,
                        start_time=start,
                        end_time=datetime.now(timezone.utc),
                        duration_ms=(datetime.now(timezone.utc) - start).total_seconds()
                        * 1000.0,
                        success=False,
                        error=msg,
                    )
                    context.stage_timings[stage_key] = timing
                    self._hooks.run_on_error(stage, context, exc)

            except PipelineFatalError as exc:
                msg = f"Fatal error in stage {stage.value}: {exc}"
                context.stage_errors[stage_key] = msg
                timing = StageTiming(
                    stage=stage,
                    start_time=start,
                    end_time=datetime.now(timezone.utc),
                    duration_ms=(datetime.now(timezone.utc) - start).total_seconds()
                    * 1000.0,
                    success=False,
                    error=msg,
                )
                context.stage_timings[stage_key] = timing
                self._hooks.run_on_error(stage, context, exc)
                return

            except Exception as exc:
                msg = f"Unexpected error in stage {stage.value}: {exc}"
                context.stage_errors[stage_key] = msg
                timing = StageTiming(
                    stage=stage,
                    start_time=start,
                    end_time=datetime.now(timezone.utc),
                    duration_ms=(datetime.now(timezone.utc) - start).total_seconds()
                    * 1000.0,
                    success=False,
                    error=msg,
                )
                context.stage_timings[stage_key] = timing
                self._hooks.run_on_error(stage, context, exc)
                return

    def _get_handler(
        self, stage: PipelineStage
    ) -> Callable[[PipelineContext, RiskProfile], Any]:
        handlers: dict[PipelineStage, Callable[[PipelineContext, RiskProfile], Any]] = {
            PipelineStage.PREPARE: self._handle_prepare,
            PipelineStage.MARKET: self._handle_market,
            PipelineStage.OPTIONS: self._handle_options,
            PipelineStage.VOLATILITY: self._handle_volatility,
            PipelineStage.DEALER: self._handle_dealer,
            PipelineStage.NEWS: self._handle_news,
            PipelineStage.EVENTS: self._handle_events,
            PipelineStage.FUSION: self._handle_fusion,
            PipelineStage.QUALIFICATION: self._handle_qualification,
            PipelineStage.RISK: self._handle_risk,
            PipelineStage.DECISION: self._handle_decision,
            PipelineStage.PORTFOLIO: self._handle_portfolio,
            PipelineStage.EXECUTION: self._handle_execution,
            PipelineStage.OMS: self._handle_oms,
            PipelineStage.BROKER: self._handle_broker,
            PipelineStage.COMPLETE: self._handle_complete,
        }
        return handlers[stage]

    # ------------------------------------------------------------------
    # Stage handlers
    # ------------------------------------------------------------------

    def _handle_prepare(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Validate inputs and initialise context metadata."""
        warnings: list[str] = []
        info: dict[str, Any] = {"symbol": ctx.symbol, "exchange": ctx.exchange.value}

        if ctx.market_data is None:
            warnings.append(
                "No market data provided — market intelligence will be limited."
            )
        if ctx.existing_portfolio is None:
            warnings.append(
                "No portfolio provided — portfolio analysis will be limited."
            )

        ctx.metadata["warnings"] = warnings
        return info

    def _handle_market(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Run market intelligence engines."""
        result: dict[str, Any] = {}
        md = ctx.market_data
        if md is None:
            ctx.market_regime = None
            return result

        try:
            struct = self._structure_analyzer.analyze(md)
            ctx.market_structure = struct
            result["market_structure"] = struct

            ev = _collect_evidence(
                "MarketStructureAnalyzer", EvidenceCategory.MARKET_STRUCTURE, struct
            )
            if ev is not None:
                ctx.evidence_items.append(ev)
        except Exception as exc:
            raise PipelineRecoverableError(
                f"Market structure analysis failed: {exc}"
            ) from exc

        try:
            vwap = self._vwap_analyzer.analyze(md)
            ctx.vwap_analysis = vwap
            result["vwap"] = vwap
        except Exception as exc:
            raise PipelineRecoverableError(f"VWAP analysis failed: {exc}") from exc

        try:
            vol = self._volume_analyzer.analyze(md)
            ctx.volume_analysis = vol
            result["volume"] = vol
        except Exception as exc:
            raise PipelineRecoverableError(f"Volume analysis failed: {exc}") from exc

        breadth = ctx.metadata.get("breadth_snapshot")
        if breadth is not None:
            try:
                ba = self._breadth_analyzer.analyze(breadth)
                ctx.breadth_analysis = ba
                result["breadth"] = ba
            except Exception as exc:
                raise PipelineRecoverableError(
                    f"Breadth analysis failed: {exc}"
                ) from exc

        try:
            regime = self._regime_analyzer.analyze(
                market_structure=ctx.market_structure,
                vwap=ctx.vwap_analysis,
                volume=ctx.volume_analysis,
                breadth=ctx.breadth_analysis,
            )
            ctx.market_regime = regime
            result["market_regime"] = regime

            ev = _collect_evidence(
                "MarketRegimeAnalyzer", EvidenceCategory.MARKET_REGIME, regime
            )
            if ev is not None:
                ctx.evidence_items.append(ev)
        except Exception as exc:
            raise PipelineRecoverableError(
                f"Market regime analysis failed: {exc}"
            ) from exc

        return result

    def _handle_options(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Run options intelligence engines."""
        result: dict[str, Any] = {}
        snapshot = ctx.metadata.get("option_chain_snapshot")
        if snapshot is None:
            return result

        try:
            chain = self._option_chain_analyzer.analyze(snapshot)
            ctx.option_chain = chain
            result["option_chain"] = chain
            ev = _collect_evidence(
                "OptionChainAnalyzer", EvidenceCategory.OPTION_CHAIN, chain
            )
            if ev is not None:
                ctx.evidence_items.append(ev)
        except Exception as exc:
            raise PipelineRecoverableError(
                f"Option chain analysis failed: {exc}"
            ) from exc

        try:
            greeks = self._greeks_analyzer.analyze(snapshot)
            ctx.greeks = greeks
            result["greeks"] = greeks
        except Exception as exc:
            raise PipelineRecoverableError(f"Greeks analysis failed: {exc}") from exc

        try:
            liq = self._liquidity_analyzer.analyze(snapshot)
            ctx.liquidity = liq  # type: ignore[assignment]
            result["liquidity"] = liq
        except Exception as exc:
            raise PipelineRecoverableError(f"Liquidity analysis failed: {exc}") from exc

        return result

    def _handle_volatility(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Run volatility intelligence engines."""
        result: dict[str, Any] = {}
        snapshot = ctx.metadata.get("volatility_snapshot")
        if snapshot is None:
            return result

        try:
            vol = self._volatility_analyzer.analyze(snapshot)
            ctx.volatility = vol
            result["volatility"] = vol
            ev = _collect_evidence(
                "VolatilityAnalyzer", EvidenceCategory.VOLATILITY, vol
            )
            if ev is not None:
                ctx.evidence_items.append(ev)
        except Exception as exc:
            raise PipelineRecoverableError(
                f"Volatility analysis failed: {exc}"
            ) from exc

        return result

    def _handle_dealer(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Run dealer intelligence engines."""
        result: dict[str, Any] = {}
        gamma_input = ctx.metadata.get("gamma_exposure_input")
        dealer_input = ctx.metadata.get("dealer_input")

        if gamma_input is not None:
            try:
                ge = self._gamma_analyzer.analyze(gamma_input)
                ctx.gamma_exposure = ge
                result["gamma_exposure"] = ge
            except Exception as exc:
                raise PipelineRecoverableError(
                    f"Gamma exposure analysis failed: {exc}"
                ) from exc

            if dealer_input is not None:
                try:
                    de = self._dealer_analyzer.analyze(dealer_input)
                    ctx.dealer_positioning = de
                    result["dealer_positioning"] = de
                except Exception as exc:
                    raise PipelineRecoverableError(
                        f"Dealer positioning analysis failed: {exc}"
                    ) from exc

        charm = ctx.metadata.get("charm_input")
        if charm is not None:
            try:
                ce = self._charm_analyzer.analyze(charm)
                ctx.charm_exposure = ce
                result["charm_exposure"] = ce
            except Exception as exc:
                raise PipelineRecoverableError(
                    f"Charm exposure analysis failed: {exc}"
                ) from exc

        vanna = ctx.metadata.get("vanna_input")
        if vanna is not None:
            try:
                ve = self._vanna_analyzer.analyze(vanna)
                ctx.vanna_exposure = ve
                result["vanna_exposure"] = ve
            except Exception as exc:
                raise PipelineRecoverableError(
                    f"Vanna exposure analysis failed: {exc}"
                ) from exc

        if ctx.dealer_positioning is not None:
            ev = _collect_evidence(
                "DealerPositioningAnalyzer",
                EvidenceCategory.MARKET_STRUCTURE,
                ctx.dealer_positioning,
            )
            if ev is not None:
                ctx.evidence_items.append(ev)

        return result

    def _handle_news(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Run news intelligence engine."""
        result: dict[str, Any] = {}
        articles = ctx.metadata.get("articles")
        if articles is None:
            return result

        try:
            news = self._news_analyzer.analyze(articles)
            ctx.news = news
            result["news"] = news
            ev = _collect_evidence(
                "NewsIntelligenceAnalyzer", EvidenceCategory.NEWS, news
            )
            if ev is not None:
                ctx.evidence_items.append(ev)
        except Exception as exc:
            raise PipelineRecoverableError(f"News intelligence failed: {exc}") from exc

        return result

    def _handle_events(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Run event intelligence engine."""
        result: dict[str, Any] = {}

        try:
            events = self._event_analyzer.analyze(
                economic_events=ctx.metadata.get("economic_events", ()),
                corporate_events=ctx.metadata.get("corporate_events", ()),
            )
            ctx.events = events
            result["events"] = events
            ev = _collect_evidence(
                "EventIntelligenceAnalyzer", EvidenceCategory.EVENT, events
            )
            if ev is not None:
                ctx.evidence_items.append(ev)
        except Exception as exc:
            raise PipelineRecoverableError(f"Event intelligence failed: {exc}") from exc

        return result

    def _handle_fusion(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Fuse all collected evidence into a single intelligence assessment."""
        result: dict[str, Any] = {}

        if not ctx.evidence_items:
            return result

        try:
            engine = self._fusion_engine
            engine.clear()
            for ev in ctx.evidence_items:
                if ev is not None:
                    engine.add_evidence(ev)

            fusion = engine.fuse()
            ctx.fusion = fusion
            result["fusion"] = fusion

            ev = _collect_evidence("FusionEngine", EvidenceCategory.SYSTEM, fusion)
            if ev is not None:
                ctx.evidence_items.append(ev)
        except Exception as exc:
            raise PipelineRecoverableError(f"Evidence fusion failed: {exc}") from exc

        return result

    def _handle_qualification(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Run trade qualification engine."""
        result: dict[str, Any] = {}

        q_input = TradeQualificationInput(
            market_regime=ctx.market_regime,
            option_chain=ctx.option_chain,
            greeks=ctx.greeks,
            liquidity=ctx.liquidity,
            volatility=ctx.volatility,
            dealer_positioning=ctx.dealer_positioning,
            gamma_exposure=ctx.gamma_exposure,
            vanna_exposure=ctx.vanna_exposure,
            charm_exposure=ctx.charm_exposure,
            event_analysis=ctx.events,
            news_analysis=ctx.news,
            intelligence_fusion=ctx.fusion,
        )

        try:
            qual = self._qualification_engine.qualify(q_input)
            ctx.qualification = qual
            result["qualification"] = qual
            ev = _collect_evidence(
                "TradeQualificationEngine", EvidenceCategory.TRADE_QUALIFICATION, qual
            )
            if ev is not None:
                ctx.evidence_items.append(ev)
        except Exception as exc:
            raise PipelineFatalError(f"Trade qualification failed: {exc}") from exc

        return result

    def _handle_risk(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Run risk intelligence engine."""
        result: dict[str, Any] = {}

        if ctx.qualification is None:
            return result

        try:
            r_input = RiskInput(
                trade_qualification=ctx.qualification,
                market_regime=ctx.market_regime,
                volatility=ctx.volatility,
                liquidity=ctx.liquidity,
                dealer_positioning=ctx.dealer_positioning,
                gamma_exposure=ctx.gamma_exposure,
                event_analysis=ctx.events,
                news_analysis=ctx.news,
                intelligence_fusion=ctx.fusion,
                underlying_price=ctx.metadata.get("underlying_price"),
                entry_price=ctx.metadata.get("entry_price"),
            )
            risk = self._risk_engine.analyze(
                risk_input=r_input,
                risk_profile=risk_profile,
                total_capital=(
                    ctx.existing_portfolio.total_capital
                    if ctx.existing_portfolio
                    else 1_000_000.0
                ),
            )
            ctx.risk = risk
            result["risk"] = risk
            ev = _collect_evidence("RiskEngine", EvidenceCategory.RISK, risk)
            if ev is not None:
                ctx.evidence_items.append(ev)
        except Exception as exc:
            raise PipelineFatalError(f"Risk analysis failed: {exc}") from exc

        return result

    def _handle_decision(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Run decision engine."""
        result: dict[str, Any] = {}

        if ctx.qualification is None or ctx.risk is None:
            return result

        try:
            d_input = DecisionInput(
                trade_qualification=ctx.qualification,
                risk_analysis=ctx.risk,
                market_regime=ctx.market_regime,
                option_chain=ctx.option_chain,
                greeks=ctx.greeks,
                liquidity=ctx.liquidity,
                volatility=ctx.volatility,
                dealer_positioning=ctx.dealer_positioning,
                gamma_exposure=ctx.gamma_exposure,
                vanna_exposure=ctx.vanna_exposure,
                charm_exposure=ctx.charm_exposure,
                event_analysis=ctx.events,
                news_analysis=ctx.news,
                intelligence_fusion=ctx.fusion,
                underlying_price=ctx.metadata.get("underlying_price"),
                symbol=ctx.symbol,
            )
            decision = self._decision_engine.decide(d_input)
            ctx.decision = decision
            result["decision"] = decision

            if self._decision_journal is not None:
                self._decision_journal.record_decision(decision)
        except Exception as exc:
            raise PipelineFatalError(f"Decision engine failed: {exc}") from exc

        return result

    def _handle_portfolio(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Run portfolio intelligence engine."""
        result: dict[str, Any] = {}

        if ctx.decision is None or ctx.risk is None:
            return result
        portfolio = ctx.existing_portfolio
        if portfolio is None:
            return result

        try:
            pa = self._portfolio_engine.analyze(
                trade_decision=ctx.decision,
                risk_analysis=ctx.risk,
                portfolio=portfolio,
            )
            ctx.portfolio = pa
            ctx.portfolio_snapshot = pa.snapshot
            result["portfolio"] = pa
            ev = _collect_evidence("PortfolioEngine", EvidenceCategory.PORTFOLIO, pa)
            if ev is not None:
                ctx.evidence_items.append(ev)
        except Exception as exc:
            raise PipelineRecoverableError(f"Portfolio analysis failed: {exc}") from exc

        return result

    def _handle_execution(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Run execution orchestrator."""
        result: dict[str, Any] = {}

        if ctx.decision is None:
            return result
        if self._orchestrator is None:
            return result
        ps = ctx.portfolio_snapshot
        if ps is None:
            ps = PortfolioSnapshot()
        risk = ctx.risk
        if risk is None:
            return result

        try:
            report = self._orchestrator.execute(
                decision=ctx.decision,
                portfolio=ps,
                risk=risk,
            )
            ctx.execution = report
            result["execution"] = report
        except Exception as exc:
            raise PipelineRecoverableError(f"Execution failed: {exc}") from exc

        return result

    def _handle_oms(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Report on OMS order state (passive reporting stage)."""
        result: dict[str, Any] = {}
        if ctx.execution is not None:
            result["orders_submitted"] = ctx.execution.orders_submitted
            result["orders_accepted"] = ctx.execution.orders_accepted
            result["orders_rejected"] = ctx.execution.orders_rejected
        return result

    def _handle_broker(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        """Report on broker execution state (passive reporting stage)."""
        result: dict[str, Any] = {}
        if ctx.execution is not None:
            result["broker_order_ids"] = ctx.execution.broker_order_ids
        return result

    def _handle_complete(
        self, ctx: PipelineContext, risk_profile: RiskProfile = RiskProfile.MODERATE
    ) -> dict[str, Any]:
        """Finalise pipeline state."""
        self._hooks.run_on_complete(ctx, self._build_report(ctx))
        return {"status": "complete"}

    # ------------------------------------------------------------------
    # Report building
    # ------------------------------------------------------------------

    def _build_report(self, ctx: PipelineContext) -> PipelineReport:
        end = datetime.now(timezone.utc)
        total_duration = (end - ctx.start_time).total_seconds() * 1000.0

        stages: list[StageTiming] = []
        for stage in PipelineStage.execution_order():
            timing = ctx.stage_timings.get(stage.value)
            if timing is not None:
                stages.append(timing)

        errors: list[str] = []
        warnings: list[str] = []
        for stage_key, err in ctx.stage_errors.items():
            errors.append(f"[{stage_key}] {err}")
        for w in ctx.metadata.get("warnings", []):
            warnings.append(w)

        decision_action = None
        if ctx.decision is not None:
            decision_action = (
                ctx.decision.decision.value
                if hasattr(ctx.decision.decision, "value")
                else str(ctx.decision.decision)
            )

        orders_submitted = 0
        orders_accepted = 0
        orders_rejected = 0
        broker_ids: tuple[str, ...] = ()
        exec_result = None
        if ctx.execution is not None:
            orders_submitted = ctx.execution.orders_submitted
            orders_accepted = ctx.execution.orders_accepted
            orders_rejected = ctx.execution.orders_rejected
            broker_ids = ctx.execution.broker_order_ids
            exec_result = (
                "executed" if ctx.execution.orders_submitted > 0 else "no_orders"
            )

        if len(errors) >= len(stages):
            status = PipelineStatus.FAILED
        elif errors:
            status = PipelineStatus.PARTIAL
        elif ctx.aborted:
            status = PipelineStatus.ABORTED
        else:
            status = PipelineStatus.SUCCESS

        return PipelineReport(
            pipeline_id=ctx.pipeline_id,
            symbol=ctx.symbol,
            exchange=ctx.exchange.value,
            status=status,
            stages=tuple(stages),
            evidence_count=len(ctx.evidence_items),
            decision_action=decision_action,
            orders_submitted=orders_submitted,
            orders_accepted=orders_accepted,
            orders_rejected=orders_rejected,
            broker_order_ids=broker_ids,
            execution_result=exec_result,
            warnings=tuple(warnings),
            errors=tuple(errors),
            start_time=ctx.start_time,
            end_time=end,
            total_duration_ms=total_duration,
            metadata=dict(ctx.metadata),
        )
