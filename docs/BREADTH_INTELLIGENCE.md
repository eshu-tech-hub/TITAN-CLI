# Breadth Intelligence Engine

## Overview

The Breadth Intelligence Engine analyses the internal health of the market by evaluating whether market participation confirms or contradicts observed price action. It is a pure analysis module that consumes only `MarketBreadthSnapshot` and produces institutional-grade breadth context for the Evidence Engine and Intelligence Fusion Engine.

### Core Philosophy

> Analyse supplied breadth data only. Do not fetch exchange data. Do not calculate McClellan, TRIN, Tick Index, or New High/New Low statistics. Do not estimate breadth from a single symbol.

The engine evaluates four dimensions of breadth:

1. **Advance/Decline Ratio** — ratio of advancing to declining symbols
2. **Sector Breadth** — sector-level leadership and rotation
3. **Market Participation** — quality of participation and breadth-price divergence
4. **Market Health** — qualitative assessment of internal market condition

---

## Architecture

```
MarketBreadthSnapshot
       │
       ├─→ AdvanceDeclineAnalyzer        (A/D ratio, breadth strength)
       ├─→ SectorBreadthAnalyzer         (sector leadership, rotation)
       ├─→ MarketParticipationAnalyzer   (participation ratio, divergence)
       │
       └─→ BreadthAnalyzer (orchestrator)
                │
                ├─→ BreadthAnalysis
                ├─→ Evidence (MARKET_BREADTH)
                └─→ BreadthExplanation
```

### Analyzers

| Component | File | Responsibility |
|-----------|------|---------------|
| `BreadthAnalyzer` | `breadth.py` | Orchestrator — combines sub-analyzers, generates evidence + explanation |
| `AdvanceDeclineAnalyzer` | `advance_decline.py` | A/D ratio, advance/decline percentage, breadth strength classification |
| `SectorBreadthAnalyzer` | `sector_breadth.py` | Sector advancing/declining count, leadership, rotation detection |
| `MarketParticipationAnalyzer` | `market_participation.py` | Participation ratio, internal strength/weakness, divergence detection |

---

## Input Models

### MarketBreadthSnapshot

Broker-independent market breadth data container.

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `datetime \| None` | Observation time |
| `index_name` | `str` | Market index name (e.g. "NIFTY 50") |
| `advances` | `int` | Total advancing symbols |
| `declines` | `int` | Total declining symbols |
| `unchanged` | `int` | Total unchanged symbols |
| `total_symbols` | `int` | Total symbols tracked |
| `sector_summaries` | `tuple[SectorBreadthSnapshot, ...]` | Per-sector breadth data |
| `metadata` | `Mapping[str, Any]` | Additional context |

### SectorBreadthSnapshot

Per-sector breadth data.

| Field | Type | Description |
|-------|------|-------------|
| `sector_name` | `str` | Sector name |
| `advances` | `int` | Advancing symbols in the sector |
| `declines` | `int` | Declining symbols in the sector |
| `unchanged` | `int` | Unchanged symbols in the sector |
| `weight` | `float` | Sector weight in the composite index (0–1) |
| `metadata` | `Mapping[str, Any]` | Additional context |

---

## Data Models

### Enums

| Enum | Values |
|------|--------|
| `BreadthBias` | BULLISH, BEARISH, NEUTRAL, UNKNOWN |
| `BreadthStrength` | VERY_WEAK, WEAK, NEUTRAL, STRONG, VERY_STRONG |

### Core Dataclasses

All dataclasses are frozen with slots for immutability and performance.

| Class | Key Fields |
|-------|-----------|
| `AdvanceDecline` | ad_ratio, advance_percentage, decline_percentage, advance_dominance, decline_dominance, breadth_strength, confidence |
| `SectorBreadth` | advancing_sectors, declining_sectors, leading_sectors, lagging_sectors, rotation_detected, concentration_risk, confidence |
| `MarketParticipation` | participation_ratio, internal_strength, internal_weakness, divergence_detected, confidence |
| `BreadthExplanation` | overall_breadth, advance_decline, participation, sector_leadership, market_health, institutional_interpretation |
| `BreadthAnalysis` | advance_decline_ratio, advance_percentage, participation_ratio, breadth_strength, breadth_bias, leading_sectors, lagging_sectors, divergence_detected, market_health, advance_decline, sector_breadth, market_participation, confidence, warnings, metadata, evidence, explanation |

All classes provide a `neutral_placeholder()` classmethod for graceful degradation on insufficient data.

---

## Advance / Decline Analysis

### A/D Ratio

```
ad_ratio = advances / declines
```

When `declines == 0`, the ratio is set to `advances` (or `1.0` if both are zero).

### Breadth Strength Classification

| A/D Ratio | BreadthStrength | Interpretation |
|-----------|----------------|----------------|
| ≥ 3.0 | VERY_STRONG | Broad-based buying |
| ≥ 1.5 | STRONG | Healthy advance dominance |
| 0.67–1.5 | NEUTRAL | Balanced market |
| ≤ 0.67 | WEAK | Decline pressure |
| ≤ 0.33 | VERY_WEAK | Broad-based selling |

### Dominance

- **Advance dominance**: `advance_pct ≥ 2 × decline_pct`
- **Decline dominance**: `decline_pct ≥ 2 × advance_pct`

---

## Sector Breadth Analysis

### Sector Classification

Sectors are classified based on net breadth (`advances - declines`):
- **Advancing**: net breadth > 0
- **Declining**: net breadth < 0
- **Neutral**: net breadth = 0

### Leadership

The top 3 and bottom 3 sectors by net breadth are reported as leading and lagging sectors respectively.

### Rotation Detection

Rotation is detected when both advancing and declining sectors are present, indicating capital is rotating between sectors rather than a uniform market move.

### Concentration Risk

Concentration risk is flagged when any single sector has weight ≥ 0.50 in the composite index.

---

## Market Participation Analysis

### Participation Ratio

```
participation_ratio = (advances + declines) / total_symbols
```

### Internal Strength / Weakness

| Condition | Assessment |
|-----------|-----------|
| `participation_ratio ≥ 0.80` AND `ad_ratio ≥ 1.5` | Internal strength |
| `participation_ratio < 0.50` OR `ad_ratio ≤ 0.67` | Internal weakness |

### Breadth Divergence

Divergence is detected when:

- **Narrow participation**: `participation_ratio < 0.80` AND `ad_ratio > 1.5` (price up on narrow participation)
- **Skewed breadth**: `participation_ratio ≥ 0.80` AND (`ad_ratio ≤ 0.5` OR `ad_ratio ≥ 3.0`)

---

## Market Health

The orchestrator produces a qualitative `market_health` label:

| Condition | Label |
|-----------|-------|
| Very strong/strong breadth + internal strength | `"healthy"` |
| Very weak/weak breadth + internal weakness | `"unhealthy"` |
| Divergence detected | `"divergent"` |
| Otherwise | `"neutral"` |

---

## Bias Determination

| Condition | BreadthBias |
|-----------|-------------|
| Very strong/strong breadth + internal strength | BULLISH |
| Very weak/weak breadth + internal weakness | BEARISH |
| Advance dominance, no divergence | BULLISH |
| Decline dominance, no divergence | BEARISH |
| Otherwise | NEUTRAL |

---

## Evidence Generation

Each `BreadthAnalysis` produces a single `Evidence` item:

| Field | Value |
|-------|-------|
| Source | `"Breadth"` |
| Category | `EvidenceCategory.MARKET_BREADTH` |
| Signal | Mapped from `BreadthBias` |
| Score | Base 65 (bullish) / 35 (bearish) / 50 (neutral), -5 for divergence, +5 for confidence≥0.7, +3 for confidence≥0.5 |
| Confidence | Weighted average of sub-analyzers + sample factor |
| Reasons | A/D ratio, breadth strength, bias, divergence status |

---

## Confidence Calculation

```
confidence = (ad.confidence × 0.40 +
              sector.confidence × 0.30 +
              participation.confidence × 0.30 +
              sample_factor × 0.20) / sum(weights)
```

Sample factor = `min(1.0, total_symbols / 50)`.

---

## Testing

Tests cover:

- Healthy, weak, and neutral breadth scenarios
- Advance dominance and decline dominance
- Sector rotation and sector concentration
- Breadth divergence (narrow participation and skewed breadth)
- Empty snapshot and missing sector data
- Single sector and extreme A/D ratio edge cases
- Evidence generation and signal mapping
- Explanation generation and section content
- Frozen dataclass validation (immutability, slots)
- Neutral placeholder construction
- Internal strength, weakness, and divergence detection
- Confidence bounds

Run with:

```bash
pytest tests/test_breadth_intelligence.py -v
```

---

## Future Roadmap

The architecture supports these extensions without redesign:

| Feature | Integration Point |
|---------|------------------|
| New High / New Low | New input fields in `MarketBreadthSnapshot` |
| Percent Above MA | New sub-analyzer, same `MarketBreadthSnapshot` input |
| McClellan Oscillator | New sub-analyzer, daily A/D data |
| McClellan Summation Index | New sub-analyzer, daily A/D data |
| TRIN (Arms Index) | New sub-analyzer, advancing/declining volume data |
| Tick Index | New sub-analyzer, tick-level data |
| Cross-index Breadth | Extended `MarketBreadthSnapshot` with multi-index support |
| Multi-exchange Breadth | Extended input model with exchange field |

---

## Dependencies

- `titan/market/intelligence/models.py` — `MarketBreadthSnapshot`, `SectorBreadthSnapshot`, breadth dataclasses
- `titan/core/evidence/` — `Evidence`, `EvidenceCategory`, `EvidenceSignal`
- **No broker imports**
- **No API calls**
