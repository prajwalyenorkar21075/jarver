"""State Manager - SQLite-backed state management.

Ported from OpenClaw. Uses SQLite with WAL mode for concurrent access.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StateManager:
    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path) if db_path else Path.home() / ".jarvis" / "state" / "jarvis.sqlite"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                namespace TEXT DEFAULT 'default',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_state (
                agent_name TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    def set(self, key: str, value: Any, namespace: str = "default") -> None:
        serialized = json.dumps(value)
        self._conn.execute(
            "INSERT OR REPLACE INTO kv_store (key, value, namespace) VALUES (?, ?, ?)",
            (key, serialized, namespace),
        )
        self._conn.commit()

    def get(self, key: str, namespace: str = "default", default: Any = None) -> Any:
        cursor = self._conn.execute(
            "SELECT value FROM kv_store WHERE key = ? AND namespace = ?",
            (key, namespace),
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return default

    def delete(self, key: str, namespace: str = "default") -> bool:
        cursor = self._conn.execute(
            "DELETE FROM kv_store WHERE key = ? AND namespace = ?",
            (key, namespace),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def list_keys(self, namespace: str = "default") -> list[str]:
        cursor = self._conn.execute(
            "SELECT key FROM kv_store WHERE namespace = ? ORDER BY key",
            (namespace,),
        )
        return [row[0] for row in cursor.fetchall()]

    def save_conversation(self, session_id: str, role: str, content: str, metadata: dict | None = None) -> int:
        cursor = self._conn.execute(
            "INSERT INTO conversation_history (session_id, role, content, metadata) VALUES (?, ?, ?, ?)",
            (session_id, role, content, json.dumps(metadata or {})),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_conversation(self, session_id: str, limit: int = 50) -> list[dict]:
        cursor = self._conn.execute(
            "SELECT role, content, metadata, created_at FROM conversation_history WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        rows = cursor.fetchall()
        return [
            {"role": r[0], "content": r[1], "metadata": json.loads(r[2]), "created_at": r[3]}
            for r in reversed(rows)
        ]

    def save_agent_state(self, agent_name: str, state: dict) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO agent_state (agent_name, state_json) VALUES (?, ?)",
            (agent_name, json.dumps(state)),
        )
        self._conn.commit()

    def get_agent_state(self, agent_name: str) -> dict | None:
        cursor = self._conn.execute(
            "SELECT state_json FROM agent_state WHERE agent_name = ?",
            (agent_name,),
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
