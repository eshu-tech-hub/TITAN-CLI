# Trade Journal

The Trade Journal is the institutional system of record for all executed trades within TITAN. 

## Purpose

Unlike the Decision Journal, which records *why* TITAN made a decision (even if that decision was to reject a trade), the Trade Journal tracks exactly what happened *after* a trade was submitted to the market. It maintains a strictly append-only history of trades and their lifecycle transitions.

## Architecture

The Trade Journal consists of:

- `TradeJournal`: The orchestrator that handles recording trades and appending lifecycle events.
- `TradeRepository`: The in-memory persistent store containing the canonical `TradeJournalEntry` objects.

## Usage

Trades are initialized when a pipeline execution submits an order.

```python
engine.trade_journal.initialize_trade(entry)
engine.trade_journal.record_transition(
    trade_id, 
    TradeLifecycleState.SUBMITTED,
    broker_reference="ORD123"
)
```

## Data Exports

The journal can be exported fully to CSV or JSON formats for offline compliance or deeper data science analysis. All fields including tags, strategy, fees, slippage, and hold time are tracked.
