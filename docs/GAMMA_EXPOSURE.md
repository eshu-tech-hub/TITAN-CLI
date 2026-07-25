# Gamma Exposure (GEX) Intelligence Engine

## Purpose

The Gamma Exposure Intelligence Engine estimates institutional dealer
gamma exposure using supplied analytics — Greeks, open interest, dealer
positioning, surface intelligence, and option-chain data — without
broker imports, API calls, or Black-Scholes pricing.

It produces a unified assessment of:

- **Net Gamma Exposure** — aggregate gamma risk in the option chain.
- **Gamma Regime** — whether dealers are net long gamma (dampening),
  net short gamma (amplifying), or neutral.
- **Zero Gamma (Gamma Flip) Level** — the price level where net gamma
  exposure crosses zero, representing a critical inflection point in
  dealer hedging behaviour.
- **Call Wall / Put Wall** — strikes with the highest gamma-weighted
  open interest concentration, acting as resistance (call wall) or
  support (put wall).
- **Pinning Probability** — likelihood that price will be drawn toward
  and held near gamma levels.
- **Volatility Expansion Probability** — likelihood that gamma
  conditions will amplify or suppress realised volatility.

This engine explicitly does **not** implement Vanna, Charm, Dealer
Hedging simulation, or standalone trading signals. GEX is treated as
market-regime context only.

## Architecture

```text
+------------------+  +----------------+  +---------------------+
|DealerPositioning |  |GreeksAnalysis  |  |SurfaceIntelligence  |
|Analysis          |  |                |  |Analysis             |
+--------+---------+  +-------+--------+  +---------+-----------+
         |                    |                      |
         +--------------------+----------------------+
                              |
                              v
                 +--------------------------+
                 | GammaExposureInput       |
                 | (5 optional component    |
                 |  analysis objects)       |
                 +------------+-------------+
                              |
              +---------------+---------------+
              |                               |
              v                               v
+---------------------------+    +-------------------------+
| ZeroGammaAnalyzer         |    | GammaWallsAnalyzer      |
|                           |    |                         |
| Find gamma flip level     |    | Find call/put walls     |
| From: snapshot, greeks   |    | From: snapshot gamma/OI |
+-------------+-------------+    +------------+------------+
              |                               |
              +--------------+----------------+
                             |
                             v
                +--------------------------+
                | GammaExposureAnalyzer    |
                | (Orchestrator)           |
                |                          |
                | Combines zero gamma +    |
                | walls                    |
                | Produces evidence        |
                +--------------------------+
```

## Components

### 1. ZeroGammaAnalyzer

Identifies the price level where aggregate gamma exposure crosses zero
(the "gamma flip").

**Input signals:**

| Signal Source | How Used |
|---|---|
| GreeksAnalysis (net_gamma) | Determines overall regime sign |
| OptionChainSnapshot (per-strike gamma, OI) | Computes cumulative gamma exposure, finds zero crossing |

**Output:** `ZeroGammaLevel` with `strike` (interpolated flip level),
`distance_percent` (distance from underlying), and `confidence` (0-1).

The zero crossing is found by:
1. Sorting strikes by strike price.
2. Computing cumulative gamma exposure (call_gex - put_gex) across
   strikes.
3. Detecting a sign change in cumulative gamma.
4. Linearly interpolating between the two straddling strikes.

### 2. GammaWallsAnalyzer

Identifies strikes with the highest gamma-weighted open interest
concentration.

**Input signals:**

| Signal Source | How Used |
|---|---|
| OptionChainSnapshot (per-strike gamma, OI) | Gamma × OI per strike, ranked |

**Output:** Tuple of `(call_wall, put_wall)`, each a `GammaWall` with
`strike`, `wall_type`, `gamma_concentration` (0-1 normalised),
`open_interest`, and `confidence` (0-1).

Wall identification follows these rules:
1. Separate call-side and put-side gamma × OI products.
2. Rank strikes descending by gamma exposure.
3. Top candidate is the wall for each side.
4. Gamma concentration = top exposure ÷ total of top 5 candidates.
5. Confidence increases with concentration, OI magnitude, and
   candidate count.
6. When gamma is unavailable, falls back to raw OI ranking.

### 3. GammaExposureAnalyzer (Orchestrator)

The orchestrator combines zero-gamma and wall assessments into a
single `GammaExposureAnalysis`. It:

1. Computes net gamma exposure from GreeksAnalysis (preferred) or
   per-strike data.
2. Determines gamma regime from net gamma sign, falling back to
   dealer positioning side.
3. Runs the ZeroGammaAnalyzer and GammaWallsAnalyzer sub-analyzers.
4. Assesses pinning probability from gamma regime, zero-gamma
   proximity, and wall strength.
5. Assesses volatility expansion probability from gamma regime and
   wall weakness.
6. Generates an `Evidence` object for the Intelligence Fusion Engine.
7. Produces a structured `GammaExposureExplanation` with sections
   for regime, zero gamma, walls, pinning, volatility implications,
   and institutional interpretation.

## Data Models

### Enums

| Enum | Values | Description |
|---|---|---|
| `GammaRegime` | `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `UNKNOWN` | Net gamma exposure regime |
| `WallType` | `CALL_WALL`, `PUT_WALL`, `NONE`, `UNKNOWN` | Gamma wall classification |
| `PinningProbability` | `LOW`, `MEDIUM`, `HIGH`, `EXTREME`, `UNKNOWN` | Likelihood of price pinning |

### Key Dataclasses (all `frozen=True`, `slots=True`)

- **`GammaExposureInput`** — Container for `DealerPositioningAnalysis`,
  `GreeksAnalysis`, `OptionChainAnalysis`,
  `SurfaceIntelligenceAnalysis`, `OptionChainSnapshot`. All fields
  optional.
- **`ZeroGammaLevel`** — Gamma flip level estimate.
- **`GammaWall`** — Gamma wall with concentration and confidence.
- **`GammaExposureAnalysis`** — Combined output with `net_gamma_exposure`,
  `gamma_regime`, `zero_gamma_level`, `call_wall`, `put_wall`,
  `pinning_probability`, `volatility_expansion_probability`,
  `confidence`, `evidence`, `explanation`.
- **`GammaExposureExplanation`** — Six-section structured explanation.

## Interpretation

### Positive Gamma (Net Long Gamma)

Dealers benefit from large directional moves. Their hedging dampens
price action:

- Upward move → dealers sell into strength (hedging short gamma).
- Downward move → dealers buy into weakness (hedging short gamma).

**Effect:** Range-bound, choppy price action with mean reversion.
Pinning probability tends to be elevated.

### Negative Gamma (Net Short Gamma)

Dealers lose on large directional moves. Their hedging amplifies price
action:

- Upward move → dealers buy to hedge (chasing strength).
- Downward move → dealers sell to hedge (chasing weakness).

**Effect:** Trending, accelerating price action with momentum.
Volatility expansion probability tends to be elevated.

### Zero Gamma (Gamma Flip)

The gamma flip level represents a critical inflection point:

- **Below flip:** Gamma regime may be positive (dealers buy weakness).
- **Above flip:** Gamma regime may be negative (dealers sell strength).
- **At flip:** Dealer hedging behaviour changes polarity.

When price is near the zero-gamma level, pinning is more likely.

### Call Wall

A call wall is a strike where high call-side gamma exposure creates
resistance:

- As price approaches, dealers who are short calls delta-hedge by
  selling underlying.
- This selling pressure creates resistance, slowing or reversing the
  upward move.
- A break above the call wall can trigger rapid acceleration as
  dealers cover.

### Put Wall

A put wall is a strike where high put-side gamma exposure creates
support:

- As price approaches, dealers who are short puts delta-hedge by
  buying underlying.
- This buying pressure creates support, slowing or reversing the
  downward move.
- A break below the put wall can trigger rapid acceleration as
  dealers cover.

### Pinning

Pinning refers to the tendency of price to be drawn toward and held
near significant gamma levels (zero gamma, call/put walls). Causes:

1. **Long gamma:** Dealers hedge by selling strength and buying
   weakness, creating a spring that pulls price back.
2. **Gamma flip proximity:** When price is near the zero-gamma level,
   small moves trigger hedging that pushes price back.
3. **Wall corridor:** When both walls are close, price is trapped in
   a range.

### Volatility Expansion

Volatility expansion is more likely when:

1. **Short gamma:** Dealer hedging amplifies rather than dampens
   moves.
2. **Weak or distant walls:** No significant gamma levels exist to
   arrest price movement.
3. **Regime shift:** A gamma flip (positive→negative) can trigger
   volatility expansion as dealer behaviour changes.

## Evidence

The orchestrator produces a single `Evidence` object:

- **Source:** "Gamma Exposure"
- **Category:** `EvidenceCategory.OPTION_CHAIN`
- **Signal:** Derived from `gamma_regime` (POSITIVE → BULLISH,
  NEGATIVE → BEARISH, NEUTRAL → NEUTRAL, UNKNOWN → UNKNOWN).
- **Score:** Base score from regime (70 POSITIVE, 30 NEGATIVE, 50
  NEUTRAL) adjusted for pinning extremity.
- **Confidence:** Composite of Greeks, dealer positioning,
  zero-gamma, and wall confidences.
- **Reasons:** Human-readable summary of regime, net gamma,
  zero-gamma level, walls, and pinning.
- **Metadata:** Analyzer name, gamma regime, net gamma exposure,
  pinning probability, volatility expansion probability, component
  availability.

## Graceful Degradation

The engine degrades gracefully when inputs are missing:

- No inputs → neutral placeholder with reason.
- Partial inputs → analysis continues with reduced confidence.
- Missing Greeks → regime from dealer positioning if available.
- Missing snapshot → zero gamma and walls unavailable; regime still
  determined.

## Future Compatability

The architecture supports the following future additions without
redesign:

| Feature | Approach | Timeline |
|---|---|---|
| Vanna Exposure | New sub-analyzer + new field on `GammaExposureInput` | Future |
| Charm Exposure | New sub-analyzer + new field on `GammaExposureInput` | Future |
| Dealer Hedging Simulation | New sub-analyzer using inventory + GEX | Future |
| 0DTE Gamma | Per-expiry GEX decomposition | Future |
| Cross-expiry GEX | Term-structure-aware GEX aggregation | Future |
| Historical GEX | Time-series-aware GEX snapshots | Future |
| Intraday GEX Evolution | Trend-aware intraday GEX analyzer | Future |

## Current Implementation

### Milestone M2.2.6

- `titan/options/analytics/gex.py` — GammaExposureAnalyzer
- `titan/options/analytics/zero_gamma.py` — ZeroGammaAnalyzer
- `titan/options/analytics/gamma_walls.py` — GammaWallsAnalyzer
- `titan/options/analytics/models.py` — All GEX data models (enums,
  dataclasses)
- `tests/test_gamma_exposure.py` — 40+ tests covering all
  components

### Not Implemented (Future Milestones)

- Vanna / Charm exposure estimation
- Dealer hedging simulation
- 0DTE-specific GEX
- Cross-expiry GEX decomposition
- Historical GEX time series
- Intraday GEX evolution
