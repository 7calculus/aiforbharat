"""
Async SQLite database for SPASHT AI call logs.
"""

import aiosqlite
from typing import List, Optional
from models import CallLogEntry

DB_PATH = "spasht.db"

CREATE_CALLS_TABLE = """
CREATE TABLE IF NOT EXISTS calls (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    time        TEXT NOT NULL,
    duration    TEXT NOT NULL,
    intent      TEXT NOT NULL,
    confidence  REAL NOT NULL,
    decision    TEXT NOT NULL,
    location    TEXT,
    created_at  TEXT NOT NULL
)
"""


class Database:
    def __init__(self):
        self.db: Optional[aiosqlite.Connection] = None

    async def init(self):
        self.db = await aiosqlite.connect(DB_PATH)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute(CREATE_CALLS_TABLE)
        await self.db.commit()

    async def close(self):
        if self.db:
            await self.db.close()

    async def save_call(self, entry: CallLogEntry):
        await self.db.execute(
            """INSERT INTO calls
               (id, session_id, time, duration, intent, confidence, decision, location, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.id, entry.session_id, entry.time, entry.duration,
                entry.intent, entry.confidence, entry.decision,
                entry.location, entry.created_at,
            ),
        )
        await self.db.commit()

    async def get_calls(self, limit: int = 50) -> List[CallLogEntry]:
        cursor = await self.db.execute(
            "SELECT * FROM calls ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [CallLogEntry(**dict(row)) for row in rows]

    async def get_call(self, session_id: str) -> Optional[CallLogEntry]:
        cursor = await self.db.execute(
            "SELECT * FROM calls WHERE session_id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        return CallLogEntry(**dict(row)) if row else None

    async def delete_call(self, session_id: str):
        await self.db.execute("DELETE FROM calls WHERE session_id = ?", (session_id,))
        await self.db.commit()