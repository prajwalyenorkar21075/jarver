"""
Security Alert Manager for JARVIS cybersecurity module.

Generates, manages, and routes structured security alerts:
- Alert generation from security findings
- Severity-based routing and escalation
- Alert deduplication
- Alert lifecycle management (active, acknowledged, resolved)
"""

import logging
import time
import json
from typing import Optional
from dataclasses import dataclass, field

from .security_db import get_security_db

logger = logging.getLogger(__name__)


@dataclass
class SecurityAlert:
    """Represents a security alert."""
    alert_id: str
    alert_type: str
    severity: str
    title: str
    description: str
    source: str
    timestamp: float
    affected_system: str = ""
    indicators: list = field(default_factory=list)
    recommended_actions: list = field(default_factory=list)
    status: str = "active"
    acknowledged: bool = False
    acknowledged_at: Optional[float] = None
    acknowledged_by: str = ""
    resolved_at: Optional[float] = None
    resolved_by: str = ""


ESCALATION_RULES = {
    "critical": {"auto_escalate": True, "notify_immediately": True, "response_time_minutes": 15},
    "high": {"auto_escalate": True, "notify_immediately": True, "response_time_minutes": 60},
    "medium": {"auto_escalate": False, "notify_immediately": False, "response_time_minutes": 240},
    "low": {"auto_escalate": False, "notify_immediately": False, "response_time_minutes": 1440},
}


class SecurityAlertManager:
    """Manages security alerts lifecycle."""

    def __init__(self):
        self.db = get_security_db()
        self.logger = logging.getLogger(__name__)
        self._alert_handlers = []
        self._dedup_window = 300

    def create_alert(self, alert_type: str, severity: str, title: str,
                      description: str = "", source: str = "",
                      affected_system: str = "", indicators: Optional[list] = None,
                      recommended_actions: Optional[list] = None) -> dict:
        """Create a new security alert."""
        alert_id = self.db.insert_alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            source=source,
            affected_system=affected_system,
            indicators=indicators or [],
            recommended_actions=recommended_actions or [],
        )

        if self._is_duplicate(alert_type, title, source):
            self.logger.info(f"[ALERT_MGR] Duplicate alert suppressed: {title}")
            return {"alert_id": alert_id, "status": "duplicate_suppressed"}

        self.db.insert_event(
            event_type="security_alert_created",
            severity=severity,
            description=f"Alert created: {title}",
            source="alert_manager",
            details={"alert_id": alert_id, "alert_type": alert_type}
        )

        escalation = ESCALATION_RULES.get(severity, {})
        if escalation.get("notify_immediately"):
            self.logger.warning(f"[ALERT_MGR] CRITICAL ALERT: {title} - {description}")

        for handler in self._alert_handlers:
            try:
                handler(alert_id, alert_type, severity, title)
            except Exception as e:
                self.logger.error(f"Error in alert handler: {e}")

        return {
            "alert_id": alert_id,
            "status": "created",
            "severity": severity,
            "auto_escalate": escalation.get("auto_escalate", False),
        }

    def _is_duplicate(self, alert_type: str, title: str, source: str) -> bool:
        """Check if this alert is a duplicate within the dedup window."""
        recent = self.db.get_active_alerts(limit=50)
        now = time.time()

        for alert in recent:
            if (alert.get("alert_type") == alert_type and
                alert.get("title") == title and
                alert.get("source") == source and
                now - alert.get("timestamp", 0) < self._dedup_window):
                return True

        return False

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> dict:
        """Acknowledge a security alert."""
        alerts = self.db.get_active_alerts(limit=200)
        target = None
        for alert in alerts:
            if alert.get("id") == alert_id:
                target = alert
                break

        if not target:
            return {"error": "Alert not found"}

        self.db.insert_event(
            event_type="alert_acknowledged",
            severity="info",
            description=f"Alert acknowledged: {target.get('title')}",
            source="alert_manager",
            details={"alert_id": alert_id, "acknowledged_by": acknowledged_by}
        )

        return {
            "alert_id": alert_id,
            "status": "acknowledged",
            "acknowledged_by": acknowledged_by,
        }

    def resolve_alert(self, alert_id: str, resolved_by: str,
                       resolution_notes: str = "") -> dict:
        """Resolve a security alert."""
        self.db.insert_event(
            event_type="alert_resolved",
            severity="info",
            description=f"Alert resolved: {alert_id}",
            source="alert_manager",
            details={"alert_id": alert_id, "resolved_by": resolved_by,
                     "notes": resolution_notes}
        )

        return {
            "alert_id": alert_id,
            "status": "resolved",
            "resolved_by": resolved_by,
        }

    def get_active_alerts(self, severity: Optional[str] = None,
                           limit: int = 50) -> list[dict]:
        """Get active security alerts."""
        alerts = self.db.get_active_alerts(limit=limit)

        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]

        return alerts

    def get_alert_summary(self) -> dict:
        """Get summary of all alerts."""
        alerts = self.db.get_active_alerts(limit=500)

        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        by_type = {}

        for alert in alerts:
            sev = alert.get("severity", "low")
            by_severity[sev] = by_severity.get(sev, 0) + 1

            atype = alert.get("alert_type", "unknown")
            by_type[atype] = by_type.get(atype, 0) + 1

        return {
            "total_active": len(alerts),
            "by_severity": by_severity,
            "by_type": by_type,
            "oldest_alert": min((a.get("timestamp", float('inf')) for a in alerts), default=0),
        }

    def generate_alerts_from_findings(self, findings: list[dict],
                                        source: str = "scan") -> list[dict]:
        """Generate alerts from security findings."""
        alerts = []

        for finding in findings:
            severity = finding.get("severity", "medium")
            if severity in ("critical", "high"):
                result = self.create_alert(
                    alert_type=finding.get("category", "security_finding"),
                    severity=severity,
                    title=finding.get("title", "Security Finding"),
                    description=finding.get("description", ""),
                    source=source,
                    affected_system=finding.get("affected_system", finding.get("affected_component", "")),
                    recommended_actions=[finding.get("remediation", "")],
                )
                alerts.append(result)

        return alerts

    def register_alert_handler(self, handler):
        """Register a callback for new alerts."""
        self._alert_handlers.append(handler)

    def get_alert_stats(self) -> dict:
        """Get alert statistics."""
        stats = self.db.get_security_stats()
        summary = self.get_alert_summary()

        return {
            **stats,
            "alert_summary": summary,
        }


_alert_manager: Optional[SecurityAlertManager] = None


def get_alert_manager() -> SecurityAlertManager:
    """Get singleton instance of SecurityAlertManager."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = SecurityAlertManager()
    return _alert_manager
