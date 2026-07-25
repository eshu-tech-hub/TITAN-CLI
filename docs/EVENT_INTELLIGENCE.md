# Event Intelligence Engine

## Overview

The Event Intelligence Engine analyses scheduled market events — economic releases and corporate actions — and produces institutional-grade context about event-driven risk, impact, and trading implications. It is a pure analysis module that consumes only supplied event data and produces evidence for the Evidence Engine and Intelligence Fusion Engine.

### Core Philosophy

> Analyse supplied event data only. Do not fetch news. Do not call economic APIs. Do not integrate news providers.

The engine evaluates four dimensions:

1. **Economic Calendar** — central bank policies, macroeconomic indicators, holidays
2. **Corporate Actions** — results, dividends, buybacks, mergers, and capital events
3. **Market Impact** — expected volatility, liquidity, gap risk, duration, affected assets
4. **Event Risk** — multi-dimensional risk classification (level, gap, volatility, liquidity)

---

## Architecture

```
EconomicEvent[] ──→ EconomicCalendarAnalyzer  (classification, importance)
CorporateEvent[] ──→ CorporateEventAnalyzer   (classification, importance)
                         │
                         ├─→ ImpactAnalyzer   (volatility, liquidity, gap, duration)
                         ├─→ EventRiskAnalyzer (risk levels, confidence)
                         │
                         └─→ EventIntelligenceAnalyzer (orchestrator)
                                  │
                                  ├─→ EventAnalysis
                                  ├─→ Evidence (EvidenceCategory.EVENT)
                                  └─→ EventExplanation (6 sections)
```

### Component Description

| Component | Responsibility |
|---|---|
| `EconomicCalendarAnalyzer` | Classify economic events by type, assign importance, sort by criticality |
| `CorporateEventAnalyzer` | Classify corporate actions by type, assign importance, sort by criticality |
| `ImpactAnalyzer` | Determine expected volatility, liquidity, gap risk, affected assets |
| `EventRiskAnalyzer` | Multi-dimensional risk classification |
| `EventIntelligenceAnalyzer` | Orchestrator — combines all sub-analyzers, generates evidence + explanation |

---

## Data Flow

1. Caller supplies `EconomicEvent[]` and/or `CorporateEvent[]`
2. `EconomicCalendarAnalyzer` re-classifies importance based on event type
3. `CorporateEventAnalyzer` re-classifies importance based on event type
4. `ImpactAnalyzer` maps importance → impact parameters (volatility, liquidity, gap, duration)
5. `EventRiskAnalyzer` maps importance + impact → risk levels (overall, gap, vol, liquidity)
6. `EventIntelligenceAnalyzer` builds `EventAnalysis` with `DecisionContext`, `Evidence`, and `EventExplanation`

---

## Data Models

### EconomicEvent

| Field | Type | Description |
|---|---|---|
| `event_type` | `EconomicEventType` | FOMC, RBI, GDP, CPI, NFP, etc. |
| `timestamp` | `datetime` | Scheduled event time |
| `importance` | `EventImportance` | LOW / MEDIUM / HIGH / CRITICAL |
| `description` | `str` | Human-readable description |
| `country` | `str` | Affected country/region |
| `previous` | `float | None` | Previous value |
| `forecast` | `float | None` | Consensus forecast |
| `actual` | `float | None` | Actual outcome (None if unreleased) |
| `affected_asset_classes` | `tuple[AssetClass]` | Asset classes likely affected |
| `affected_sectors` | `tuple[str]` | Sectors likely affected |

### CorporateEvent

| Field | Type | Description |
|---|---|---|
| `event_type` | `CorporateEventType` | Results, dividend, buyback, merger, etc. |
| `timestamp` | `datetime` | Scheduled event time |
| `company` | `str` | Company name |
| `importance` | `EventImportance` | LOW / MEDIUM / HIGH / CRITICAL |
| `description` | `str` | Human-readable description |
| `details` | `str` | Additional event-specific details |

### EventImpact

| Field | Type | Description |
|---|---|---|
| `expected_volatility` | `float` | Expected volatility level (0-1) |
| `expected_liquidity` | `float` | Expected liquidity level (0-1) |
| `expected_gap_risk` | `float` | Expected gap risk level (0-1) |
| `affected_asset_class` | `AssetClass` | Primary affected asset class |
| `affected_sector` | `str` | Primary affected sector |
| `expected_duration` | `str` | Expected impact duration description |

### EventRiskAssessment

| Field | Type | Description |
|---|---|---|
| `risk_level` | `EventRisk` | Overall risk level |
| `gap_risk` | `EventRisk` | Gap risk component |
| `volatility_risk` | `EventRisk` | Volatility risk component |
| `liquidity_risk` | `EventRisk` | Liquidity risk component |
| `confidence` | `float` | Confidence in assessment (0-1) |

### DecisionContext

| Field | Type | Description |
|---|---|---|
| `avoid_new_positions` | `bool` | Whether new positions carry elevated risk |
| `reduce_position_size` | `bool` | Whether existing positions should be reduced |
| `expect_high_volatility` | `bool` | Whether elevated volatility is expected |
| `expect_gap_open` | `bool` | Whether a gap open is likely |
| `allow_intraday_only` | `bool` | Whether only intraday trades are advisable |
| `confidence` | `float` | Confidence in the context (0-1) |

### EventAnalysis

| Field | Type | Description |
|---|---|---|
| `economic_events` | `tuple[EconomicEvent]` | Analyzed economic events |
| `corporate_events` | `tuple[CorporateEvent]` | Analyzed corporate events |
| `highest_importance` | `EventImportance` | Highest importance across all events |
| `overall_risk` | `EventRisk` | Aggregate risk assessment |
| `decision_context` | `DecisionContext | None` | Event-driven decision context |
| `confidence` | `float` | Aggregate confidence (0-1) |
| `warnings` | `tuple[str]` | Non-fatal warnings |
| `metadata` | `dict` | Producer context |
| `evidence` | `Evidence | None` | Evidence for Intelligence Fusion Engine |
| `explanation` | `EventExplanation | None` | Structured explanation |

---

## Importance Classification

### Economic Events

| Event Type | Default Importance |
|---|---|
| FOMC, RBI Policy, ECB, BOJ, NFP, Interest Rate Decision | CRITICAL |
| GDP, CPI, PPI | HIGH |
| PMI, Unemployment | MEDIUM |
| Holiday | LOW |

### Corporate Events

| Event Type | Default Importance |
|---|---|
| Quarterly Results, Merger, Acquisition, Buyback | CRITICAL |
| Guidance, Promoter Activity, Block Deal, Rights Issue | HIGH |
| Dividend, Bonus, Split | MEDIUM |

Explicitly set importance overrides the default classification.

---

## Impact Mapping

| Importance | Volatility | Liquidity | Gap Risk | Duration |
|---|---|---|---|---|
| CRITICAL | 0.85 | 0.30 | 0.80 | Multiple sessions |
| HIGH | 0.65 | 0.45 | 0.55 | Intraday to next session |
| MEDIUM | 0.35 | 0.70 | 0.25 | Intraday |
| LOW | 0.15 | 0.90 | 0.10 | Brief intraday |

---

## Decision Context Logic

| Condition | avoid_new | reduce_size | high_vol | gap_open | intraday_only |
|---|---|---|---|---|---|
| Risk is HIGH/EXTREME OR CRITICAL importance | ✓ | ✓ | ✓ | ✓ | ✓ |
| Risk is HIGH/EXTREME AND high volatility | ✓ | ✓ | ✓ | ✓ | ✓ |
| Gap risk >= 0.5 OR risk.gap_risk is HIGH/EXTREME | | | | ✓ | |
| Volatility >= 0.5 | | | ✓ | | |
| LOW importance, LOW/Very Low risk | | | | | |

---

## Evidence System

- **Category**: `EvidenceCategory.EVENT`
- **Source**: `"Event Intelligence"`
- **Signal**: `VERY_BEARISH` for EXTREME risk; `BEARISH` for HIGH risk with CRITICAL/HIGH importance; `NEUTRAL` otherwise
- **Score**: Base 50 (neutral); CRITICAL/HIGH importance → 35; +5 for high confidence, +3 for moderate
- **Confidence**: Weighted average of calendar (0.35), corporate (0.30), and risk (0.35) confidence

---

## Explanation Sections

1. **Upcoming Events** — Scheduled event types and counts
2. **Importance** — Highest importance level
3. **Market Impact** — Volatility, liquidity, gap risk, affected asset
4. **Risk Assessment** — Overall, gap, and volatility risk levels
5. **Trading Implications** — DecisionContext interpretation
6. **Overall Assessment** — Summary and institutional guidance

---

## Future Compatibility

The architecture supports these extensions without redesign:

- **News Intelligence** — Add `NewsEvent` model, `NewsAnalyzer` sub-analyzer
- **Reuters / Bloomberg** — Integrate as data providers only (no analysis changes)
- **NSE / BSE Notices** — Add `RegulatoryEventType`, new sub-analyzer
- **Economic APIs** — Connect as data providers (no analysis changes)
- **Calendar Providers** — Connect as data providers (no analysis changes)
- **Additional Risk Dimensions** — Extend `EventRiskAssessment` with new fields
- **Multi-Event Aggregation** — No changes needed; orchestrator already handles multiple events

---

## Current Implementation

- Package: `titan/events/`
- Analyzers: `EconomicCalendarAnalyzer`, `CorporateEventAnalyzer`, `ImpactAnalyzer`, `EventRiskAnalyzer`, `EventIntelligenceAnalyzer`
- Models: `EconomicEvent`, `CorporateEvent`, `EventImpact`, `EventRiskAssessment`, `DecisionContext`, `EventAnalysis`, `EventExplanation`
- Enums: `EventImportance`, `EventRisk`, `AssetClass`, `EconomicEventType`, `CorporateEventType`
- Tests: 77 tests in `tests/test_event_intelligence.py`
- Documentation: `docs/EVENT_INTELLIGENCE.md`, `docs/adr/ADR-012-Event-Intelligence.md`
- Quality: Ruff 0, Black clean, MyPy 0 new, Pytest 77/77
