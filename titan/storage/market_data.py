from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import duckdb
from loguru import logger

from titan.market.models import Candle


class MarketDataStore:
    """High-performance Market Data Lake backed by DuckDB.
    
    Caches historical OHLCV data to eliminate external network latency.
    """

    def __init__(self, db_path: str = "data/market_data.duckdb"):
        self.db_path = db_path
        
        # Ensure data directory exists if not using memory
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
        self._conn = duckdb.connect(self.db_path)
        self._init_db()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _init_db(self) -> None:
        """Initialize the DuckDB database schema."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_candles (
                symbol VARCHAR NOT NULL,
                interval VARCHAR NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                open DOUBLE NOT NULL,
                high DOUBLE NOT NULL,
                low DOUBLE NOT NULL,
                close DOUBLE NOT NULL,
                volume DOUBLE NOT NULL,
                PRIMARY KEY (symbol, interval, timestamp)
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_candles_lookup 
            ON ohlcv_candles (symbol, interval, timestamp)
        """)

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get the database connection."""
        return self._conn

    def save_candles(self, symbol: str, interval: str, candles: Sequence[Candle]) -> None:
        """Save a list of candles to the store using bulk insertion."""
        if not candles:
            return

        # Prepare records for insertion
        records = [
            (
                symbol,
                interval,
                c.timestamp.astimezone(UTC) if c.timestamp.tzinfo else c.timestamp.replace(tzinfo=UTC),
                c.open,
                c.high,
                c.low,
                c.close,
                float(c.volume),
            )
            for c in candles
        ]

        try:
            conn = self.get_connection()
            conn.executemany("""
                INSERT OR REPLACE INTO ohlcv_candles 
                (symbol, interval, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
            logger.debug(f"Saved {len(records)} candles for {symbol} ({interval}) to DuckDB.")
        except Exception as e:
            logger.error(f"Failed to save candles for {symbol}: {e}")
            raise

    def load_candles(self, symbol: str, interval: str, start: datetime | None = None, end: datetime | None = None) -> list[Candle]:
        """Load candles from the store for a given symbol and interval."""
        query = "SELECT timestamp, open, high, low, close, volume FROM ohlcv_candles WHERE symbol = ? AND interval = ?"
        params: list[str | datetime] = [symbol, interval]

        if start:
            query += " AND timestamp >= ?"
            params.append(start.astimezone(UTC) if start.tzinfo else start.replace(tzinfo=UTC))
            
        if end:
            query += " AND timestamp <= ?"
            params.append(end.astimezone(UTC) if end.tzinfo else end.replace(tzinfo=UTC))
            
        query += " ORDER BY timestamp ASC"

        try:
            conn = self.get_connection()
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            return [
                Candle(
                    timestamp=row[0],
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=int(row[5]),
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to load candles for {symbol}: {e}")
            raise
