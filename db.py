"""
INSTINTO - Módulo de Memória de Aço (SQLite WAL + aiosqlite)
================================================================
Princípios:
1. Append-only: Tabela `events` é imutável. Nenhum UPDATE/DELETE jamais.
2. Concorrência real: `aiosqlite` com modo WAL para leituras sem bloqueio.
3. Fonte da verdade: Tabela `positions` e `nav_state` são projetadas para
   reconciliação com a Exchange (nunca confiamos apenas na nossa memória).
4. Resiliência: Conexões com timeout, retry e pool de escrita serializado.
"""

import aiosqlite
import asyncio
import json
import time
import os
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

DB_PATH = "data/instinto.db"

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    source TEXT NOT NULL,
    type TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_type_ts ON events(type, ts);

CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    side TEXT NOT NULL,
    amount REAL NOT NULL,
    entry_price REAL NOT NULL,
    current_price REAL NOT NULL,
    updated_ts REAL NOT NULL,
    exchange_ts REAL
);

CREATE TABLE IF NOT EXISTS nav_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    total_equity REAL NOT NULL,
    available_balance REAL NOT NULL,
    used_margin REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    last_nav_sync_ts REAL NOT NULL,
    last_price_feed_ts REAL NOT NULL
);

INSERT OR IGNORE INTO nav_state (id, total_equity, available_balance, used_margin, unrealized_pnl, last_nav_sync_ts, last_price_feed_ts)
VALUES (1, 0, 0, 0, 0, 0, 0);

CREATE TABLE IF NOT EXISTS command_locks (
    command TEXT PRIMARY KEY,
    locked_until REAL NOT NULL
);
"""

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._write_lock = asyncio.Lock()
        self._conn: Optional[aiosqlite.Connection] = None
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()
        self._initialized = True

    async def close(self) -> None:
        if self._conn:
            await self._conn.commit()
            await self._conn.close()
            self._conn = None
            self._initialized = False

    async def append_event(self, source: str, event_type: str, payload: Dict[str, Any]) -> int:
        if not self._initialized:
            raise RuntimeError("Database não inicializado. Chame initialize() primeiro.")
        async with self._write_lock:
            ts = time.time()
            payload_json = json.dumps(payload, ensure_ascii=False, default=str)
            cursor = await self._conn.execute(
                "INSERT INTO events (ts, source, type, payload) VALUES (?, ?, ?, ?)",
                (ts, source, event_type, payload_json)
            )
            await self._conn.commit()
            return cursor.lastrowid

    async def upsert_position(
        self,
        symbol: str,
        side: str,
        amount: float,
        entry_price: float,
        current_price: float,
        exchange_ts: Optional[float] = None
    ) -> None:
        async with self._write_lock:
            now = time.time()
            await self._conn.execute(
                """
                INSERT INTO positions (symbol, side, amount, entry_price, current_price, updated_ts, exchange_ts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    side=excluded.side,
                    amount=excluded.amount,
                    entry_price=excluded.entry_price,
                    current_price=excluded.current_price,
                    updated_ts=excluded.updated_ts,
                    exchange_ts=excluded.exchange_ts
                """,
                (symbol, side, amount, entry_price, current_price, now, exchange_ts)
            )
            await self._conn.commit()

    async def remove_position(self, symbol: str) -> None:
        async with self._write_lock:
            await self._conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
            await self._conn.commit()

    async def update_nav_state(
        self,
        total_equity: float,
        available_balance: float,
        used_margin: float,
        unrealized_pnl: float
    ) -> None:
        async with self._write_lock:
            now = time.time()
            await self._conn.execute(
                """
                UPDATE nav_state SET
                    total_equity = ?,
                    available_balance = ?,
                    used_margin = ?,
                    unrealized_pnl = ?,
                    last_nav_sync_ts = ?
                WHERE id = 1
                """,
                (total_equity, available_balance, used_margin, unrealized_pnl, now)
            )
            await self._conn.commit()

    async def update_last_price_feed_ts(self) -> None:
        async with self._write_lock:
            now = time.time()
            await self._conn.execute(
                "UPDATE nav_state SET last_price_feed_ts = ? WHERE id = 1",
                (now,)
            )
            await self._conn.commit()

    async def try_acquire_command_lock(self, command: str, ttl_seconds: float = 5.0) -> bool:
        async with self._write_lock:
            now = time.time()
            await self._conn.execute(
                "DELETE FROM command_locks WHERE locked_until < ?", (now,)
            )
            try:
                await self._conn.execute(
                    "INSERT INTO command_locks (command, locked_until) VALUES (?, ?)",
                    (command, now + ttl_seconds)
                )
                await self._conn.commit()
                return True
            except aiosqlite.IntegrityError:
                await self._conn.rollback()
                return False

    async def get_positions(self) -> List[Dict[str, Any]]:
        if not self._conn:
            return []
        cursor = await self._conn.execute("SELECT * FROM positions")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        cursor = await self._conn.execute(
            "SELECT * FROM positions WHERE symbol = ?", (symbol,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_nav_state(self) -> Optional[Dict[str, Any]]:
        cursor = await self._conn.execute("SELECT * FROM nav_state WHERE id = 1")
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_events(
        self,
        event_type: Optional[str] = None,
        limit: int = 100,
        since_ts: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM events"
        params: List[Any] = []
        conditions: List[str] = []

        if event_type:
            conditions.append("type = ?")
            params.append(event_type)
        if since_ts is not None:
            conditions.append("ts >= ?")
            params.append(since_ts)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        cursor = await self._conn.execute(query, tuple(params))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_last_event(self, event_type: str) -> Optional[Dict[str, Any]]:
        cursor = await self._conn.execute(
            "SELECT * FROM events WHERE type = ? ORDER BY id DESC LIMIT 1",
            (event_type,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    @asynccontextmanager
    async def session(self):
        await self.initialize()
        try:
            yield self
        finally:
            await self.close()


if __name__ == "__main__":
    async def test():
        db = Database("data/test_instinto.db")
        await db.initialize()

        event_id = await db.append_event(
            source="test",
            event_type="TEST_EVENT",
            payload={"message": "hello", "value": 42}
        )
        print(f"Evento criado com ID: {event_id}")

        await db.upsert_position(
            symbol="BTC/USDT",
            side="long",
            amount=0.01,
            entry_price=65000.0,
            current_price=65100.0,
            exchange_ts=time.time()
        )

        positions = await db.get_positions()
        print(f"Posições: {positions}")

        await db.update_nav_state(
            total_equity=1000.0,
            available_balance=500.0,
            used_margin=500.0,
            unrealized_pnl=50.0
        )
        nav = await db.get_nav_state()
        print(f"NAV: {nav}")

        await db.close()
        print("Teste concluído com sucesso.")

    asyncio.run(test())
