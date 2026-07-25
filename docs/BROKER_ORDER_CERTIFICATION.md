# Broker Order Lifecycle Certification

TITAN mandates strict deterministic behavior for order state transitions.

## Order Transitions Validated
The framework validates the exact sequence:
`NEW -> VALIDATED -> SUBMITTED -> ACCEPTED -> PARTIALLY_FILLED -> FILLED`

It also rigorously tests alternative paths:
- `MODIFIED`
- `CANCELLED`
- `REJECTED`

## Principles
1. **Idempotency**: Duplicate requests must not result in duplicate open orders.
2. **Invalid Transitions**: Transitions such as `FILLED` to `NEW` must raise appropriate internal errors.
3. **Rejections**: Exchange rejections must bubble up to the RuntimeSupervisor seamlessly without unhandled exceptions crashing the event loop.
