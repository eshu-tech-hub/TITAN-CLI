# Trade Lifecycle

Every trade managed by TITAN transitions through a strict, linear state machine representing its lifecycle. These events are captured in the Trade Journal as an append-only timeline.

## States

1. **CREATED**: The trade entry is instantiated locally, preparing for broker submission.
2. **SUBMITTED**: The order has been routed to the broker API.
3. **ACCEPTED**: The broker acknowledged the order and it is sitting on the exchange.
4. **PARTIALLY_FILLED**: A portion of the order quantity has executed.
5. **FILLED**: The entire order quantity has executed.
6. **MODIFIED**: The order parameters (price/quantity) were updated while live.
7. **CLOSED**: The position associated with the trade is closed. PnL is finalized.
8. **ARCHIVED**: The trade is closed and marked for long-term storage, removing it from active polling.

## Event Ordering

The journal tracks `TradeLifecycleEvent` objects. Each event contains:
- `timestamp`: UTC datetime of the transition
- `status`: The new `TradeLifecycleState`
- `reason`: System reason for transition
- `broker_reference`: Linkage to the underlying broker order ID
- `notes`: Any auxiliary info

```
[10:00:00] CREATED
[10:00:01] SUBMITTED -> broker_reference="123"
[10:00:02] ACCEPTED
[10:01:00] FILLED
[11:00:00] CLOSED -> Exit triggered by trailing stop
```
