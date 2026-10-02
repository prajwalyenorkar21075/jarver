"""Heartbeat System - Proactive periodic checks.

Ported from OpenClaw. Agent periodically wakes and runs through a checklist.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatTask:
    name: str
    description: str
    interval_seconds: int = 3600
    handler: Callable | None = None
    enabled: bool = True
    last_run: float = 0.0
    last_result: Any = None


class HeartbeatSystem:
    def __init__(self, state_file: str | Path | None = None):
        self._tasks: dict[str, HeartbeatTask] = {}
        self._state_file = Path(state_file) if state_file else Path.home() / ".jarvis" / "heartbeat-state.json"
        self._load_state()

    def register_task(self, name: str, description: str, handler: Callable, interval_seconds: int = 3600) -> None:
        self._tasks[name] = HeartbeatTask(
            name=name,
            description=description,
            interval_seconds=interval_seconds,
            handler=handler,
            last_run=self._last_run_times.get(name, 0.0),
        )

    def get_due_tasks(self) -> list[HeartbeatTask]:
        now = time.time()
        due = []
        for task in self._tasks.values():
            if not task.enabled:
                continue
            if now - task.last_run >= task.interval_seconds:
                due.append(task)
        return due

    async def run_due_tasks(self) -> dict[str, Any]:
        due = self.get_due_tasks()
        results = {}

        for task in due:
            logger.info(f"Heartbeat: running task '{task.name}'")
            try:
                if task.handler:
                    if callable(task.handler):
                        import asyncio
                        if asyncio.iscoroutinefunction(task.handler):
                            result = await task.handler()
                        else:
                            result = task.handler()
                    else:
                        result = None
                else:
                    result = None

                task.last_run = time.time()
                task.last_result = result
                results[task.name] = {"success": True, "result": result}
            except Exception as e:
                logger.error(f"Heartbeat task '{task.name}' failed: {e}")
                results[task.name] = {"success": False, "error": str(e)}

        self._save_state()
        return results

    def get_status(self) -> dict[str, Any]:
        now = time.time()
        tasks = {}
        for name, task in self._tasks.items():
            tasks[name] = {
                "description": task.description,
                "enabled": task.enabled,
                "interval": task.interval_seconds,
                "last_run": task.last_run,
                "next_run_in": max(0, task.interval_seconds - (now - task.last_run)),
                "last_result": str(task.last_result)[:200] if task.last_result else None,
            }
        return {"tasks": tasks, "due_count": len(self.get_due_tasks())}

    def _load_state(self) -> None:
        self._last_run_times: dict[str, float] = {}
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                self._last_run_times = data.get("last_run", {})
            except Exception:
                pass

    def _save_state(self) -> None:
        state = {
            "last_run": {name: task.last_run for name, task in self._tasks.items()},
        }
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
