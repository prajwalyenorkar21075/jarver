"""Event bus for inter-component communication in JARVIS."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    TOOL_CALLED = "tool.called"
    TOOL_RESULT = "tool.result"
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    PERMISSION_REQUESTED = "permission.requested"
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_DENIED = "permission.denied"
    ERROR_DETECTED = "error.detected"
    RECOVERY_APPLIED = "recovery.applied"
    RECOVERY_FAILED = "recovery.failed"
    MEMORY_UPDATED = "memory.updated"
    STATUS_CHANGED = "status.changed"
    USER_INPUT = "user.input"
    RESPONSE_READY = "response.ready"
    ROBOT_STATE_CHANGED = "robot.state.changed"
    VISION_EVENT = "vision.event"
    NAVIGATION_UPDATE = "navigation.update"


@dataclass
class Event:
    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())[:8]


EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    def __init__(self):
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []
        self._max_history = 200

    def subscribe(self, event_type: EventType, handler: EventHandler):
        self._handlers[event_type].append(handler)
        logger.debug(f"[EVENTBUS] Subscribed to {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: EventHandler):
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def publish(self, event: Event):
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"[EVENTBUS] Handler error for {event.type.value}: {e}")

    async def emit(self, event_type: EventType, data: dict[str, Any] | None = None, source: str = ""):
        event = Event(type=event_type, data=data or {}, source=source)
        await self.publish(event)

    def get_recent_events(self, limit: int = 50, event_type: EventType | None = None) -> list[dict[str, Any]]:
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return [
            {
                "id": e.id,
                "type": e.type.value,
                "source": e.source,
                "data": e.data,
                "timestamp": e.timestamp,
            }
            for e in events[-limit:]
        ]

    def get_stats(self) -> dict[str, Any]:
        by_type = {}
        for e in self._history:
            t = e.type.value
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total_events": len(self._history),
            "subscribers": sum(len(h) for h in self._handlers.values()),
            "by_type": by_type,
        }


_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
