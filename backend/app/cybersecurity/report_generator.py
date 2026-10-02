"""
Security Report Generator for JARVIS cybersecurity module.

Generates readable security reports:
- Executive summary reports
- Detailed technical findings reports
- Compliance reports
- Trend analysis reports
"""

import json
import logging
import time
from typing import Optional
from pathlib import Path
from datetime import datetime

from .security_db import get_security_db

logger = logging.getLogger(__name__)


class SecurityReportGenerator:
    """Generates security reports."""

    def __init__(self):
        self.db = get_security_db()
        self.logger = logging.getLogger(__name__)

    def generate_executive_summary(self, title: str = "Security Executive Summary") -> dict:
        """Generate executive-level security summary."""
        stats = self.db.get_security_stats()
        alerts = self.db.get_active_alerts(limit=20)

        critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
        high_alerts = [a for a in alerts if a.get("severity") == "high"]

        report = {
            "title": title,
            "generated_at": time.time(),
            "generated_at_readable": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "executive_summary": {
                "overall_security_posture": self._assess_posture(stats),
                "total_events": stats.get("total_events", 0),
                "active_alerts": stats.get("active_alerts", 0),
                "open_vulnerabilities": stats.get("open_vulnerabilities", 0),
                "active_incidents": stats.get("active_incidents", 0),
            },
            "critical_items": {
                "critical_alerts": len(critical_alerts),
                "high_alerts": len(high_alerts),
                "critical_alert_details": [
                    {"title": a.get("title"), "type": a.get("alert_type")}
                    for a in critical_alerts[:5]
                ],
            },
            "recommendations": self._generate_recommendations(stats),
        }

        report_id = self.db._generate_id() if hasattr(self.db, '_generate_id') else str(int(time.time()))
        with self.db._get_connection() as conn:
            conn.execute("""
                INSERT INTO security_reports
                (id, report_type, generated_at, title, summary, findings, recommendations, metrics, format)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (report_id, "executive_summary", time.time(), title,
                  json.dumps(report.get("executive_summary", {})),
                  json.dumps(report.get("critical_items", {})),
                  json.dumps(report.get("recommendations", [])),
                  json.dumps(stats), "json"))

        report["report_id"] = report_id
        return report

    def _assess_posture(self, stats: dict) -> str:
        """Assess overall security posture."""
        critical = stats.get("critical_alerts", 0)
        high_vulns = stats.get("high_severity_vulns", 0)
        active_incidents = stats.get("active_incidents", 0)

        if critical > 0 or active_incidents > 0:
            return "CRITICAL - Immediate action required"
        elif high_vulns > 3:
            return "AT RISK - Significant issues need attention"
        elif high_vulns > 0:
            return "MODERATE - Some issues to address"
        else:
            return "GOOD - Security posture is acceptable"

    def _generate_recommendations(self, stats: dict) -> list[str]:
        """Generate recommendations based on stats."""
        recommendations = []

        if stats.get("critical_alerts", 0) > 0:
            recommendations.append("URGENT: Address all critical alerts immediately")

        if stats.get("open_vulnerabilities", 0) > 0:
            recommendations.append("Patch all open vulnerabilities, prioritizing critical and high severity")

        if stats.get("active_incidents", 0) > 0:
            recommendations.append("Investigate and resolve all active security incidents")

        if stats.get("active_alerts", 0) > 10:
            recommendations.append("Review and triage active alerts - consider adjusting detection rules")

        if not recommendations:
            recommendations.append("Continue monitoring and maintain current security practices")

        return recommendations

    def generate_technical_report(self, scan_id: Optional[str] = None,
                                    scan_type: Optional[str] = None) -> dict:
        """Generate detailed technical findings report."""
        with self.db._get_connection() as conn:
            if scan_id:
                rows = conn.execute(
                    "SELECT * FROM scan_results WHERE id = ?", (scan_id,)
                ).fetchall()
            elif scan_type:
                rows = conn.execute(
                    "SELECT * FROM scan_results WHERE scan_type = ? ORDER BY timestamp DESC LIMIT 10",
                    (scan_type,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM scan_results ORDER BY timestamp DESC LIMIT 20"
                ).fetchall()

        scans = [dict(row) for row in rows]

        vulns = []
        with self.db._get_connection() as conn:
            vuln_rows = conn.execute(
                "SELECT * FROM vulnerabilities WHERE status = 'open' ORDER BY discovered_at DESC LIMIT 50"
            ).fetchall()
            vulns = [dict(row) for row in vuln_rows]

        report = {
            "title": "Technical Security Report",
            "generated_at": time.time(),
            "generated_at_readable": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scan_results": scans,
            "open_vulnerabilities": vulns,
            "total_scans": len(scans),
            "total_vulnerabilities": len(vulns),
        }

        return report

    def generate_compliance_report(self, framework: str = "OWASP") -> dict:
        """Generate compliance report for a specific framework."""
        stats = self.db.get_security_stats()

        if framework.upper() == "OWASP":
            from .knowledge_base import OWASP_TOP_10_2021
            compliance_items = {}
            for cat_id, cat_info in OWASP_TOP_10_2021.items():
                compliance_items[cat_id] = {
                    "title": cat_info["title"],
                    "status": "needs_verification",
                    "findings": [],
                }

            report = {
                "title": f"Compliance Report: {framework}",
                "framework": framework,
                "generated_at": time.time(),
                "categories": compliance_items,
                "total_categories": len(compliance_items),
                "compliant": 0,
                "non_compliant": 0,
                "needs_verification": len(compliance_items),
            }
        else:
            report = {
                "title": f"Compliance Report: {framework}",
                "framework": framework,
                "generated_at": time.time(),
                "error": f"Framework {framework} not yet supported",
            }

        return report

    def generate_trend_report(self, days: int = 30) -> dict:
        """Generate trend analysis report."""
        cutoff = time.time() - (days * 86400)

        with self.db._get_connection() as conn:
            events_by_day = conn.execute("""
                SELECT DATE(timestamp, 'unixepoch') as day,
                       COUNT(*) as count,
                       severity
                FROM security_events
                WHERE timestamp > ?
                GROUP BY day, severity
                ORDER BY day
            """, (cutoff,)).fetchall()

            alerts_by_day = conn.execute("""
                SELECT DATE(timestamp, 'unixepoch') as day,
                       COUNT(*) as count,
                       severity
                FROM security_alerts
                WHERE timestamp > ?
                GROUP BY day, severity
                ORDER BY day
            """, (cutoff,)).fetchall()

        report = {
            "title": f"Security Trend Report ({days} days)",
            "period_days": days,
            "generated_at": time.time(),
            "events_by_day": [dict(row) for row in events_by_day],
            "alerts_by_day": [dict(row) for row in alerts_by_day],
        }

        return report

    def generate_report(self, report_type: str = "executive_summary",
                          **kwargs) -> dict:
        """Generate a security report of the specified type."""
        generators = {
            "executive_summary": self.generate_executive_summary,
            "technical": self.generate_technical_report,
            "compliance": self.generate_compliance_report,
            "trend": self.generate_trend_report,
        }

        generator = generators.get(report_type)
        if not generator:
            return {"error": f"Unknown report type: {report_type}"}

        return generator(**kwargs)


_report_generator: Optional[SecurityReportGenerator] = None


def get_report_generator() -> SecurityReportGenerator:
    """Get singleton instance of SecurityReportGenerator."""
    global _report_generator
    if _report_generator is None:
        _report_generator = SecurityReportGenerator()
    return _report_generator
