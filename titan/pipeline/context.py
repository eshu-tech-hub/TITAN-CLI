from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from titan.brokers.models import Exchange
from titan.decision.models import TradeDecision
from titan.events.models import EventAnalysis, NewsAnalysis
from titan.execution.orchestrator import OrchestratorReport
from titan.intelligence.fusion.models import IntelligenceFusion
from titan.market.series import MarketDataSeries
from titan.market.intelligence.models import (
    BreadthAnalysis,
    MarketRegimeAnalysis,
    MarketStructureAnalysis,
    VolumeAnalysis,
    VWAPAnalysis,
)
from titan.options.analytics.models import (
    CharmExposureAnalysis,
    DealerPositioningAnalysis,
    GammaExposureAnalysis,
    GreeksAnalysis,
    LiquidityAnalysis,
    OptionChainAnalysis,
    VannaExposureAnalysis,
    VolatilityAnalysis,
)
from titan.pipeline.stages import PipelineStage
from titan.portfolio.models import (
    ExistingPortfolio,
    PortfolioAnalysis,
    PortfolioSnapshot,
)
from titan.risk.models import RiskAnalysis
from titan.trading.models import TradeQualification


@dataclass(slots=True)
class PipelineContext:
    """Mutable context that accumulates state as pipeline stages execute.

    Every intelligence engine output is stored here for downstream stages.
    """

    # --- identity ---
    pipeline_id: str
    symbol: str
    exchange: Exchange
    start_time: datetime = field(default_factory=datetime.utcnow)

    # --- market intelligence ---
    market_data: MarketDataSeries | None = None
    market_structure: MarketStructureAnalysis | None = None
    vwap_analysis: VWAPAnalysis | None = None
    volume_analysis: VolumeAnalysis | None = None
    breadth_analysis: BreadthAnalysis | None = None
    market_regime: MarketRegimeAnalysis | None = None

    # --- options intelligence ---
    option_chain: OptionChainAnalysis | None = None
    greeks: GreeksAnalysis | None = None
    liquidity: LiquidityAnalysis | None = None

    # --- volatility intelligence ---
    volatility: VolatilityAnalysis | None = None

    # --- dealer intelligence ---
    dealer_positioning: DealerPositioningAnalysis | None = None
    gamma_exposure: GammaExposureAnalysis | None = None
    vanna_exposure: VannaExposureAnalysis | None = None
    charm_exposure: CharmExposureAnalysis | None = None

    # --- news & events ---
    news: NewsAnalysis | None = None
    events: EventAnalysis | None = None

    # --- evidence & fusion ---
    evidence_items: list[Any] = field(default_factory=list)
    fusion: IntelligenceFusion | None = None

    # --- qualification ---
    qualification: TradeQualification | None = None

    # --- risk ---
    risk: RiskAnalysis | None = None

    # --- decision ---
    decision: TradeDecision | None = None

    # --- portfolio ---
    portfolio: PortfolioAnalysis | None = None
    portfolio_snapshot: PortfolioSnapshot | None = None
    existing_portfolio: ExistingPortfolio | None = None

    # --- execution ---
    execution: OrchestratorReport | None = None
    orders: tuple[Any, ...] = field(default_factory=tuple)

    # --- broker ---
    broker_responses: tuple[Any, ...] = field(default_factory=tuple)

    # --- runtime ---
    metadata: dict[str, Any] = field(default_factory=dict)
    stage_timings: dict[str, Any] = field(default_factory=dict)
    stage_results: dict[str, Any] = field(default_factory=dict)
    stage_errors: dict[str, str] = field(default_factory=dict)
    aborted: bool = False
    current_stage: PipelineStage | None = None
    max_retries: int = 0
    stage_attempts: dict[str, int] = field(default_factory=dict)
