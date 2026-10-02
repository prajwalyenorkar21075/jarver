"""Fine-grained permission and security layer for JARVIS."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PermissionLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PermissionAction(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
    REQUIRE_AUTH = "REQUIRE_AUTH"


@dataclass
class PermissionCheck:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    operation: str = ""
    level: PermissionLevel = PermissionLevel.LOW
    action: PermissionAction = PermissionAction.ALLOW
    agent: str = ""
    tool: str = ""
    timestamp: float = field(default_factory=time.time)
    confirmed: bool = False
    confirmed_by: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "operation": self.operation,
            "level": self.level.value,
            "action": self.action.value,
            "agent": self.agent,
            "tool": self.tool,
            "timestamp": self.timestamp,
            "confirmed": self.confirmed,
            "confirmed_by": self.confirmed_by,
            "reason": self.reason,
        }


LOW_RISK_OPERATIONS = {
    "read", "get", "list", "search", "query", "status", "info",
    "navigate_query", "explain", "learn", "diagnose", "monitor",
}

MEDIUM_RISK_OPERATIONS = {
    "open", "create", "modify", "update", "execute", "run",
    "install", "download", "send", "write", "edit", "launch",
    "play", "start", "connect", "configure",
}

HIGH_RISK_OPERATIONS = {
    "delete", "remove", "destroy", "reset", "restart",
    "shutdown", "format", "erase", "override",
}

CRITICAL_RISK_OPERATIONS = {
    "robot_move", "actuator", "physical", "emergency",
    "security_bypass", "permission_change", "system_override",
    "remote_robot", "hardware_command",
}

RISK_KEYWORDS = {
    PermissionLevel.LOW: LOW_RISK_OPERATIONS,
    PermissionLevel.MEDIUM: MEDIUM_RISK_OPERATIONS,
    PermissionLevel.HIGH: HIGH_RISK_OPERATIONS,
    PermissionLevel.CRITICAL: CRITICAL_RISK_OPERATIONS,
}


class PermissionManager:
    def __init__(self):
        self._audit_log: list[PermissionCheck] = []
        self._max_audit = 1000
        self._pending_confirmations: dict[str, PermissionCheck] = {}
        self._auto_approve_low = True

    def classify_risk(self, operation: str, tool: str = "") -> PermissionLevel:
        op_lower = operation.lower()
        tool_lower = tool.lower()

        for keyword in CRITICAL_RISK_OPERATIONS:
            if keyword in op_lower or keyword in tool_lower:
                return PermissionLevel.CRITICAL

        for keyword in HIGH_RISK_OPERATIONS:
            if keyword in op_lower or keyword in tool_lower:
                return PermissionLevel.HIGH

        for keyword in MEDIUM_RISK_OPERATIONS:
            if keyword in op_lower or keyword in tool_lower:
                return PermissionLevel.MEDIUM

        return PermissionLevel.LOW

    def check_permission(
        self,
        operation: str,
        agent: str = "",
        tool: str = "",
    ) -> PermissionCheck:
        level = self.classify_risk(operation, tool)
        check = PermissionCheck(operation=operation, level=level, agent=agent, tool=tool)

        if level == PermissionLevel.LOW:
            check.action = PermissionAction.ALLOW
            check.reason = "Low risk operation — auto-allowed"
        elif level == PermissionLevel.MEDIUM:
            check.action = PermissionAction.ALLOW
            check.reason = "Medium risk — allowed with audit logging"
        elif level == PermissionLevel.HIGH:
            check.action = PermissionAction.REQUIRE_CONFIRMATION
            check.reason = "High risk — requires user confirmation"
        elif level == PermissionLevel.CRITICAL:
            check.action = PermissionAction.REQUIRE_AUTH
            check.reason = "Critical risk — requires explicit authentication and confirmation"

        self._audit(check)
        return check

    def confirm_permission(self, check_id: str, confirmed_by: str = "user") -> bool:
        check = self._pending_confirmations.get(check_id)
        if not check:
            for c in reversed(self._audit_log):
                if c.id == check_id:
                    check = c
                    break
        if not check:
            return False

        check.confirmed = True
        check.confirmed_by = confirmed_by
        check.action = PermissionAction.ALLOW
        self._audit(check)
        logger.info(f"[PERMISSION] Confirmed: {check.operation} by {confirmed_by}")
        return True

    def deny_permission(self, check_id: str, reason: str = "") -> bool:
        for c in reversed(self._audit_log):
            if c.id == check_id:
                c.action = PermissionAction.DENY
                c.reason = reason or "Denied by user"
                self._audit(c)
                logger.info(f"[PERMISSION] Denied: {c.operation}")
                return True
        return False

    def _audit(self, check: PermissionCheck):
        self._audit_log.append(check)
        if len(self._audit_log) > self._max_audit:
            self._audit_log = self._audit_log[-self._max_audit:]

        if check.action in (PermissionAction.REQUIRE_CONFIRMATION, PermissionAction.REQUIRE_AUTH):
            self._pending_confirmations[check.id] = check

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._audit_log[-limit:]]

    def get_pending_confirmations(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._pending_confirmations.values() if not c.confirmed]

    def get_stats(self) -> dict[str, Any]:
        total = len(self._audit_log)
        allowed = sum(1 for c in self._audit_log if c.action == PermissionAction.ALLOW)
        denied = sum(1 for c in self._audit_log if c.action == PermissionAction.DENY)
        pending = sum(1 for c in self._pending_confirmations.values() if not c.confirmed)
        by_level = {}
        for c in self._audit_log:
            lvl = c.level.value
            by_level[lvl] = by_level.get(lvl, 0) + 1
        return {
            "total_checks": total,
            "allowed": allowed,
            "denied": denied,
            "pending_confirmations": pending,
            "by_level": by_level,
        }


_permission_manager: PermissionManager | None = None


def get_permission_manager() -> PermissionManager:
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager
