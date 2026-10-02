"""
Incident Response Engine for JARVIS cybersecurity module.

Provides safe incident response workflows:
- Incident creation and tracking
- Response action workflows
- Containment strategies (read-only by default)
- Timeline documentation
- Post-incident analysis
"""

import logging
import time
import json
from typing import Optional
from dataclasses import dataclass, field

from .security_db import get_security_db

logger = logging.getLogger(__name__)


INCIDENT_TYPES = {
    "malware_infection": {
        "severity": "critical",
        "response_priority": 1,
        "containment_actions": ["isolate_host", "block_network", "capture_forensics"],
    },
    "data_breach": {
        "severity": "critical",
        "response_priority": 1,
        "containment_actions": ["block_exfiltration", "revoke_credentials", "capture_forensics"],
    },
    "unauthorized_access": {
        "severity": "high",
        "response_priority": 2,
        "containment_actions": ["revoke_session", "reset_credentials", "audit_access"],
    },
    "denial_of_service": {
        "severity": "high",
        "response_priority": 2,
        "containment_actions": ["rate_limit", "block_source", "scale_resources"],
    },
    "vulnerability_exploit": {
        "severity": "high",
        "response_priority": 2,
        "containment_actions": ["patch_system", "block_exploit", "audit_systems"],
    },
    "insider_threat": {
        "severity": "high",
        "response_priority": 3,
        "containment_actions": ["restrict_access", "monitor_activity", "audit_logs"],
    },
    "policy_violation": {
        "severity": "medium",
        "response_priority": 4,
        "containment_actions": ["notify_admin", "document_evidence", "review_policy"],
    },
}


class IncidentResponseEngine:
    """Manages security incident response workflows."""

    def __init__(self):
        self.db = get_security_db()
        self.logger = logging.getLogger(__name__)

    def create_incident(self, incident_type: str, severity: str, title: str,
                         description: str = "", affected_systems: Optional[list] = None,
                         indicators: Optional[list] = None) -> dict:
        """Create a new security incident."""
        incident_id = self.db.insert_incident(
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
            affected_systems=affected_systems or [],
            indicators=indicators or [],
        )

        self._add_timeline_entry(incident_id, "incident_created",
                                  f"Incident created: {title}")

        type_info = INCIDENT_TYPES.get(incident_type, {})
        response_priority = type_info.get("response_priority", 5)

        self.logger.warning(
            f"[INCIDENT] {severity.upper()} incident created: {title} "
            f"(priority: {response_priority})"
        )

        return {
            "incident_id": incident_id,
            "status": "detected",
            "incident_type": incident_type,
            "severity": severity,
            "response_priority": response_priority,
            "recommended_containment": type_info.get("containment_actions", []),
        }

    def _add_timeline_entry(self, incident_id: str, action: str, description: str):
        """Add a timeline entry to an incident."""
        self.db.insert_event(
            event_type="incident_timeline",
            severity="info",
            description=f"[{incident_id}] {action}: {description}",
            source="incident_response",
            details={"incident_id": incident_id, "action": action, "description": description}
        )

    def update_incident_status(self, incident_id: str, new_status: str,
                                 updated_by: str) -> dict:
        """Update incident status."""
        valid_transitions = {
            "detected": ["investigating", "contained"],
            "investigating": ["contained", "eradicated"],
            "contained": ["eradicated", "investigating"],
            "eradicated": ["recovering"],
            "recovering": ["resolved"],
            "resolved": [],
        }

        self._add_timeline_entry(incident_id, "status_change",
                                  f"Status changed to {new_status} by {updated_by}")

        return {
            "incident_id": incident_id,
            "new_status": new_status,
            "updated_by": updated_by,
        }

    def add_response_action(self, incident_id: str, action: str,
                              actor: str, result: str = "",
                              details: Optional[dict] = None) -> dict:
        """Add a response action to incident timeline."""
        self._add_timeline_entry(
            incident_id, "response_action",
            f"Action: {action} by {actor} - Result: {result}"
        )

        return {
            "incident_id": incident_id,
            "action": action,
            "actor": actor,
            "result": result,
            "timestamp": time.time(),
        }

    def get_incident_details(self, incident_id: str) -> dict:
        """Get full incident details."""
        events = self.db.get_recent_events(limit=200)
        timeline = [
            e for e in events
            if e.get("details") and incident_id in str(e.get("details", ""))
        ]

        return {
            "incident_id": incident_id,
            "timeline": timeline,
        }

    def get_active_incidents(self) -> list[dict]:
        """Get all active incidents."""
        events = self.db.get_recent_events(limit=500)
        incidents = []

        incidents_raw = self.db._get_connection().__class__
        with self.db._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM incidents WHERE status != 'resolved'
                ORDER BY created_at DESC
            """).fetchall()

        return [dict(row) for row in rows]

    def get_incident_stats(self) -> dict:
        """Get incident statistics."""
        with self.db._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM incidents WHERE status != 'resolved'"
            ).fetchone()[0]
            by_severity = {}
            rows = conn.execute("""
                SELECT severity, COUNT(*) as cnt FROM incidents
                GROUP BY severity
            """).fetchall()
            for row in rows:
                by_severity[row["severity"]] = row["cnt"]

            by_type = {}
            rows = conn.execute("""
                SELECT incident_type, COUNT(*) as cnt FROM incidents
                GROUP BY incident_type
            """).fetchall()
            for row in rows:
                by_type[row["incident_type"]] = row["cnt"]

        return {
            "total_incidents": total,
            "active_incidents": active,
            "resolved_incidents": total - active,
            "by_severity": by_severity,
            "by_type": by_type,
        }

    def generate_post_mortem(self, incident_id: str) -> dict:
        """Generate post-incident analysis."""
        events = self.db.get_recent_events(limit=500)
        timeline = [
            e for e in events
            if e.get("details") and incident_id in str(e.get("details", ""))
        ]

        return {
            "incident_id": incident_id,
            "timeline_entries": len(timeline),
            "timeline": timeline,
            "generated_at": time.time(),
        }


_incident_engine: Optional[IncidentResponseEngine] = None


def get_incident_response_engine() -> IncidentResponseEngine:
    """Get singleton instance of IncidentResponseEngine."""
    global _incident_engine
    if _incident_engine is None:
        _incident_engine = IncidentResponseEngine()
    return _incident_engine
