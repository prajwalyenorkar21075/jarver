"""Structured execution status and results for all JARVIS operations."""

from __future__ import annotations

import time
import uuid
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    BLOCKED = "BLOCKED"
    PERMISSION_REQUIRED = "PERMISSION_REQUIRED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    CANCELLED = "CANCELLED"
    RETRYING = "RETRYING"


@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_backoff: bool = True
    retryable_statuses: tuple[ExecutionStatus, ...] = (
        ExecutionStatus.FAILED,
        ExecutionStatus.TIMEOUT,
    )

    def get_delay(self, attempt: int) -> float:
        if self.exponential_backoff:
            delay = self.base_delay * (2 ** attempt)
        else:
            delay = self.base_delay
        return min(delay, self.max_delay)

    def should_retry(self, status: ExecutionStatus, attempt: int) -> bool:
        return status in self.retryable_statuses and attempt < self.max_retries


@dataclass
class ExecutionResult:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: ExecutionStatus = ExecutionStatus.PENDING
    operation: str = ""
    result: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    attempts: int = 0
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    sub_results: list[ExecutionResult] = field(default_factory=list)
    recovery_applied: bool = False
    verified: bool = False

    def complete(self, status: ExecutionStatus, result: Any = None, error: str | None = None):
        self.status = status
        self.result = result
        self.error = error
        self.completed_at = time.time()
        self.duration_ms = round((self.completed_at - self.started_at) * 1000, 2)

    def fail(self, error: str, error_type: str | None = None):
        self.status = ExecutionStatus.FAILED
        self.error = error
        self.error_type = error_type
        self.completed_at = time.time()
        self.duration_ms = round((self.completed_at - self.started_at) * 1000, 2)

    def succeed(self, result: Any = None):
        self.complete(ExecutionStatus.SUCCESS, result=result)

    def add_sub_result(self, sub: ExecutionResult):
        self.sub_results.append(sub)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status.value,
            "operation": self.operation,
            "result": _safe_serialize(self.result),
            "error": self.error,
            "error_type": self.error_type,
            "attempts": self.attempts,
            "duration_ms": self.duration_ms,
            "verified": self.verified,
            "recovery_applied": self.recovery_applied,
            "sub_results": [s.to_dict() for s in self.sub_results],
            "metadata": self.metadata,
        }


@dataclass
class StepResult:
    step_name: str
    result: ExecutionResult
    critical: bool = True

    @property
    def ok(self) -> bool:
        return self.result.status == ExecutionStatus.SUCCESS


def _safe_serialize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_safe_serialize(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _safe_serialize(v) for k, v in value.items()}
    return str(value)
