# Portfolio Analytics

## Overview
The Portfolio Analytics subsystem (introduced in M8.3.4) provides a read-only, broker-independent view of institutional portfolio health. It consumes outputs from the `TradeJournal` and `ExistingPortfolio` objects.

## Core Models
- `PortfolioSnapshot`
- `ExposureAnalysis`
- `AllocationAnalysis`
- `DiversificationAnalysis`
- `DrawdownAnalysis`
- `PortfolioPerformance`

## TUI Dashboard
The `PortfolioDashboardScreen` provides 8 real-time widgets updating every second to display metrics. It integrates into the Shell router.

## Export
Exports are supported in both `CSV` and `JSON` via `PortfolioAnalytics.export_csv()` and `export_json()`.
