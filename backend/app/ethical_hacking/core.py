"""
Ethical Hacking / Authorized Penetration Testing Module for JARVIS.

This module provides comprehensive ethical hacking capabilities with strict
authorization controls, scope management, and safety mechanisms.

CRITICAL: All testing must be authorized and within defined scope.
"""

import logging
import time
import json
import uuid
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class TestMode(str, Enum):
    SAFE = "safe"
    READ_ONLY = "read_only"
    INTRUSIVE = "intrusive"


class AuthorizationStatus(str, Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    DENIED = "denied"
    EXPIRED = "expired"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class TestScope:
    """Defines the authorized testing scope."""
    id: str
    name: str
    targets: list[str]
    excluded_targets: list[str] = field(default_factory=list)
    allowed_ports: list[int] = field(default_factory=list)
    excluded_ports: list[int] = field(default_factory=list)
    test_types: list[str] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    authorized_by: str = ""
    authorization_status: AuthorizationStatus = AuthorizationStatus.PENDING
    mode: TestMode = TestMode.SAFE
    created_at: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if not self.start_time:
            self.start_time = time.time()

    def is_target_authorized(self, target: str) -> bool:
        if self.authorization_status != AuthorizationStatus.AUTHORIZED:
            return False
        if target in self.excluded_targets:
            return False
        if not self.targets:
            return True
        return any(self._matches_scope(target, scope) for scope in self.targets)

    def _matches_scope(self, target: str, scope: str) -> bool:
        if scope == target:
            return True
        if scope.startswith("*.") and target.endswith(scope[2:]):
            return True
        if "/" in scope:
            try:
                import ipaddress
                return ipaddress.ip_address(target) in ipaddress.ip_network(scope, strict=False)
            except ValueError:
                return False
        return False

    def is_active(self) -> bool:
        if self.authorization_status != AuthorizationStatus.AUTHORIZED:
            return False
        if self.end_time and time.time() > self.end_time:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "targets": self.targets,
            "excluded_targets": self.excluded_targets,
            "allowed_ports": self.allowed_ports,
            "excluded_ports": self.excluded_ports,
            "test_types": self.test_types,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "authorized_by": self.authorized_by,
            "authorization_status": self.authorization_status.value,
            "mode": self.mode.value,
            "is_active": self.is_active(),
        }


@dataclass
class SecurityFinding:
    """Represents a security finding with complete evidence."""
    id: str
    finding_type: str
    severity: Severity
    title: str
    description: str
    target: str
    scope_id: str
    evidence: dict = field(default_factory=dict)
    affected_component: str = ""
    cve_id: Optional[str] = None
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None
    remediation: str = ""
    references: list[str] = field(default_factory=list)
    timestamp: float = 0.0
    verified: bool = False
    retest_status: str = "pending"

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.id:
            self.id = str(uuid.uuid4())[:12]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "finding_type": self.finding_type,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "target": self.target,
            "scope_id": self.scope_id,
            "evidence": self.evidence,
            "affected_component": self.affected_component,
            "cve_id": self.cve_id,
            "cwe_id": self.cwe_id,
            "cvss_score": self.cvss_score,
            "remediation": self.remediation,
            "references": self.references,
            "timestamp": self.timestamp,
            "verified": self.verified,
            "retest_status": self.retest_status,
        }


class ScopeManager:
    """Manages testing scopes and authorization."""

    def __init__(self):
        self._scopes: dict[str, TestScope] = {}
        self._audit_log: list[dict] = []
        logger.info("[SCOPE_MANAGER] Initialized")

    def create_scope(self, name: str, targets: list[str], authorized_by: str,
                     **kwargs) -> TestScope:
        scope_id = str(uuid.uuid4())[:12]
        scope = TestScope(
            id=scope_id,
            name=name,
            targets=targets,
            authorized_by=authorized_by,
            authorization_status=AuthorizationStatus.AUTHORIZED,
            excluded_targets=kwargs.get('excluded_targets', []),
            allowed_ports=kwargs.get('allowed_ports', []),
            excluded_ports=kwargs.get('excluded_ports', []),
            test_types=kwargs.get('test_types', []),
            end_time=kwargs.get('end_time', 0.0),
            mode=kwargs.get('mode', TestMode.SAFE),
        )
        self._scopes[scope_id] = scope
        self._audit("scope_created", {"scope_id": scope_id, "name": name, "targets": targets})
        logger.info(f"[SCOPE_MANAGER] Created scope: {name} ({scope_id})")
        return scope

    def get_scope(self, scope_id: str) -> Optional[TestScope]:
        return self._scopes.get(scope_id)

    def get_active_scopes(self) -> list[TestScope]:
        return [s for s in self._scopes.values() if s.is_active()]

    def authorize_scope(self, scope_id: str, authorized_by: str) -> bool:
        scope = self._scopes.get(scope_id)
        if not scope:
            return False
        scope.authorization_status = AuthorizationStatus.AUTHORIZED
        scope.authorized_by = authorized_by
        self._audit("scope_authorized", {"scope_id": scope_id, "authorized_by": authorized_by})
        logger.info(f"[SCOPE_MANAGER] Scope {scope_id} authorized by {authorized_by}")
        return True

    def revoke_scope(self, scope_id: str, reason: str = "") -> bool:
        scope = self._scopes.get(scope_id)
        if not scope:
            return False
        scope.authorization_status = AuthorizationStatus.DENIED
        self._audit("scope_revoked", {"scope_id": scope_id, "reason": reason})
        logger.info(f"[SCOPE_MANAGER] Scope {scope_id} revoked: {reason}")
        return True

    def verify_target(self, target: str) -> Optional[TestScope]:
        for scope in self._scopes.values():
            if scope.is_active() and scope.is_target_authorized(target):
                return scope
        return None

    def _audit(self, action: str, details: dict):
        self._audit_log.append({
            "timestamp": time.time(),
            "action": action,
            "details": details,
        })
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        return self._audit_log[-limit:]


class SafetyController:
    """Enforces safety controls and prevents unauthorized actions."""

    RESTRICTED_OPERATIONS = {
        "credential_theft", "malware_deployment", "persistence",
        "data_destruction", "system_damage", "unauthorized_access",
    }

    def __init__(self, scope_manager: ScopeManager):
        self.scope_manager = scope_manager
        self._rate_limits: dict[str, list[float]] = {}
        self._blocked_actions: list[dict] = []
        logger.info("[SAFETY_CONTROLLER] Initialized with strict controls")

    def verify_authorization(self, target: str, operation: str,
                             scope_id: Optional[str] = None) -> tuple[bool, str]:
        if operation in self.RESTRICTED_OPERATIONS:
            self._blocked_actions.append({
                "timestamp": time.time(),
                "target": target,
                "operation": operation,
                "reason": "Restricted operation",
            })
            return False, f"Operation '{operation}' is restricted and not allowed"

        if scope_id:
            scope = self.scope_manager.get_scope(scope_id)
            if not scope:
                return False, f"Scope {scope_id} not found"
            if not scope.is_active():
                return False, f"Scope {scope_id} is not active or expired"
            if not scope.is_target_authorized(target):
                return False, f"Target {target} is not within authorized scope"
        else:
            scope = self.scope_manager.verify_target(target)
            if not scope:
                return False, f"No active authorization for target {target}"

        return True, "Authorized"

    def check_rate_limit(self, target: str, operation: str,
                         max_requests: int = 100, window_seconds: int = 60) -> bool:
        key = f"{target}:{operation}"
        now = time.time()

        if key not in self._rate_limits:
            self._rate_limits[key] = []

        self._rate_limits[key] = [t for t in self._rate_limits[key]
                                   if now - t < window_seconds]

        if len(self._rate_limits[key]) >= max_requests:
            logger.warning(f"[SAFETY] Rate limit exceeded: {key}")
            return False

        self._rate_limits[key].append(now)
        return True

    def validate_safe_mode(self, scope_id: str) -> bool:
        scope = self.scope_manager.get_scope(scope_id)
        if not scope:
            return False
        return scope.mode in [TestMode.SAFE, TestMode.READ_ONLY]

    def require_confirmation(self, operation: str, severity: str) -> bool:
        if severity in ["critical", "high"]:
            return True
        if operation in ["exploit_validation", "intrusive_test"]:
            return True
        return False

    def get_blocked_actions(self, limit: int = 50) -> list[dict]:
        return self._blocked_actions[-limit:]


class EthicalHackingEngine:
    """Main engine for ethical hacking operations."""

    def __init__(self):
        self.scope_manager = ScopeManager()
        self.safety_controller = SafetyController(self.scope_manager)
        self._findings: list[SecurityFinding] = []
        self._test_sessions: list[dict] = []
        logger.info("[ETHICAL_HACKING] Engine initialized with safety controls")

    def create_test_scope(self, name: str, targets: list[str],
                          authorized_by: str, **kwargs) -> dict:
        scope = self.scope_manager.create_scope(name, targets, authorized_by, **kwargs)
        return scope.to_dict()

    def get_scope(self, scope_id: str) -> Optional[dict]:
        scope = self.scope_manager.get_scope(scope_id)
        return scope.to_dict() if scope else None

    def get_active_scopes(self) -> list[dict]:
        return [s.to_dict() for s in self.scope_manager.get_active_scopes()]

    def add_finding(self, finding_type: str, severity: str, title: str,
                    description: str, target: str, scope_id: str,
                    **kwargs) -> dict:
        finding = SecurityFinding(
            id="",
            finding_type=finding_type,
            severity=Severity(severity),
            title=title,
            description=description,
            target=target,
            scope_id=scope_id,
            evidence=kwargs.get('evidence', {}),
            affected_component=kwargs.get('affected_component', ''),
            cve_id=kwargs.get('cve_id'),
            cwe_id=kwargs.get('cwe_id'),
            cvss_score=kwargs.get('cvss_score'),
            remediation=kwargs.get('remediation', ''),
            references=kwargs.get('references', []),
        )
        self._findings.append(finding)
        logger.info(f"[ETHICAL_HACKING] Finding added: {title} ({severity})")
        return finding.to_dict()

    def get_findings(self, scope_id: Optional[str] = None,
                     severity: Optional[str] = None,
                     limit: int = 100) -> list[dict]:
        findings = self._findings
        if scope_id:
            findings = [f for f in findings if f.scope_id == scope_id]
        if severity:
            findings = [f for f in findings if f.severity.value == severity]
        return [f.to_dict() for f in findings[-limit:]]

    def get_finding(self, finding_id: str) -> Optional[dict]:
        for finding in self._findings:
            if finding.id == finding_id:
                return finding.to_dict()
        return None

    def get_stats(self) -> dict:
        total_findings = len(self._findings)
        by_severity = {}
        for finding in self._findings:
            sev = finding.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1

        return {
            "total_findings": total_findings,
            "findings_by_severity": by_severity,
            "active_scopes": len(self.scope_manager.get_active_scopes()),
            "blocked_actions": len(self.safety_controller.get_blocked_actions()),
        }


_ethical_hacking_engine: Optional[EthicalHackingEngine] = None


def get_ethical_hacking_engine() -> EthicalHackingEngine:
    global _ethical_hacking_engine
    if _ethical_hacking_engine is None:
        _ethical_hacking_engine = EthicalHackingEngine()
    return _ethical_hacking_engine
