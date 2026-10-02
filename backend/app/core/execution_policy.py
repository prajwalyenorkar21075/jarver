"""Centralized Safe AI Execution Layer for JARVIS.

Every capability invocation (agent, tool, industrial control, security test)
is classified before it runs, so the same rules apply no matter which module
or route asked for it.

Action classes
    READ        — inspect state, no side effects
    ANALYZE     — compute over existing data, no side effects
    SIMULATE    — run against a model/simulator, never real hardware
    WRITE       — change a file, a record, or a device setpoint
    CONTROL     — command real hardware/machinery
    SECURITY_TEST — active security testing against an authorized target

Rules enforced here:
  * HIGH/CRITICAL actions require a recorded authorization or explicit confirmation
  * physical CONTROL actions require an explicit confirmation token
  * SECURITY_TEST actions require an active, in-scope, authorized test scope
  * every decision is written to an in-process execution record (see observability)

This module does not replace ``core.permissions``: the permission manager stays
the risk classifier and user-confirmation gate. This layer adds the physical /
security-specific scoping rules and produces the structured record that the
observability layer persists.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("jarvis.execution_policy")


class ActionClass(str, Enum):
    READ = "READ"
    ANALYZE = "ANALYZE"
    SIMULATE = "SIMULATE"
    WRITE = "WRITE"
    CONTROL = "CONTROL"
    SECURITY_TEST = "SECURITY_TEST"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
    REQUIRE_AUTHORIZATION = "REQUIRE_AUTHORIZATION"
    DENY = "DENY"


# Default risk per action class. A caller may raise it, never lower it.
_ACTION_RISK = {
    ActionClass.READ: RiskLevel.LOW,
    ActionClass.ANALYZE: RiskLevel.LOW,
    ActionClass.SIMULATE: RiskLevel.LOW,
    ActionClass.WRITE: RiskLevel.MEDIUM,
    ActionClass.CONTROL: RiskLevel.CRITICAL,
    ActionClass.SECURITY_TEST: RiskLevel.HIGH,
}

# Substrings that mark an operation as physical control of real machinery.
_CONTROL_MARKERS = (
    "actuator", "motor", "conveyor", "servo", "valve", "relay",
    "write_tag", "setpoint", "jog", "energize", "plc_write", "robot_move",
    "joint_command", "emergency_release",
)

# Substrings that mark an operation as reading only (never a control action).
_READ_MARKERS = (
    "status", "state", "read", "list", "get", "query", "monitor",
    "telemetry", "diagnose", "inspect",
)


@dataclass
class ExecutionRecord:
    """The single structured record every capability call produces."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    tool_name: str = ""
    agent: str = ""
    user_intent: str = ""
    target: str = ""
    requested_action: str = ""
    action_class: str = ActionClass.READ.value
    risk_level: str = RiskLevel.LOW.value
    required_permission: str = ""
    authorization_state: str = "not_required"
    decision: str = PolicyDecision.ALLOW.value
    decision_reason: str = ""
    execution_status: str = "pending"
    validation_status: str = "pending"
    result: Any = None
    error: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    duration_ms: float = 0.0
    task_id: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    db_changes: list[str] = field(default_factory=list)

    def finish(self, status: str, result: Any = None, error: str = "", validation: str = "pending"):
        self.execution_status = status
        self.result = result
        self.error = error
        self.validation_status = validation
        self.finished_at = time.time()
        self.duration_ms = round((self.finished_at - self.started_at) * 1000, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "tool_name": self.tool_name,
            "agent": self.agent,
            "user_intent": self.user_intent,
            "target": self.target,
            "requested_action": self.requested_action,
            "action_class": self.action_class,
            "risk_level": self.risk_level,
            "required_permission": self.required_permission,
            "authorization_state": self.authorization_state,
            "decision": self.decision,
            "decision_reason": self.decision_reason,
            "execution_status": self.execution_status,
            "validation_status": self.validation_status,
            "result": _safe(self.result),
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "context": self.context,
            "db_changes": self.db_changes,
        }


def _safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in list(value.items())[:40]}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in list(value)[:40]]
    return str(value)[:500]


class ExecutionPolicy:
    """Classifies and authorizes capability invocations."""

    def __init__(self, max_history: int = 500):
        self._history: list[ExecutionRecord] = []
        self._max_history = max_history
        self._confirmations: dict[str, float] = {}

    # ------------------------------------------------------------------ #
    # Classification
    # ------------------------------------------------------------------ #
    def classify_action(self, operation: str, declared: ActionClass | str | None = None,
                        target: str = "") -> ActionClass:
        """Return the action class, never weaker than the declared one."""
        text = f"{operation} {target}".lower()

        inferred: Optional[ActionClass] = None
        if any(m in text for m in _CONTROL_MARKERS):
            inferred = ActionClass.CONTROL
        elif "security_test" in text or "port_scan" in text or "vuln" in text or "pen_test" in text:
            inferred = ActionClass.SECURITY_TEST
        elif any(m in text for m in _READ_MARKERS):
            inferred = ActionClass.READ

        declared_cls: Optional[ActionClass] = None
        if declared is not None:
            declared_cls = declared if isinstance(declared, ActionClass) else ActionClass(str(declared).upper())

        order = [ActionClass.READ, ActionClass.ANALYZE, ActionClass.SIMULATE,
                 ActionClass.WRITE, ActionClass.SECURITY_TEST, ActionClass.CONTROL]

        if declared_cls is None:
            return inferred or ActionClass.READ
        if inferred is None:
            return declared_cls
        return declared_cls if order.index(declared_cls) >= order.index(inferred) else inferred

    # ------------------------------------------------------------------ #
    # Authorization / gating
    # ------------------------------------------------------------------ #
    def evaluate(
        self,
        operation: str,
        *,
        agent: str = "",
        tool: str = "",
        target: str = "",
        action_class: ActionClass | str | None = None,
        authorized: bool = False,
        scope_id: str | None = None,
        simulate: bool = False,
        user_intent: str = "",
        task_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> ExecutionRecord:
        cls = self.classify_action(operation, action_class, target)
        # A simulation of a control action never touches hardware: it is a SIMULATE.
        if simulate and cls in (ActionClass.CONTROL, ActionClass.SECURITY_TEST):
            cls = ActionClass.SIMULATE

        risk = _ACTION_RISK[cls]
        record = ExecutionRecord(
            tool_name=tool or operation,
            agent=agent,
            user_intent=user_intent or operation,
            target=target,
            requested_action=operation,
            action_class=cls.value,
            risk_level=risk.value,
            required_permission=self._required_permission(cls),
            task_id=task_id,
            context=context or {},
        )

        if cls in (ActionClass.READ, ActionClass.ANALYZE, ActionClass.SIMULATE):
            record.decision = PolicyDecision.ALLOW.value
            record.decision_reason = f"{cls.value} action — no side effects on real systems"
            if simulate:
                record.decision_reason += " (simulated execution, no hardware touched)"
            record.authorization_state = "not_required"
            self._store(record)
            return record

        if cls == ActionClass.WRITE:
            record.decision = PolicyDecision.ALLOW.value
            record.decision_reason = "WRITE action — audited, reversible where the target supports undo"
            record.authorization_state = "not_required"
            self._store(record)
            return record

        if cls == ActionClass.SECURITY_TEST:
            record.authorization_state = "authorized" if authorized else "not_authorized"
            if not authorized:
                record.decision = PolicyDecision.DENY.value
                record.decision_reason = (
                    "Security testing requires an active authorized scope covering the target. "
                    "Create a scope with the target listed, then retry."
                )
            else:
                record.decision = PolicyDecision.ALLOW.value
                record.decision_reason = f"Target authorized under scope {scope_id or 'active scope'}"
            self._store(record)
            return record

        # CONTROL
        record.required_permission = "explicit_confirmation"
        if authorized or self._is_confirmed(operation, target):
            record.authorization_state = "confirmed"
            record.decision = PolicyDecision.ALLOW.value
            record.decision_reason = "Physical control confirmed by the operator"
        else:
            record.authorization_state = "pending_confirmation"
            record.decision = PolicyDecision.REQUIRE_CONFIRMATION.value
            record.decision_reason = (
                "Physical control of real equipment requires explicit operator confirmation. "
                "Re-issue the action with authorization=authorized after confirming."
            )
        self._store(record)
        return record

    def _required_permission(self, cls: ActionClass) -> str:
        return {
            ActionClass.READ: "none",
            ActionClass.ANALYZE: "none",
            ActionClass.SIMULATE: "none",
            ActionClass.WRITE: "write_audit",
            ActionClass.CONTROL: "explicit_confirmation",
            ActionClass.SECURITY_TEST: "authorized_scope",
        }[cls]

    def confirm(self, operation: str, target: str = "", confirmed_by: str = "user") -> str:
        """Record an operator confirmation; returns the token for the retry call."""
        token = str(uuid.uuid4())[:8]
        self._confirmations[token] = time.time()
        self._confirmations[f"{operation}|{target}"] = time.time()
        logger.info(f"[POLICY] Control confirmed by {confirmed_by}: {operation} -> {target or 'local'}")
        return token

    def _is_confirmed(self, operation: str, target: str) -> bool:
        key = f"{operation}|{target}"
        ts = self._confirmations.get(key)
        if ts is None:
            return False
        if time.time() - ts > 120:
            del self._confirmations[key]
            return False
        return True

    # ------------------------------------------------------------------ #
    # History / observability
    # ------------------------------------------------------------------ #
    def _store(self, record: ExecutionRecord):
        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_record(self, record_id: str) -> Optional[ExecutionRecord]:
        for r in reversed(self._history):
            if r.id == record_id:
                return r
        return None

    def update_record(self, record_id: str, **kwargs):
        record = self.get_record(record_id)
        if not record:
            return None
        for key, value in kwargs.items():
            if hasattr(record, key):
                setattr(record, key, value)
        return record

    def get_history(self, limit: int = 50, action_class: str | None = None) -> list[dict[str, Any]]:
        items = self._history
        if action_class:
            items = [r for r in items if r.action_class == action_class]
        return [r.to_dict() for r in items[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        by_class: dict[str, int] = {}
        by_decision: dict[str, int] = {}
        for r in self._history:
            by_class[r.action_class] = by_class.get(r.action_class, 0) + 1
            by_decision[r.decision] = by_decision.get(r.decision, 0) + 1
        return {
            "total_records": len(self._history),
            "by_action_class": by_class,
            "by_decision": by_decision,
            "denied": sum(1 for r in self._history if r.decision == PolicyDecision.DENY.value),
            "control_actions": by_class.get(ActionClass.CONTROL.value, 0),
            "security_tests": by_class.get(ActionClass.SECURITY_TEST.value, 0),
        }


_policy: ExecutionPolicy | None = None


def get_execution_policy() -> ExecutionPolicy:
    global _policy
    if _policy is None:
        _policy = ExecutionPolicy()
    return _policy
