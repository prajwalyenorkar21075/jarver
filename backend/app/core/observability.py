"""Unified execution observability for JARVIS.

One row per capability invocation, from any module, covering the full pipeline:

    Task ID | Intent | Agent | Tool | Input | Permission result | Execution |
    Duration | Output | Validation | Errors | Database changes | UI update |
    Voice response

Rows are written to the persistent SQLite database (``task_executions`` table)
so the whole pipeline can be debugged after the fact, and mirrored in memory
for fast reads by the UI.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("jarvis.observability")

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "jarvis_persistent.db"


@dataclass
class PipelineTrace:
    """A complete record of one JARVIS pipeline execution."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    task_id: str = ""
    user_input: str = ""
    intent: str = ""
    agent: str = ""
    tool: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)
    action_class: str = ""
    risk_level: str = ""
    permission_result: str = ""
    permission_id: str = ""
    execution_status: str = "pending"
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    duration_ms: float = 0.0
    output: Any = None
    validation_status: str = "pending"
    validation_detail: str = ""
    errors: list[str] = field(default_factory=list)
    db_changes: list[str] = field(default_factory=list)
    ui_update: str = ""
    voice_response: str = ""
    simulated: bool = False
    source: str = ""

    def finish(self, status: str, output: Any = None, error: str | None = None):
        self.execution_status = status
        self.output = output
        if error:
            self.errors.append(error)
        self.finished_at = time.time()
        self.duration_ms = round((self.finished_at - self.started_at) * 1000, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "user_input": self.user_input,
            "intent": self.intent,
            "agent": self.agent,
            "tool": self.tool,
            "tool_input": self.tool_input,
            "action_class": self.action_class,
            "risk_level": self.risk_level,
            "permission_result": self.permission_result,
            "permission_id": self.permission_id,
            "execution_status": self.execution_status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "output": _safe(self.output),
            "validation_status": self.validation_status,
            "validation_detail": self.validation_detail,
            "errors": self.errors,
            "db_changes": self.db_changes,
            "ui_update": self.ui_update,
            "voice_response": self.voice_response,
            "simulated": self.simulated,
            "source": self.source,
        }


def _safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in list(value.items())[:30]}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in list(value)[:30]]
    return str(value)[:400]


class ObservabilityStore:
    def __init__(self, db_path: Path | None = None, memory_limit: int = 300):
        self.db_path = db_path or DB_PATH
        self._memory: list[PipelineTrace] = []
        self._memory_limit = memory_limit
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS task_executions (
                        id TEXT PRIMARY KEY,
                        task_id TEXT,
                        timestamp REAL NOT NULL,
                        user_input TEXT,
                        intent TEXT,
                        agent TEXT,
                        tool TEXT,
                        tool_input TEXT,
                        action_class TEXT,
                        risk_level TEXT,
                        permission_result TEXT,
                        permission_id TEXT,
                        execution_status TEXT,
                        duration_ms REAL,
                        output TEXT,
                        validation_status TEXT,
                        validation_detail TEXT,
                        errors TEXT,
                        db_changes TEXT,
                        ui_update TEXT,
                        voice_response TEXT,
                        simulated INTEGER DEFAULT 0,
                        source TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_task_exec_task ON task_executions(task_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_task_exec_ts ON task_executions(timestamp DESC)")
                conn.commit()
            logger.info(f"[OBSERVABILITY] task_executions table ready at {self.db_path}")
        except Exception as e:
            logger.warning(f"[OBSERVABILITY] Could not create task_executions table: {e}")

    def start_trace(self, **kwargs) -> PipelineTrace:
        trace = PipelineTrace(**kwargs)
        self._memory.append(trace)
        if len(self._memory) > self._memory_limit:
            self._memory = self._memory[-self._memory_limit:]
        return trace

    def record(self, trace: PipelineTrace, persist: bool = True):
        if trace not in self._memory:
            self._memory.append(trace)
            if len(self._memory) > self._memory_limit:
                self._memory = self._memory[-self._memory_limit:]
        if persist:
            self._persist(trace)

    def _persist(self, trace: PipelineTrace):
        try:
            with self._connect() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO task_executions
                    (id, task_id, timestamp, user_input, intent, agent, tool, tool_input,
                     action_class, risk_level, permission_result, permission_id,
                     execution_status, duration_ms, output, validation_status,
                     validation_detail, errors, db_changes, ui_update, voice_response,
                     simulated, source)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    trace.id, trace.task_id, trace.started_at, trace.user_input, trace.intent,
                    trace.agent, trace.tool, json.dumps(_safe(trace.tool_input)),
                    trace.action_class, trace.risk_level, trace.permission_result, trace.permission_id,
                    trace.execution_status, trace.duration_ms, json.dumps(_safe(trace.output)),
                    trace.validation_status, trace.validation_detail, json.dumps(trace.errors),
                    json.dumps(trace.db_changes), trace.ui_update, trace.voice_response,
                    1 if trace.simulated else 0, trace.source,
                ))
                conn.commit()
        except Exception as e:
            logger.debug(f"[OBSERVABILITY] persist skipped: {e}")

    def get_trace(self, trace_id: str) -> Optional[dict[str, Any]]:
        for t in reversed(self._memory):
            if t.id == trace_id:
                return t.to_dict()
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM task_executions WHERE id=?", (trace_id,)).fetchone()
                return dict(row) if row else None
        except Exception:
            return None

    def get_by_task(self, task_id: str) -> list[dict[str, Any]]:
        rows = [t.to_dict() for t in self._memory if t.task_id == task_id]
        if rows:
            return rows
        try:
            with self._connect() as conn:
                return [dict(r) for r in conn.execute(
                    "SELECT * FROM task_executions WHERE task_id=? ORDER BY timestamp ASC", (task_id,)
                )]
        except Exception:
            return []

    def recent(self, limit: int = 50, agent: str | None = None,
               status: str | None = None) -> list[dict[str, Any]]:
        items = list(reversed(self._memory))
        if agent:
            items = [t for t in items if t.agent == agent]
        if status:
            items = [t for t in items if t.execution_status == status]
        if items:
            return [t.to_dict() for t in items[:limit]]
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM task_executions ORDER BY timestamp DESC LIMIT ?", (limit,)
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def get_stats(self) -> dict[str, Any]:
        stats = {
            "in_memory": len(self._memory),
            "completed": 0,
            "failed": 0,
            "by_agent": {},
            "by_action_class": {},
            "avg_duration_ms": 0.0,
        }
        durations = []
        for t in self._memory:
            if t.execution_status == "completed":
                stats["completed"] += 1
            elif t.execution_status == "failed":
                stats["failed"] += 1
            if t.agent:
                stats["by_agent"][t.agent] = stats["by_agent"].get(t.agent, 0) + 1
            if t.action_class:
                stats["by_action_class"][t.action_class] = stats["by_action_class"].get(t.action_class, 0) + 1
            if t.duration_ms:
                durations.append(t.duration_ms)
        if durations:
            stats["avg_duration_ms"] = round(sum(durations) / len(durations), 2)
        try:
            with self._connect() as conn:
                stats["persisted_rows"] = conn.execute(
                    "SELECT COUNT(*) FROM task_executions"
                ).fetchone()[0]
        except Exception:
            stats["persisted_rows"] = 0
        return stats


_store: ObservabilityStore | None = None


def get_observability() -> ObservabilityStore:
    global _store
    if _store is None:
        _store = ObservabilityStore()
    return _store
