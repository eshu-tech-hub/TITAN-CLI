"""TUI dashboard data models.

Lightweight snapshot of all manager states for the dashboard.
No business logic — pure data transfer objects.
"""

from __future__ import annotations

from titan.portfolio.models import (
    AllocationAnalysis,
    DiversificationAnalysis,
    DrawdownAnalysis,
    ExposureAnalysis,
    PortfolioPerformance,
    PortfolioSnapshot,
)

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RuntimeInfo:
    """Snapshot of runtime engine state."""

    status: str = "Unknown"
    uptime: str = "00:00:00"
    is_running: bool = False
    pipeline_executions: int = 0
    broker_status: str = "Disconnected"
    stream_status: str = "Disconnected"


@dataclass(frozen=True, slots=True)
class MarketInfo:
    """Snapshot of market connectivity state."""

    broker_connected: bool = False
    broker_provider: str = "None"
    stream_connected: bool = False
    symbols_tracked: int = 0
    last_quote_time: str = "Never"


@dataclass(frozen=True, slots=True)
class TradingInfo:
    """Snapshot of trading subsystem state."""

    live_status: str = "Stopped"
    paper_status: str = "Stopped"
    backtests_today: int = 0
    active_positions: int = 0
    pending_orders: int = 0


@dataclass(frozen=True, slots=True)
class HealthInfo:
    """Snapshot of health and monitoring state."""

    monitoring_status: str = "Unknown"
    critical_alerts: int = 0
    total_alerts: int = 0
    recovery_status: str = "Idle"
    recovery_attempts: int = 0
    health_probes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SystemInfo:
    """Snapshot of system/deployment state."""

    version: str = "1.0.0"
    environment: str = "Development"
    deployment_status: str = "Stopped"
    uptime: str = "00:00:00"
    python_version: str = ""
    log_level: str = "INFO"


@dataclass(frozen=True, slots=True)
class DashboardState:
    """Complete snapshot of all dashboard data.

    Collected from all managers in a single pass.
    Widgets receive this object for rendering.
    """

    runtime: RuntimeInfo = field(default_factory=RuntimeInfo)
    market: MarketInfo = field(default_factory=MarketInfo)
    trading: TradingInfo = field(default_factory=TradingInfo)
    health: HealthInfo = field(default_factory=HealthInfo)
    system: SystemInfo = field(default_factory=SystemInfo)
    last_refresh: str = ""


@dataclass(frozen=True, slots=True)
class RuntimeEngineInfo:
    """Snapshot of runtime engine state for the Runtime screen."""

    status: str = "Unknown"
    uptime: str = "00:00:00"
    is_running: bool = False
    scheduler_active: bool = False


@dataclass(frozen=True, slots=True)
class RuntimeStreamInfo:
    """Snapshot of market stream state for the Runtime screen."""

    connected: bool = False
    symbols_tracked: int = 0
    tick_rate: str = "N/A"


@dataclass(frozen=True, slots=True)
class RuntimePipelineInfo:
    """Snapshot of pipeline state for the Runtime screen."""

    executions: int = 0
    avg_runtime: str = "N/A"
    last_run: str = "Never"


@dataclass(frozen=True, slots=True)
class RuntimeEventBusInfo:
    """Snapshot of event bus state for the Runtime screen."""

    published: int = 0
    subscribers: int = 0


@dataclass(frozen=True, slots=True)
class RuntimeComponentInfo:
    """Health of a single runtime component."""

    name: str = ""
    status: str = "Unknown"


@dataclass(frozen=True, slots=True)
class RuntimeEventEntry:
    """A single runtime event for the event history."""

    level: str = "info"
    source: str = ""
    message: str = ""


@dataclass(frozen=True, slots=True)
class RuntimeScreenState:
    """Complete snapshot for the Runtime screen."""

    engine: RuntimeEngineInfo = field(default_factory=RuntimeEngineInfo)
    stream: RuntimeStreamInfo = field(default_factory=RuntimeStreamInfo)
    pipeline: RuntimePipelineInfo = field(default_factory=RuntimePipelineInfo)
    event_bus: RuntimeEventBusInfo = field(default_factory=RuntimeEventBusInfo)
    components: tuple[RuntimeComponentInfo, ...] = ()
    events: tuple[RuntimeEventEntry, ...] = ()
    last_refresh: str = ""


# ─── Paper Trading screen models ────────────────────────────


@dataclass(frozen=True, slots=True)
class PaperSessionInfo:
    """Snapshot of paper trading session state."""

    status: str = "Stopped"
    started: str = "--:--"
    duration: str = "00:00"


@dataclass(frozen=True, slots=True)
class PaperAccountInfo:
    """Snapshot of paper account funds and margin state."""

    available_cash: str = "₹0"
    used_margin: str = "₹0"
    available_margin: str = "₹0"
    payin: str = "₹0"
    payout: str = "₹0"


@dataclass(frozen=True, slots=True)
class PaperOrderEntry:
    """A single order for the active orders table."""

    order_id: str = ""
    symbol: str = ""
    side: str = ""
    order_type: str = ""
    quantity: int = 0
    filled_quantity: int = 0
    price: str = ""
    status: str = ""
    placed_at: str = ""


@dataclass(frozen=True, slots=True)
class PaperPortfolioInfo:
    """Snapshot of paper portfolio state."""

    cash: str = "₹0"
    equity: str = "₹0"
    unrealized_pnl: str = "+₹0"
    realized_pnl: str = "+₹0"


@dataclass(frozen=True, slots=True)
class PaperPerformanceInfo:
    """Snapshot of paper trading performance metrics."""

    total_trades: int = 0
    win_rate: str = "0%"
    profit_factor: str = "0.00"
    expectancy: str = "+0.00R"
    max_drawdown: str = "0%"


@dataclass(frozen=True, slots=True)
class PaperPositionEntry:
    """A single position for the position table."""

    symbol: str = ""
    quantity: int = 0
    avg_price: str = "0"
    current_price: str = "0"
    unrealized_pnl: str = "+₹0"


@dataclass(frozen=True, slots=True)
class PaperTradeEntry:
    """A single trade for the trade history."""

    symbol: str = ""
    side: str = ""
    quantity: int = 0
    price: str = "0"
    pnl: str = "+₹0"
    time: str = ""


@dataclass(frozen=True, slots=True)
class PaperScreenState:
    """Complete snapshot for the Paper Trading screen."""

    session: PaperSessionInfo = field(default_factory=PaperSessionInfo)
    account: PaperAccountInfo = field(default_factory=PaperAccountInfo)
    portfolio: PaperPortfolioInfo = field(default_factory=PaperPortfolioInfo)
    performance: PaperPerformanceInfo = field(default_factory=PaperPerformanceInfo)
    positions: tuple[PaperPositionEntry, ...] = ()
    orders: tuple[PaperOrderEntry, ...] = ()
    trades: tuple[PaperTradeEntry, ...] = ()
    last_refresh: str = ""


# ─── Market Intelligence screen models ────────────────────────────


@dataclass(frozen=True, slots=True)
class MarketStatusInfo:
    """Snapshot of overall market status."""

    runtime_status: str = "Unavailable"
    broker_status: str = "Unavailable"
    active_subscriptions: int = 0
    last_quote_time: str = ""


@dataclass(frozen=True, slots=True)
class RegimeInfo:
    """Market regime intelligence."""

    regime: str = "Unavailable"
    trend_strength: str = ""
    participation: str = ""
    institutional_confirmation: str = ""
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class VolatilityInfo:
    """Volatility intelligence."""

    current_iv: float = 0.0
    current_hv: float = 0.0
    iv_rank: float = 0.0
    iv_percentile: float = 0.0
    regime: str = "Unavailable"
    trend: str = "Unavailable"
    overall_bias: str = "Unavailable"


@dataclass(frozen=True, slots=True)
class LiquidityInfo:
    """Liquidity intelligence."""

    spread: float = 0.0
    spread_percent: float = 0.0
    depth_score: float = 0.0
    execution_score: float = 0.0
    execution_grade: str = "Unavailable"


@dataclass(frozen=True, slots=True)
class OptionChainSummaryInfo:
    """Option chain summary intelligence."""

    overall_bias: str = "Unavailable"
    pcr: float = 0.0
    support: float = 0.0
    resistance: float = 0.0
    bullish_score: float = 0.0
    bearish_score: float = 0.0


@dataclass(frozen=True, slots=True)
class OpenInterestSummaryInfo:
    """Open interest summary intelligence."""

    bias: str = "Unavailable"
    score: float = 0.0
    confidence: float = 0.0
    bullish_factors: tuple[str, ...] = ()
    bearish_factors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GreeksSummaryInfo:
    """Greeks summary intelligence."""

    net_delta: float = 0.0
    net_gamma: float = 0.0
    net_theta: float = 0.0
    net_vega: float = 0.0
    overall_bias: str = "Unavailable"


@dataclass(frozen=True, slots=True)
class EvidenceSummaryInfo:
    """Evidence engine summary."""

    overall_score: float = 0.0
    overall_signal: str = "Unavailable"
    confidence: float = 0.0
    evidence_count: int = 0
    top_factors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MarketEventEntry:
    """A recent market event."""

    timestamp: str = ""
    source: str = ""
    message: str = ""
    severity: str = "info"


@dataclass(frozen=True, slots=True)
class MarketScreenState:
    """Complete snapshot for the Market Intelligence screen."""

    market_status: MarketStatusInfo = field(default_factory=MarketStatusInfo)
    regime: RegimeInfo = field(default_factory=RegimeInfo)
    volatility: VolatilityInfo = field(default_factory=VolatilityInfo)
    liquidity: LiquidityInfo = field(default_factory=LiquidityInfo)
    option_chain: OptionChainSummaryInfo = field(default_factory=OptionChainSummaryInfo)
    open_interest: OpenInterestSummaryInfo = field(
        default_factory=OpenInterestSummaryInfo
    )
    greeks: GreeksSummaryInfo = field(default_factory=GreeksSummaryInfo)
    evidence: EvidenceSummaryInfo = field(default_factory=EvidenceSummaryInfo)
    events: tuple[MarketEventEntry, ...] = ()
    last_refresh: str = ""


# ─── Live Trading screen models ────────────────────────────


@dataclass(frozen=True, slots=True)
class LiveStatusInfo:
    """Snapshot of live trading engine status."""

    status: str = "Stopped"
    uptime: str = "00:00:00"
    is_running: bool = False
    broker_connected: bool = False
    stream_connected: bool = False
    pipeline_executions: int = 0


@dataclass(frozen=True, slots=True)
class BrokerStatusInfo:
    """Snapshot of broker connection and provider state."""

    provider: str = "None"
    connection_status: str = "Disconnected"
    is_connected: bool = False
    exchange: str = ""
    account_id: str = ""


@dataclass(frozen=True, slots=True)
class AccountInfo:
    """Snapshot of live account funds and margin state."""

    available_cash: str = "₹0"
    used_margin: str = "₹0"
    available_margin: str = "₹0"
    payin: str = "₹0"
    payout: str = "₹0"


@dataclass(frozen=True, slots=True)
class ExposureInfo:
    """Snapshot of portfolio exposure metrics."""

    total_positions: int = 0
    long_positions: int = 0
    short_positions: int = 0
    gross_exposure: str = "₹0"
    net_exposure: str = "₹0"
    unrealized_pnl: str = "+₹0"


@dataclass(frozen=True, slots=True)
class LivePositionEntry:
    """A single open position for the live positions table."""

    symbol: str = ""
    exchange: str = ""
    product: str = ""
    quantity: int = 0
    buy_qty: int = 0
    sell_qty: int = 0
    avg_price: str = "0"
    current_price: str = "0"
    pnl: str = "+₹0"
    realised_pnl: str = "+₹0"


@dataclass(frozen=True, slots=True)
class LiveOrderEntry:
    """A single order for the live active orders table."""

    order_id: str = ""
    symbol: str = ""
    side: str = ""
    order_type: str = ""
    quantity: int = 0
    filled_quantity: int = 0
    price: str = ""
    status: str = ""
    placed_at: str = ""


@dataclass(frozen=True, slots=True)
class ExecutionEntry:
    """A single recent execution (trade fill)."""

    trade_id: str = ""
    order_id: str = ""
    symbol: str = ""
    side: str = ""
    quantity: int = 0
    price: str = ""
    time: str = ""


@dataclass(frozen=True, slots=True)
class LiveScreenState:
    """Complete snapshot for the Live Trading screen."""

    live_status: LiveStatusInfo = field(default_factory=LiveStatusInfo)
    broker_status: BrokerStatusInfo = field(default_factory=BrokerStatusInfo)
    account: AccountInfo = field(default_factory=AccountInfo)
    exposure: ExposureInfo = field(default_factory=ExposureInfo)
    positions: tuple[LivePositionEntry, ...] = ()
    orders: tuple[LiveOrderEntry, ...] = ()
    executions: tuple[ExecutionEntry, ...] = ()
    last_refresh: str = ""


# ─── Monitoring & Alerting screen models ────────────────────────────


@dataclass(frozen=True, slots=True)
class SubsystemHealthEntry:
    """Health of a single monitored subsystem."""

    name: str = ""
    status: str = "Unknown"
    message: str = ""
    latency_ms: str = "0"
    failures: int = 0


@dataclass(frozen=True, slots=True)
class SystemHealthInfo:
    """Snapshot of overall system health."""

    overall_status: str = "Unknown"
    healthy_count: int = 0
    warning_count: int = 0
    critical_count: int = 0
    offline_count: int = 0
    subsystems: tuple[SubsystemHealthEntry, ...] = ()


@dataclass(frozen=True, slots=True)
class TelemetryInfo:
    """Snapshot of telemetry collection state."""

    total_metrics: int = 0
    active_collectors: int = 0
    failed_collections: int = 0
    total_collections: int = 0
    uptime: str = "00:00:00"


@dataclass(frozen=True, slots=True)
class ResourceMetricEntry:
    """A single resource metric for the metrics table."""

    name: str = ""
    value: str = "0"
    unit: str = ""
    trend: str = "stable"


@dataclass(frozen=True, slots=True)
class ResourceMetricsInfo:
    """Snapshot of resource metrics summaries."""

    metrics: tuple[ResourceMetricEntry, ...] = ()


@dataclass(frozen=True, slots=True)
class AlertSummaryInfo:
    """Snapshot of alert counts by status."""

    total: int = 0
    active: int = 0
    critical: int = 0
    acknowledged: int = 0
    resolved: int = 0
    escalated: int = 0


@dataclass(frozen=True, slots=True)
class AlertEntry:
    """A single active alert for the active alerts list."""

    alert_id: str = ""
    level: str = ""
    source: str = ""
    title: str = ""
    message: str = ""
    status: str = ""
    timestamp_str: str = ""


@dataclass(frozen=True, slots=True)
class AlertHistoryEntry:
    """A single alert history entry."""

    alert_id: str = ""
    level: str = ""
    source: str = ""
    title: str = ""
    status: str = ""
    timestamp_str: str = ""
    duration: str = ""


@dataclass(frozen=True, slots=True)
class RecoveryStatusInfo:
    """Snapshot of recovery framework state."""

    status: str = "Idle"
    total_attempts: int = 0
    successful: int = 0
    failed: int = 0
    last_strategy: str = ""
    recovered_components: str = ""


@dataclass(frozen=True, slots=True)
class MonitoringEventEntry:
    """A single monitoring event for the events list."""

    level: str = "info"
    source: str = ""
    message: str = ""
    timestamp_str: str = ""


@dataclass(frozen=True, slots=True)
class MonitoringScreenState:
    """Complete snapshot for the Monitoring & Alerting screen."""

    system_health: SystemHealthInfo = field(default_factory=SystemHealthInfo)
    telemetry: TelemetryInfo = field(default_factory=TelemetryInfo)
    resource_metrics: ResourceMetricsInfo = field(default_factory=ResourceMetricsInfo)
    alert_summary: AlertSummaryInfo = field(default_factory=AlertSummaryInfo)
    active_alerts: tuple[AlertEntry, ...] = ()
    alert_history: tuple[AlertHistoryEntry, ...] = ()
    recovery_status: RecoveryStatusInfo = field(default_factory=RecoveryStatusInfo)
    monitoring_events: tuple[MonitoringEventEntry, ...] = ()
    last_refresh: str = ""


# ─── Audit, Logs & Recovery screen DTOs ──────────────────────────


@dataclass(frozen=True, slots=True)
class AuditSummaryInfo:
    """Snapshot of audit trail summary."""

    total_events: int = 0
    events_by_source: str = ""
    events_by_severity: str = ""
    integrity_status: str = "unknown"
    verification_failures: int = 0
    first_event_time: str = ""
    last_event_time: str = ""


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """A single audit event for the recent audit list."""

    event_id: str = ""
    sequence: int = 0
    source: str = ""
    category: str = ""
    severity: str = ""
    action: str = ""
    result: str = ""
    timestamp_str: str = ""


@dataclass(frozen=True, slots=True)
class LogSummaryInfo:
    """Snapshot of logging framework state."""

    level: str = "INFO"
    handler_count: int = 0
    component_count: int = 0
    dropped_messages: int = 0
    warning_count: int = 0
    error_count: int = 0


@dataclass(frozen=True, slots=True)
class LogEntry:
    """A single log line for the recent logs list."""

    timestamp_str: str = ""
    level: str = ""
    module: str = ""
    component: str = ""
    message: str = ""


@dataclass(frozen=True, slots=True)
class RecoveryHistoryEntry:
    """A single recovery history event."""

    request_id: str = ""
    component: str = ""
    strategy: str = ""
    status: str = ""
    attempts: int = 0
    failure_reason: str = ""
    timestamp_str: str = ""


@dataclass(frozen=True, slots=True)
class CircuitBreakerInfo:
    """Status of a single circuit breaker."""

    name: str = ""
    state: str = "CLOSED"
    failure_count: int = 0
    success_count: int = 0
    failure_threshold: int = 5
    recovery_timeout: str = ""


@dataclass(frozen=True, slots=True)
class CheckpointInfo:
    """A single checkpoint entry."""

    checkpoint_id: str = ""
    component: str = ""
    version: str = ""
    created_at_str: str = ""
    has_metadata: bool = False


@dataclass(frozen=True, slots=True)
class BackupStatusInfo:
    """Snapshot of backup/restore status."""

    total_checkpoints: int = 0
    components_with_checkpoints: str = ""
    last_checkpoint_time: str = ""
    storage_type: str = ""
    storage_path: str = ""


@dataclass(frozen=True, slots=True)
class AuditScreenState:
    """Complete snapshot for the Audit, Logs & Recovery screen."""

    audit_summary: AuditSummaryInfo = field(default_factory=AuditSummaryInfo)
    recent_audit: tuple[AuditEntry, ...] = ()
    log_summary: LogSummaryInfo = field(default_factory=LogSummaryInfo)
    recent_logs: tuple[LogEntry, ...] = ()
    recovery_history: tuple[RecoveryHistoryEntry, ...] = ()
    circuit_breakers: tuple[CircuitBreakerInfo, ...] = ()
    checkpoints: tuple[CheckpointInfo, ...] = ()
    backup_status: BackupStatusInfo = field(default_factory=BackupStatusInfo)
    last_refresh: str = ""


# ─── Configuration & Deployment Screen ─────────────────────────


@dataclass(frozen=True, slots=True)
class ConfigurationInfo:
    """Snapshot of TITAN configuration status."""

    profile: str = ""
    sources: tuple[str, ...] = ()
    log_level: str = ""
    pipeline_interval: str = ""
    validation_status: str = ""
    blocking_errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EnvironmentInfo:
    """Snapshot of active deployment environment."""

    name: str = ""
    directories_verified: bool = False
    secrets_available: bool = False
    validation_status: str = ""


@dataclass(frozen=True, slots=True)
class DeploymentInfo:
    """Snapshot of overall deployment runtime status."""

    status: str = ""
    uptime: str = ""
    start_time: str = ""
    health_status: str = ""
    startup_duration: str = ""


@dataclass(frozen=True, slots=True)
class ServiceStatusEntry:
    """Snapshot of a single service's health/status."""

    name: str = ""
    status: str = ""
    latency_ms: str = ""
    message: str = ""


@dataclass(frozen=True, slots=True)
class VersionInfo:
    """Snapshot of TITAN version and build info."""

    version: str = ""
    build_number: str = ""
    git_commit: str = ""
    git_branch: str = ""
    python_version: str = ""


@dataclass(frozen=True, slots=True)
class BackupInfo:
    """Snapshot of backup/restore status for configuration/data."""

    last_backup_id: str = ""
    last_backup_time: str = ""
    components_backed_up: int = 0
    total_files: int = 0
    status: str = ""


@dataclass(frozen=True, slots=True)
class DeploymentHistoryEntry:
    """Snapshot of a historical deployment action."""

    timestamp_str: str = ""
    action: str = ""
    status: str = ""
    version: str = ""
    duration: str = ""


@dataclass(frozen=True, slots=True)
class ConfigurationScreenState:
    """Complete snapshot for the Configuration & Deployment screen."""

    configuration: ConfigurationInfo = field(default_factory=ConfigurationInfo)
    environment: EnvironmentInfo = field(default_factory=EnvironmentInfo)
    deployment: DeploymentInfo = field(default_factory=DeploymentInfo)
    services: tuple[ServiceStatusEntry, ...] = ()
    version: VersionInfo = field(default_factory=VersionInfo)
    backup: BackupInfo = field(default_factory=BackupInfo)
    history: tuple[DeploymentHistoryEntry, ...] = ()
    last_refresh: str = ""


# ─── Decision Journal screen models ─────────────────────────


@dataclass(frozen=True, slots=True)
class DecisionSummaryInfo:
    """Snapshot of the latest decision summary."""

    decision_id: str = "None"
    symbol: str = "None"
    decision: str = "NO_TRADE"
    trade_direction: str = "None"
    instrument_type: str = "None"
    confidence: float = 0.0
    trade_score: float = 0.0
    institutional_grade: bool = False
    timestamp_str: str = "Never"


@dataclass(frozen=True, slots=True)
class DecisionEvidenceInfo:
    """Snapshot of evidence supporting the decision."""

    source: str = "Unknown"
    category: str = "Unknown"
    signal: str = "Unknown"
    score: float = 0.0
    confidence: float = 0.0
    weight: float = 0.0
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DecisionRiskInfo:
    """Snapshot of risk assessment for the decision."""

    risk_summary: str = "No risk data available."


@dataclass(frozen=True, slots=True)
class DecisionQualificationInfo:
    """Snapshot of qualification explanation."""

    explanation_summary: str = "No explanation available."


@dataclass(frozen=True, slots=True)
class DecisionTimelineEntry:
    """Snapshot of a step in the decision timeline."""

    step: str = ""
    status: str = ""
    timestamp_str: str = ""


@dataclass(frozen=True, slots=True)
class DecisionReasonEntry:
    """Snapshot of a specific decision reason."""

    reason_type: str = ""
    description: str = ""
    severity: str = "info"


@dataclass(frozen=True, slots=True)
class DecisionJournalEntry:
    """Snapshot of a historical decision journal entry."""

    decision_id: str = ""
    symbol: str = ""
    decision: str = ""
    timestamp_str: str = ""


@dataclass(frozen=True, slots=True)
class DecisionScreenState:
    """Complete snapshot for the Decision Journal Explainability screen."""

    summary: DecisionSummaryInfo = field(default_factory=DecisionSummaryInfo)
    evidence: DecisionEvidenceInfo = field(default_factory=DecisionEvidenceInfo)
    risk: DecisionRiskInfo = field(default_factory=DecisionRiskInfo)
    qualification: DecisionQualificationInfo = field(
        default_factory=DecisionQualificationInfo
    )
    timeline: tuple[DecisionTimelineEntry, ...] = ()
    reasons: tuple[DecisionReasonEntry, ...] = ()
    history: tuple[DecisionJournalEntry, ...] = ()
    last_refresh: str = ""


# ─── Trade Journal Screen ─────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TradeJournalSummaryInfo:
    today_pnl: str = "₹0"
    open_risk: str = "₹0"
    exposure: str = "₹0"
    win_percent: str = "0.0%"
    current_drawdown: str = "0.0%"
    largest_winner: str = "₹0"
    largest_loser: str = "₹0"


@dataclass(frozen=True, slots=True)
class TradeHistoryEntry:
    trade_id: str = ""
    symbol: str = ""
    direction: str = ""
    quantity: int = 0
    entry_price: str = "₹0"
    exit_price: str = "₹0"
    net_pnl: str = "₹0"
    status: str = ""
    open_time: str = ""


@dataclass(frozen=True, slots=True)
class TradeJournalScreenState:
    """Complete snapshot for the Trade Journal screen."""

    summary: TradeJournalSummaryInfo = field(default_factory=TradeJournalSummaryInfo)
    history: tuple[TradeHistoryEntry, ...] = ()
    last_refresh: str = ""


# ─── Decision Replay screen models ────────────────────────


@dataclass(frozen=True, slots=True)
class ReplaySummaryInfo:
    """Snapshot of the selected replay decision summary."""

    decision_id: str = "None"
    symbol: str = "None"
    decision: str = "NO_TRADE"
    trade_direction: str = "None"
    instrument_type: str = "None"
    confidence: float = 0.0
    trade_score: float = 0.0
    institutional_grade: bool = False
    timestamp_str: str = "Never"


@dataclass(frozen=True, slots=True)
class ReplayEvidenceInfo:
    """Snapshot of evidence for the replayed decision."""

    source: str = "Unknown"
    category: str = "Unknown"
    signal: str = "Unknown"
    score: float = 0.0
    confidence: float = 0.0
    weight: float = 0.0
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReplayRiskInfo:
    """Snapshot of risk assessment for the replayed decision."""

    risk_summary: str = "No risk data available."


@dataclass(frozen=True, slots=True)
class ReplayQualificationInfo:
    """Snapshot of qualification explanation for the replayed decision."""

    explanation_summary: str = "No explanation available."


@dataclass(frozen=True, slots=True)
class ReplayTimelineEntry:
    """Snapshot of a step in the replayed decision timeline."""

    step: str = ""
    status: str = ""
    timestamp_str: str = ""


@dataclass(frozen=True, slots=True)
class ReplayReasonEntry:
    """Snapshot of a specific reason for the replayed decision."""

    reason_type: str = ""
    description: str = ""
    severity: str = "info"


@dataclass(frozen=True, slots=True)
class ReplayMetadataInfo:
    """Metadata about the replay context itself."""

    has_previous: bool = False
    has_next: bool = False
    previous_id: str | None = None
    next_id: str | None = None
    current_index: int = 0
    total_decisions: int = 0
    filter_active: bool = False


@dataclass(frozen=True, slots=True)
class ReplayScreenState:
    """Complete snapshot for the Decision Replay screen."""

    summary: ReplaySummaryInfo = field(default_factory=ReplaySummaryInfo)
    evidence: ReplayEvidenceInfo = field(default_factory=ReplayEvidenceInfo)
    risk: ReplayRiskInfo = field(default_factory=ReplayRiskInfo)
    qualification: ReplayQualificationInfo = field(
        default_factory=ReplayQualificationInfo
    )
    reasons: tuple[ReplayReasonEntry, ...] = ()
    timeline: tuple[ReplayTimelineEntry, ...] = ()
    metadata: ReplayMetadataInfo = field(default_factory=ReplayMetadataInfo)
    last_refresh: str = ""


@dataclass(frozen=True, slots=True)
class PortfolioScreenState:
    """Complete snapshot for the Portfolio Analytics screen."""

    snapshot: PortfolioSnapshot = field(default_factory=PortfolioSnapshot)
    exposure: ExposureAnalysis = field(default_factory=ExposureAnalysis)
    allocation: AllocationAnalysis = field(default_factory=AllocationAnalysis)
    diversification: DiversificationAnalysis = field(
        default_factory=DiversificationAnalysis
    )
    drawdown: DrawdownAnalysis = field(default_factory=DrawdownAnalysis)
    performance: PortfolioPerformance = field(default_factory=PortfolioPerformance)
    last_refresh: str = ""


# ─── Strategy Intelligence Dashboard models ──────────────────────────


@dataclass(frozen=True, slots=True)
class RegimePerformanceEntry:
    """Snapshot of a strategy's performance in a specific regime."""

    regime: str = ""
    trades: int = 0
    win_rate: str = "0.0%"
    profit_factor: str = "0.00"
    net_pnl: str = "₹0"


@dataclass(frozen=True, slots=True)
class StrategyScorecardInfo:
    """Snapshot of a strategy's overall evaluation."""

    strategy_name: str = ""
    total_trades: int = 0
    win_rate: str = "0.0%"
    profit_factor: str = "0.00"
    expectancy: str = "0.00R"
    net_pnl: str = "₹0"
    max_drawdown: str = "₹0"
    regimes: tuple[RegimePerformanceEntry, ...] = ()


@dataclass(frozen=True, slots=True)
class StrategyEvalScreenState:
    """Complete snapshot for the Strategy Intelligence screen."""

    best_strategy: str = ""
    scorecards: tuple[StrategyScorecardInfo, ...] = ()
    last_refresh: str = ""
