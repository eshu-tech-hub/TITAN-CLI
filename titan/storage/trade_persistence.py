import json
import sqlite3
from pathlib import Path
from typing import Any


class TradePersistence:
    """Lightweight SQLite-backed trade store for persistence across restarts."""

    def __init__(self, db_path: str = "data/trades.db"):
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                decision_id TEXT,
                runtime_session_id TEXT,
                symbol TEXT,
                exchange TEXT,
                direction TEXT,
                quantity INTEGER,
                entry_price REAL,
                exit_price REAL,
                gross_pnl REAL,
                net_pnl REAL,
                fees REAL,
                slippage REAL,
                strategy TEXT,
                tags TEXT,
                decision_status TEXT,
                execution_status TEXT,
                open_time TEXT,
                close_time TEXT,
                lifecycle_events TEXT
            )
        """)
        self._conn.commit()

    def save(self, entry: Any) -> None:
        """Upsert a TradeJournalEntry."""
        cursor = self._conn.cursor()
        
        tags = json.dumps(entry.tags) if getattr(entry, "tags", None) else "[]"
        
        events = []
        if getattr(entry, "lifecycle_events", None):
            for e in entry.lifecycle_events:
                events.append({
                    "event_id": e.event_id,
                    "timestamp": e.timestamp.isoformat() if hasattr(e.timestamp, "isoformat") else str(e.timestamp),
                    "status_from": e.status_from.value if hasattr(e.status_from, "value") else str(e.status_from),
                    "status_to": e.status_to.value if hasattr(e.status_to, "value") else str(e.status_to),
                    "reason": e.reason,
                    "broker_reference": e.broker_reference
                })
        lifecycle_events = json.dumps(events)
        
        cursor.execute("""
            INSERT INTO trades (
                trade_id, decision_id, runtime_session_id, symbol, exchange,
                direction, quantity, entry_price, exit_price, gross_pnl,
                net_pnl, fees, slippage, strategy, tags,
                decision_status, execution_status, open_time, close_time, lifecycle_events
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trade_id) DO UPDATE SET
                decision_status=excluded.decision_status,
                execution_status=excluded.execution_status,
                exit_price=excluded.exit_price,
                gross_pnl=excluded.gross_pnl,
                net_pnl=excluded.net_pnl,
                fees=excluded.fees,
                slippage=excluded.slippage,
                close_time=excluded.close_time,
                lifecycle_events=excluded.lifecycle_events
        """, (
            entry.trade_id,
            entry.decision_id,
            entry.runtime_session_id,
            entry.symbol,
            entry.exchange,
            entry.direction,
            entry.quantity,
            entry.entry_price,
            entry.exit_price,
            entry.gross_pnl,
            entry.net_pnl,
            entry.fees,
            entry.slippage,
            entry.strategy,
            tags,
            entry.decision_status,
            entry.execution_status.value if hasattr(entry.execution_status, "value") else str(entry.execution_status),
            entry.open_time.isoformat() if entry.open_time else None,
            entry.close_time.isoformat() if entry.close_time else None,
            lifecycle_events
        ))
        self._conn.commit()

    def load_all(self) -> list[dict[str, Any]]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM trades")
        
        columns = [description[0] for description in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
            
        return results

    def close(self) -> None:
        self._conn.close()

trade_store = TradePersistence()
