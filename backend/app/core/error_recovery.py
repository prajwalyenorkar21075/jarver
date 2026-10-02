"""Self-error detection and recovery engine for JARVIS."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable, Optional

from .execution import ExecutionStatus, ExecutionResult, RetryPolicy

logger = logging.getLogger(__name__)


class FailureType(str, Enum):
    TRANSIENT = "TRANSIENT"
    PERSISTENT = "PERSISTENT"
    PERMISSION = "PERMISSION"
    TIMEOUT = "TIMEOUT"
    RESOURCE = "RESOURCE"
    VALIDATION = "VALIDATION"
    UNKNOWN = "UNKNOWN"


class RecoveryAction(str, Enum):
    RETRY = "RETRY"
    RETRY_WITH_BACKOFF = "RETRY_WITH_BACKOFF"
    ALTERNATIVE = "ALTERNATIVE"
    FALLBACK = "FALLBACK"
    SKIP = "SKIP"
    ABORT = "ABORT"
    ESCALATE = "ESCALATE"
    WAIT = "WAIT"


@dataclass
class FailurePattern:
    error_pattern: str
    failure_type: FailureType
    recovery_action: RecoveryAction
    max_occurrences: int = 3
    occurrence_count: int = 0
    alternative_fn: Optional[Callable] = None


@dataclass
class RecoveryRecord:
    timestamp: float
    operation: str
    failure_type: FailureType
    error: str
    action_taken: RecoveryAction
    success: bool
    attempt: int


class RecoveryEngine:
    def __init__(self):
        self._patterns: list[FailurePattern] = []
        self._history: list[RecoveryRecord] = []
        self._failure_counts: dict[str, int] = {}
        self._max_history = 500
        self._setup_default_patterns()

    def _setup_default_patterns(self):
        self._patterns = [
            FailurePattern("timeout", FailureType.TIMEOUT, RecoveryAction.RETRY_WITH_BACKOFF),
            FailurePattern("connection", FailureType.TRANSIENT, RecoveryAction.RETRY_WITH_BACKOFF),
            FailurePattern("rate.limit", FailureType.TRANSIENT, RecoveryAction.WAIT),
            FailurePattern("permission", FailureType.PERMISSION, RecoveryAction.ESCALATE),
            FailurePattern("unauthorized", FailureType.PERMISSION, RecoveryAction.ESCALATE),
            FailurePattern("not.found", FailureType.PERSISTENT, RecoveryAction.ABORT),
            FailurePattern("resource", FailureType.RESOURCE, RecoveryAction.WAIT),
            FailurePattern("busy", FailureType.RESOURCE, RecoveryAction.WAIT),
            FailurePattern("validation", FailureType.VALIDATION, RecoveryAction.ABORT),
            FailurePattern("invalid", FailureType.VALIDATION, RecoveryAction.ABORT),
        ]

    def classify_failure(self, error: str) -> FailureType:
        error_lower = error.lower()
        for pattern in self._patterns:
            if pattern.error_pattern in error_lower:
                return pattern.failure_type
        return FailureType.UNKNOWN

    def decide_recovery(self, error: str, attempt: int, policy: RetryPolicy) -> RecoveryAction:
        failure_type = self.classify_failure(error)
        error_lower = error.lower()

        for pattern in self._patterns:
            if pattern.error_pattern in error_lower:
                if pattern.failure_type == FailureType.PERMISSION:
                    return RecoveryAction.ESCALATE
                if pattern.failure_type == FailureType.VALIDATION:
                    return RecoveryAction.ABORT
                break

        if not policy.should_retry(ExecutionStatus.FAILED, attempt):
            return RecoveryAction.ESCALATE

        error_lower = error.lower()
        for pattern in self._patterns:
            if pattern.error_pattern in error_lower:
                if pattern.recovery_action == RecoveryAction.ALTERNATIVE and pattern.alternative_fn:
                    return RecoveryAction.ALTERNATIVE
                return pattern.recovery_action

        return RecoveryAction.RETRY_WITH_BACKOFF

    async def execute_with_recovery(
        self,
        operation: str,
        fn: Callable[..., Awaitable[Any]],
        policy: RetryPolicy | None = None,
        alternative_fn: Callable[..., Awaitable[Any]] | None = None,
        *args,
        **kwargs,
    ) -> ExecutionResult:
        result = ExecutionResult(operation=operation)
        policy = policy or RetryPolicy()
        result.status = ExecutionStatus.RUNNING

        for attempt in range(policy.max_retries + 1):
            result.attempts = attempt + 1
            try:
                value = await fn(*args, **kwargs)
                result.succeed(result=value)
                if attempt > 0:
                    result.recovery_applied = True
                self._record(RecoveryRecord(
                    timestamp=time.time(),
                    operation=operation,
                    failure_type=FailureType.UNKNOWN,
                    error="",
                    action_taken=RecoveryAction.RETRY,
                    success=True,
                    attempt=attempt,
                ))
                return result

            except Exception as e:
                error_msg = str(e)
                action = self.decide_recovery(error_msg, attempt, policy)

                logger.warning(
                    f"[RECOVERY] {operation} attempt {attempt + 1}/{policy.max_retries + 1} "
                    f"failed: {error_msg} → {action.value}"
                )

                if action == RecoveryAction.ESCALATE:
                    result.fail(error=error_msg, error_type=self.classify_failure(error_msg).value)
                    self._record(RecoveryRecord(
                        timestamp=time.time(),
                        operation=operation,
                        failure_type=self.classify_failure(error_msg),
                        error=error_msg,
                        action_taken=action,
                        success=False,
                        attempt=attempt,
                    ))
                    return result

                if action == RecoveryAction.ABORT:
                    result.fail(error=error_msg, error_type=self.classify_failure(error_msg).value)
                    return result

                if action == RecoveryAction.ALTERNATIVE and alternative_fn:
                    try:
                        value = await alternative_fn(*args, **kwargs)
                        result.succeed(result=value)
                        result.recovery_applied = True
                        return result
                    except Exception as alt_e:
                        result.fail(error=f"Primary: {error_msg}, Alternative: {alt_e}")
                        return result

                if action in (RecoveryAction.RETRY_WITH_BACKOFF, RecoveryAction.RETRY):
                    delay = policy.get_delay(attempt)
                    result.status = ExecutionStatus.RETRYING
                    await asyncio.sleep(delay)
                    continue

                if action == RecoveryAction.WAIT:
                    await asyncio.sleep(policy.base_delay)
                    continue

        result.fail(
            error=f"Max retries ({policy.max_retries}) exceeded",
            error_type=FailureType.PERSISTENT.value,
        )
        result.recovery_applied = True
        return result

    def _record(self, record: RecoveryRecord):
        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_failure_patterns(self) -> dict[str, int]:
        return dict(self._failure_counts)

    def get_recovery_stats(self) -> dict[str, Any]:
        total = len(self._history)
        successful = sum(1 for r in self._history if r.success)
        return {
            "total_recoveries": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": round(successful / total * 100, 1) if total > 0 else 0.0,
            "recent": [
                {
                    "operation": r.operation,
                    "failure_type": r.failure_type.value,
                    "action": r.action_taken.value,
                    "success": r.success,
                }
                for r in self._history[-10:]
            ],
        }

    def learn_from_failure(self, error_pattern: str, failure_type: FailureType, preferred_action: RecoveryAction):
        for pattern in self._patterns:
            if pattern.error_pattern == error_pattern:
                pattern.recovery_action = preferred_action
                return
        self._patterns.append(FailurePattern(
            error_pattern=error_pattern,
            failure_type=failure_type,
            recovery_action=preferred_action,
        ))


_recovery_engine: RecoveryEngine | None = None


def get_recovery_engine() -> RecoveryEngine:
    global _recovery_engine
    if _recovery_engine is None:
        _recovery_engine = RecoveryEngine()
    return _recovery_engine
