
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                # SQLite Persistence Hook
                try:
                    from titan.storage.trade_persistence import trade_store
                    updated_entry = self.trade_journal.get_trade(entry.trade_id)
                    if updated_entry:
                        trade_store.save(updated_entry)
                except Exception as e:
                    from titan.core.logger import logger
                    logger.error(f"Failed to persist trade: {e}")"""

replacement = """                # SQLite Persistence Hook
                try:
                    from titan.storage.trade_persistence import trade_store
                    updated_entry = self.trade_journal.get_trade(entry.trade_id)
                    if updated_entry:
                        trade_store.save(updated_entry)
                except Exception as e:
                    from titan.core.logger import logger
                    logger.error(f"Failed to persist trade: {e}")
                    
                # Publish Telegram alert hook
                from titan.runtime.models import RuntimeEventType
                entry_price = getattr(entry, "execution_price", None) or getattr(entry, "target_entry", 0.0)
                self.event_bus.publish_type(
                    RuntimeEventType.TRADE_EXECUTED,
                    "runtime",
                    data={
                        "symbol": entry.symbol,
                        "action": report.decision_action.value if report.decision_action else "UNKNOWN",
                        "price": entry_price,
                        "quantity": entry.quantity,
                        "trade_id": entry.trade_id
                    }
                )"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
