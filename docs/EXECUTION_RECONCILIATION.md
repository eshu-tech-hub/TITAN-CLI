# Execution Reconciliation

Reconciliation ensures the synchronization of disparate subsystems in the TITAN paper trading architecture.

## Validation Chains
`ExecutionReconciliationValidator` guarantees that the following states align identically:

### Order -> Fill
Every tracked broker order matches exactly the generated fills produced by the `FillEngine` and journaled by the `TradeJournal`.

### Fill -> Position
Executed fills reflect precisely in the `PositionEngine`. A fill of +10 updates the net open position by exactly +10. Zero-quantity positions are correctly garbage-collected.

### Position -> Portfolio
The `PaperPortfolio` computes available funds and margin solely based on the current outstanding positions and original cash layout, guaranteeing PnL matches net risk precisely.

### Journal -> Runtime
The journal serves as the ground truth. Restarts or disconnections recover state entirely from journal history, ensuring runtime instances immediately reflect pre-crash states.
