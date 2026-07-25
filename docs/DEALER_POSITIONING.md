# Dealer Positioning Intelligence Engine

## Purpose

The Dealer Positioning Intelligence Engine estimates institutional
dealer positioning using supplied option analytics — Greeks, surface
intelligence, option-chain analysis, and liquidity — without broker
imports, API calls, or raw order flow.

It produces a unified assessment of:

- **Dealer inventory (gamma) side** — whether dealers are long gamma,
  short gamma, or neutral.
- **Dealer directional bias** — what dealer hedging pressure implies
  for near-term price direction.
- **Hedging pressure** — how intense dealer hedging activity is likely
  to be.
- **Institutional confidence** — the reliability of the estimate.

This engine explicitly does **not** estimate Gamma Exposure (GEX),
compute dealer hedging simulations, or access any broker API. It is a
pure orchestrator over existing option analytics.

## Architecture

```text
+------------------+  +----------------+  +-----------+  +---------------------+
|OptionChainAnalysis|  |GreeksAnalysis  |  |Liquidity  |  |SurfaceIntelligence  |
|                  |  |                |  |Analysis   |  |Analysis             |
+--------+---------+  +-------+--------+  +-----+-----+  +---------+-----------+
         |                    |                   |                  |
         +--------------------+-------------------+------------------+
                              |
                              v
                 +-------------------------+
                 | DealerPositioningInput  |
                 | (4 optional component   |
                 |  analysis objects)      |
                 +------------+------------+
                              |
              +---------------+---------------+
              |                               |
              v                               v
+-------------------------+    +-------------------------+
| DealerInventoryAnalyzer |    | DealerBiasAnalyzer      |
|                         |    |                         |
| Gamma positioning       |    | Directional bias        |
| Long/Short/Neutral      |    | Bullish/Bearish/Neutral |
| From: Greeks, Surface,  |    | From: Surface, Chain,   |
|       OI                |    |       Greeks            |
+-----------+-------------+    +------------+------------+
            |                              |
            +--------------+---------------+
                           |
                           v
              +---------------------------+
              | DealerPositioningAnalyzer |
              | (Orchestrator)            |
              |                           |
              | Combines inventory + bias |
              | Produces evidence         |
              +---------------------------+
```

## Components

### 1. DealerInventoryAnalyzer

Estimates whether dealers are net long gamma, net short gamma, or
neutral.

**Input signals:**

| Signal Source | Long Gamma Indication | Short Gamma Indication |
|---|---|---|
| Greeks (net_gamma) | Positive net gamma | Negative net gamma |
| Surface (Smile/Skew) | Bearish surface signals | Bullish surface signals |
| Option Chain (bullish/bearish OI) | OI imbalance suggests opposite | OI imbalance suggests dealer short premium |

**Output:** `DealerInventory` with `dealer_side` (LONG_GAMMA /
SHORT_GAMMA / NEUTRAL / UNKNOWN), `inventory_score` (-100 to +100),
and `confidence` (0-1).

### 2. DealerBiasAnalyzer

Estimates the directional bias implied by dealer positioning.

**Input signals:**

| Signal Source | Bullish Bias | Bearish Bias |
|---|---|---|
| Surface (Skew/Smile/Term Structure) | Put skew, bearish-smile | Call skew, bullish-smile |
| Option Chain (bullish/bearish scores) | High bullish score | High bearish score |
| Greeks (net_delta, overall_bias) | Positive net delta, bullish bias | Negative net delta, bearish bias |

**Output:** `DealerBias` with `bias_level` (BULLISH / BEARISH /
NEUTRAL / UNKNOWN), `bias_score` (-100 to +100), and `confidence`
(0-1).

### 3. DealerPositioningAnalyzer (Orchestrator)

The orchestrator combines inventory and bias assessments into a single
`DealerPositioningAnalysis`. It:

1. Runs the inventory and bias sub-analyzers.
2. Computes aggregate hedging pressure from gamma extremity,
   directional conviction, and short-gamma amplification risk.
3. Generates an `Evidence` object for the Intelligence Fusion Engine.
4. Produces a structured `DealerPositioningExplanation` with sections
   for inventory, bias, hedging, institutional interpretation, and
   risk assessment.

## Data Models

### Enums

| Enum | Values | Description |
|---|---|---|
| `DealerSide` | `LONG_GAMMA`, `SHORT_GAMMA`, `NEUTRAL`, `UNKNOWN` | Dealer gamma positioning |
| `DealerBiasLevel` | `BULLISH`, `BEARISH`, `NEUTRAL`, `UNKNOWN` | Dealer directional bias |

### Key Dataclasses (all `frozen=True`, `slots=True`)

- **`DealerPositioningInput`** — Container for `OptionChainAnalysis`,
  `GreeksAnalysis`, `LiquidityAnalysis`, `SurfaceIntelligenceAnalysis`.
  All fields optional.
- **`DealerInventory`** — Gamma positioning result.
- **`DealerBias`** — Directional bias result.
- **`DealerPositioningAnalysis`** — Combined output with `evidence`,
  `explanation`, `dealer_side`, `dealer_bias`, `hedging_pressure`,
  `confidence`.
- **`DealerPositioningExplanation`** — Five-section structured
  explanation.

## Interpretation

### Long Gamma

Dealers benefit from large directional moves. Their hedging dampens
price action:

- Upward move → dealers sell into strength (hedging short gamma).
- Downward move → dealers buy into weakness (hedging short gamma).

**Effect:** Range-bound, choppy price action with mean reversion.

### Short Gamma

Dealers lose on large directional moves. Their hedging amplifies price
action:

- Upward move → dealers buy to hedge (chasing strength).
- Downward move → dealers sell to hedge (chasing weakness).

**Effect:** Trending, accelerating price action with momentum.

### Bullish Bias

Dealer hedging flows are expected to provide support on pullbacks.
Common when:

- Put skew is steep (dealers are short puts, hedge by buying).
- Call OI dominates (dealers are short calls, hedge by selling on
  rallies, but net pressure is up).

### Bearish Bias

Dealer hedging flows are expected to create resistance on rallies.
Common when:

- Call skew is steep (dealers are short calls, hedge by selling into
  strength).
- Put OI dominates (dealers are short puts, hedge by buying on
  weakness, but net pressure is down).

### Hedging Pressure

A composite metric (0-1) combining:

1. Extremity of gamma positioning (how far from neutral).
2. Directional conviction (how strong the bias signal).
3. Short gamma amplification risk (short gamma adds 0.2 to the
   aggregate).

## Evidence

The orchestrator produces a single `Evidence` object:

- **Source:** "Dealer Positioning"
- **Category:** `EvidenceCategory.OPTION_CHAIN`
- **Signal:** Derived from `dealer_bias` (BULLISH → BULLISH, BEARISH →
  BEARISH, NEUTRAL → NEUTRAL, UNKNOWN → UNKNOWN).
- **Score:** Confidence-weighted combination of inventory and bias
  scores, mapped to 0-100.
- **Confidence:** Composite of inventory and bias confidences.
- **Reasons:** Human-readable summary of gamma side, bias, hedging
  pressure, and key sub-analyst findings.
- **Metadata:** Analyzer name, dealer side, bias, hedging pressure,
  component confidences.

## Warning Propagation

Warnings from sub-analyzers are tagged with their source class name
and propagated to the orchestrator output.

Example: `[DealerInventoryAnalyzer] Greeks analysis not available for
inventory estimate.`

## Graceful Degradation

The engine degrades gracefully when inputs are missing:

- No inputs → neutral placeholder with `reason: "No dealer positioning
  inputs provided."`
- Partial inputs → analysis continues with reduced confidence.
- Missing component → warning appended, confidence reduced.

## Future Compatibility

The architecture supports the following future additions without
redesign:

- **Gamma Exposure (GEX)** — Add as a new input field on
  `DealerPositioningInput`.
- **Zero Gamma / Zero DR** — New sub-analyzer reading GEX data.
- **Vanna / Charm / Speed** — Extend inventory signal extraction.
- **Dealer Hedging Simulation** — New sub-analyzer using inventory and
  bias outputs.
- **Intraday Position Changes** — Supply time-series of analysis
  snapshots to a trend-aware analyzer.
