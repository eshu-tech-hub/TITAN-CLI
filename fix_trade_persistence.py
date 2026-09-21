
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                self.trade_journal.record_transition(
                    trade_id=entry.trade_id,
                    status=TradeLifecycleState.SUBMITTED,
                    reason="Pipeline execution",
                    broker_reference=broker_id,
                )"""

replacement = """                self.trade_journal.record_transition(
                    trade_id=entry.trade_id,
                    status=TradeLifecycleState.SUBMITTED,
                    reason="Pipeline execution",
                    broker_reference=broker_id,
                )
                
                # SQLite Persistence Hook
                try:
                    from titan.storage.trade_persistence import trade_store
                    updated_entry = self.trade_journal.get_trade(entry.trade_id)
                    if updated_entry:
                        trade_store.save(updated_entry)
                except Exception as e:
                    logger.error(f"Failed to persist trade {entry.trade_id} to SQLite: {e}")"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
