# Trade Pipeline Integration Engine

## Overview

The Trade Pipeline is the central conductor that orchestrates the complete TITAN workflow.

It coordinates all previously completed modules — market intelligence, option intelligence,
volatility intelligence, dealer intelligence, news/events, evidence fusion, trade qualification,
risk intelligence, decision engine, portfolio intelligence, and execution orchestration.

It contains **no market analysis, no trading logic, and no broker-specific logic**.

It only orchestrates the flow.

## Architecture

```
Market Data
    │
    ▼
TradePipeline.run()
    │
    ├── PREPARE        ─── Validate inputs, initialise context
    ├── MARKET         ─── MarketStructureAnalyzer, VWAPAnalyzer, VolumeAnalyzer,
    │                       MarketRegimeAnalyzer
    ├── OPTIONS        ─── OptionChainAnalyzer, GreeksAnalyzer, LiquidityAnalyzer
    ├── VOLATILITY     ─── VolatilityAnalyzer
    ├── DEALER         ─── DealerPositioningAnalyzer, GammaExposureAnalyzer,
    │                       CharmExposureAnalyzer, VannaExposureAnalyzer
    ├── NEWS           ─── NewsIntelligenceAnalyzer
    ├── EVENTS         ─── EventIntelligenceAnalyzer
    ├── FUSION         ─── FusionEngine (all evidence → IntelligenceFusion)
    ├── QUALIFICATION  ─── TradeQualificationEngine
    ├── RISK           ─── RiskEngine
    ├── DECISION       ─── DecisionEngine
    ├── PORTFOLIO      ─── PortfolioEngine
    ├── EXECUTION      ─── ExecutionOrchestrator
    ├── OMS            ─── Order state reporting
    ├── BROKER         ─── Broker response reporting
    │
    ▼
PipelineReport
```

## Key Components

### `TradePipeline`

The main engine. Constructed with all intelligence engines injected as dependencies:

```python
pipeline = TradePipeline(
    _structure_analyzer=MarketStructureAnalyzer(),
    _vwap_analyzer=VWAPAnalyzer(),
    _volume_analyzer=VolumeAnalyzer(),
    _regime_analyzer=MarketRegimeAnalyzer(),
    _option_chain_analyzer=OptionChainAnalyzer(),
    _greeks_analyzer=GreeksAnalyzer(),
    _liquidity_analyzer=LiquidityAnalyzer(),
    _volatility_analyzer=VolatilityAnalyzer(),
    _dealer_analyzer=DealerPositioningAnalyzer(),
    _gamma_analyzer=GammaExposureAnalyzer(),
    _charm_analyzer=CharmExposureAnalyzer(),
    _vanna_analyzer=VannaExposureAnalyzer(),
    _news_analyzer=NewsIntelligenceAnalyzer(),
    _event_analyzer=EventIntelligenceAnalyzer(),
    _fusion_engine=FusionEngine(),
    _qualification_engine=TradeQualificationEngine(),
    _risk_engine=RiskEngine(),
    _decision_engine=DecisionEngine(),
    _portfolio_engine=PortfolioEngine(),
    _orchestrator=None,  # optional — requires explicit OMS + Broker
    _hooks=PipelineHooks(),
)
```

### `PipelineContext`

Mutable context that accumulates state as pipeline stages execute. Stores outputs
from every intelligence engine for downstream stages.

### `PipelineReport`

Immutable report generated after pipeline execution. Includes:
- Stage timings (per-stage start/end/duration/success/error)
- Evidence count
- Decision action
- Order statistics (submitted, accepted, rejected)
- Broker order IDs
- Warnings and errors

### `PipelineHooks`

Lifecycle hooks for monitoring, logging, and dashboard updates:

```python
hooks = PipelineHooks(
    before_stage=lambda stage, ctx: log.info(f"Starting {stage.value}"),
    after_stage=lambda stage, ctx, result, duration: metrics.record(stage, duration),
    on_error=lambda stage, ctx, error: alert(f"Stage {stage.value} failed: {error}"),
    on_complete=lambda ctx, report: dashboard.update(report),
)
```

## Usage

```python
from titan.brokers.models import Exchange
from titan.market.models import Candle
from titan.market.series import MarketDataSeries
from titan.pipeline import TradePipeline

pipeline = TradePipeline()

candles = [Candle(timestamp=..., open=100, high=105, low=99, close=103, volume=10000)]
market_data = MarketDataSeries(candles=candles)

portfolio = ExistingPortfolio(
    positions=(),
    total_capital=1_000_000.0,
    cash_reserve=100_000.0,
)

report = pipeline.run(
    symbol="NIFTY",
    exchange=Exchange.NSE,
    market_data=market_data,
    portfolio=portfolio,
)

print(f"Status: {report.status.value}")
print(f"Decision: {report.decision_action}")
print(f"Orders submitted: {report.orders_submitted}")
```

## Error Handling

- **Recoverable errors** — stage failures where retry may succeed
  (e.g., market intelligence, options analysis, execution)
- **Fatal errors** — stage failures where the pipeline cannot continue
  (e.g., trade qualification, risk analysis, decision engine)
- **Validation errors** — raised before execution begins for invalid inputs
- **Aborted** — pipeline stopped by user or hook callback

## Stages

| Stage          | Engine(s) Called                                      | Optional? | Fatal on Error |
|----------------|-------------------------------------------------------|-----------|----------------|
| PREPARE        | — (input validation)                                  | No        | Yes            |
| MARKET         | MarketStructureAnalyzer, VWAPAnalyzer, VolumeAnalyzer, MarketRegimeAnalyzer | Yes | No |
| OPTIONS        | OptionChainAnalyzer, GreeksAnalyzer, LiquidityAnalyzer | Yes       | No             |
| VOLATILITY     | VolatilityAnalyzer                                    | Yes       | No             |
| DEALER         | DealerPositioningAnalyzer, GammaExposureAnalyzer, CharmExposureAnalyzer, VannaExposureAnalyzer | Yes | No |
| NEWS           | NewsIntelligenceAnalyzer                              | Yes       | No             |
| EVENTS         | EventIntelligenceAnalyzer                             | Yes       | No             |
| FUSION         | FusionEngine                                          | Yes       | No             |
| QUALIFICATION  | TradeQualificationEngine                              | No        | Yes            |
| RISK           | RiskEngine                                            | No        | Yes            |
| DECISION       | DecisionEngine                                        | No        | Yes            |
| PORTFOLIO      | PortfolioEngine                                       | Yes       | No             |
| EXECUTION      | ExecutionOrchestrator                                  | Yes       | No             |
| OMS            | (reporting only)                                      | Yes       | No             |
| BROKER         | (reporting only)                                      | Yes       | No             |

## Future Compatibility

The pipeline architecture supports without redesign:
- Paper trading (inject mock broker)
- Backtesting (inject historical data provider)
- Live trading (inject live data + real broker)
- Batch execution (run multiple pipeline instances)
- Portfolio rebalancing (extend PREPARE stage)
- Scheduler integration (trigger via hooks)
- Cloud workers (pipeline is stateless — context is serializable)
- Distributed execution (run stages across workers via hooks)
