# Performance Analytics

The Performance Analytics subsystem reads from the Trade Journal to compute key institutional metrics for evaluating trading strategies and account health.

## Core Design Principle

The analytics subsystem is strictly *read-only*. 
`PerformanceAnalyzer -> TradeJournal` is permitted. 
`TradeJournal -> PerformanceAnalyzer` is prohibited.

This ensures metrics generation never mutates the underlying trade records.

## Supported Metrics

- **Profitability:** Gross PnL, Net PnL, Win Rate, Daily/Monthly PnL.
- **Expectancy:** Mathematical expectancy per trade, Profit Factor, Average R Multiple.
- **Risk & Drawdown:** Max Drawdown, Largest Loser, Average Loser, Consecutive Losses.
- **Segments:** Performance is automatically segmented into Overall, Longs, Shorts, and Strategy-specific metrics.

## Usage

```python
from titan.trading.performance import PerformanceAnalyzer

analyzer = PerformanceAnalyzer()
performance = analyzer.analyze(journal_entries)

print(f"Win Rate: {performance.overall.win_rate}")
print(f"Max Drawdown: {performance.max_drawdown}")
```
