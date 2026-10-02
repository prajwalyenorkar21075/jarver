"""
Security Evidence Collection and Penetration Testing Report Generation.

Collects comprehensive evidence for all findings and generates professional
penetration testing reports.
"""

import logging
import time
import json
from typing import Optional
from pathlib import Path
from datetime import datetime

from .core import get_ethical_hacking_engine, Severity

logger = logging.getLogger(__name__)


class EvidenceCollector:
    """Collects and manages security evidence."""

    def __init__(self):
        self.engine = get_ethical_hacking_engine()
        self._evidence_store: dict[str, list[dict]] = {}
        logger.info("[EVIDENCE] Evidence collector initialized")

    def collect_evidence(self, finding_id: str, evidence_type: str,
                         evidence_data: dict) -> dict:
        finding = self.engine.get_finding(finding_id)
        if not finding:
            return {"success": False, "error": "Finding not found"}

        evidence_entry = {
            "timestamp": time.time(),
            "evidence_type": evidence_type,
            "data": evidence_data,
            "collected_by": "ethical_hacking_engine",
        }

        if finding_id not in self._evidence_store:
            self._evidence_store[finding_id] = []

        self._evidence_store[finding_id].append(evidence_entry)

        logger.info(f"[EVIDENCE] Collected {evidence_type} evidence for finding {finding_id}")

        return {
            "success": True,
            "finding_id": finding_id,
            "evidence_type": evidence_type,
            "timestamp": evidence_entry["timestamp"],
        }

    def get_evidence(self, finding_id: str) -> list[dict]:
        return self._evidence_store.get(finding_id, [])

    def get_all_evidence(self, scope_id: Optional[str] = None) -> dict:
        findings = self.engine.get_findings(scope_id)
        evidence_map = {}

        for finding in findings:
            finding_id = finding["id"]
            evidence_map[finding_id] = {
                "finding": finding,
                "evidence": self._evidence_store.get(finding_id, []),
            }

        return evidence_map


class PenTestReportGenerator:
    """Generates professional penetration testing reports."""

    def __init__(self):
        self.engine = get_ethical_hacking_engine()
        self.evidence_collector = EvidenceCollector()
        logger.info("[REPORT] Penetration testing report generator initialized")

    def generate_report(self, scope_id: str, report_format: str = "json",
                        include_evidence: bool = True) -> dict:
        scope = self.engine.get_scope(scope_id)
        if not scope:
            return {"success": False, "error": "Scope not found"}

        findings = self.engine.get_findings(scope_id)

        report = {
            "report_metadata": {
                "report_id": f"pentest-{scope_id}-{int(time.time())}",
                "generated_at": datetime.now().isoformat(),
                "generated_by": "JARVIS Ethical Hacking Engine",
                "report_format": report_format,
            },
            "executive_summary": self._generate_executive_summary(findings, scope),
            "scope": {
                "scope_id": scope_id,
                "scope_name": scope["name"],
                "targets": scope["targets"],
                "excluded_targets": scope["excluded_targets"],
                "test_types": scope["test_types"],
                "start_time": scope["start_time"],
                "end_time": scope.get("end_time"),
                "authorized_by": scope["authorized_by"],
            },
            "methodology": self._generate_methodology(scope),
            "findings": self._generate_findings_section(findings, include_evidence),
            "severity_summary": self._generate_severity_summary(findings),
            "remediation_summary": self._generate_remediation_summary(findings),
            "recommendations": self._generate_recommendations(findings),
            "conclusion": self._generate_conclusion(findings, scope),
        }

        if report_format == "json":
            return {"success": True, "report": report}
        elif report_format == "html":
            html_report = self._convert_to_html(report)
            return {"success": True, "report": report, "html": html_report}
        elif report_format == "text":
            text_report = self._convert_to_text(report)
            return {"success": True, "report": report, "text": text_report}
        else:
            return {"success": True, "report": report}

    def _generate_executive_summary(self, findings: list[dict], scope: dict) -> dict:
        total = len(findings)
        by_severity = {}
        for finding in findings:
            sev = finding["severity"]
            by_severity[sev] = by_severity.get(sev, 0) + 1

        critical_high = by_severity.get("critical", 0) + by_severity.get("high", 0)

        if critical_high > 0:
            risk_level = "HIGH"
            summary = f"Testing identified {critical_high} critical/high severity vulnerabilities requiring immediate attention."
        elif total > 0:
            risk_level = "MEDIUM"
            summary = f"Testing identified {total} security issues of varying severity."
        else:
            risk_level = "LOW"
            summary = "No significant security issues identified during testing."

        return {
            "risk_level": risk_level,
            "summary": summary,
            "total_findings": total,
            "findings_by_severity": by_severity,
            "scope_name": scope["name"],
            "targets_count": len(scope["targets"]),
        }

    def _generate_methodology(self, scope: dict) -> dict:
        return {
            "approach": "Authorized penetration testing following industry best practices",
            "standards": [
                "OWASP Testing Guide",
                "PTES (Penetration Testing Execution Standard)",
                "NIST SP 800-115",
            ],
            "phases": [
                "Reconnaissance and asset discovery",
                "Vulnerability scanning and identification",
                "Manual verification and validation",
                "Risk assessment and prioritization",
                "Reporting and remediation guidance",
            ],
            "tools_used": [
                "JARVIS Ethical Hacking Engine",
                "Custom security assessment tools",
                "Network scanning utilities",
                "Web application security testers",
            ],
            "testing_mode": scope["mode"],
        }

    def _generate_findings_section(self, findings: list[dict], include_evidence: bool) -> list[dict]:
        findings_section = []

        for finding in findings:
            finding_entry = {
                "id": finding["id"],
                "title": finding["title"],
                "severity": finding["severity"],
                "description": finding["description"],
                "target": finding["target"],
                "affected_component": finding["affected_component"],
                "finding_type": finding["finding_type"],
            }

            if finding.get("cve_id"):
                finding_entry["cve_id"] = finding["cve_id"]
            if finding.get("cwe_id"):
                finding_entry["cwe_id"] = finding["cwe_id"]
            if finding.get("cvss_score"):
                finding_entry["cvss_score"] = finding["cvss_score"]

            finding_entry["remediation"] = finding.get("remediation", "")
            finding_entry["references"] = finding.get("references", [])

            if include_evidence:
                evidence = self.evidence_collector.get_evidence(finding["id"])
                if evidence:
                    finding_entry["evidence"] = evidence

            findings_section.append(finding_entry)

        return findings_section

    def _generate_severity_summary(self, findings: list[dict]) -> dict:
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for finding in findings:
            sev = finding["severity"]
            by_severity[sev] = by_severity.get(sev, 0) + 1

        return {
            "by_severity": by_severity,
            "total": len(findings),
            "critical_high": by_severity["critical"] + by_severity["high"],
        }

    def _generate_remediation_summary(self, findings: list[dict]) -> dict:
        remediations = {}
        for finding in findings:
            remediation = finding.get("remediation", "")
            if remediation:
                if remediation not in remediations:
                    remediations[remediation] = []
                remediations[remediation].append(finding["id"])

        return {
            "unique_remediations": len(remediations),
            "remediations": [
                {"remediation": rem, "finding_ids": ids}
                for rem, ids in remediations.items()
            ],
        }

    def _generate_recommendations(self, findings: list[dict]) -> list[str]:
        recommendations = []

        severity_counts = {}
        for finding in findings:
            sev = finding["severity"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if severity_counts.get("critical", 0) > 0:
            recommendations.append("Immediately address all critical severity vulnerabilities")
        if severity_counts.get("high", 0) > 0:
            recommendations.append("Prioritize remediation of high severity vulnerabilities")
        if any(f["finding_type"] == "missing_security_header" for f in findings):
            recommendations.append("Implement security headers across all web applications")
        if any(f["finding_type"] == "exposed_secret" for f in findings):
            recommendations.append("Remove all hardcoded secrets and implement secure secret management")
        if any(f["finding_type"] == "weak_password_policy" for f in findings):
            recommendations.append("Strengthen password policies to meet industry standards")

        if not recommendations:
            recommendations.append("Continue regular security assessments and monitoring")

        return recommendations

    def _generate_conclusion(self, findings: list[dict], scope: dict) -> dict:
        total = len(findings)
        critical_high = sum(1 for f in findings if f["severity"] in ["critical", "high"])

        if critical_high > 0:
            overall_risk = "HIGH"
            conclusion = f"The assessment identified {critical_high} critical/high severity vulnerabilities that pose significant risk. Immediate remediation is strongly recommended."
        elif total > 0:
            overall_risk = "MEDIUM"
            conclusion = f"The assessment identified {total} security issues. While no critical vulnerabilities were found, remediation of identified issues is recommended to improve security posture."
        else:
            overall_risk = "LOW"
            conclusion = "The assessment did not identify significant security vulnerabilities. Continue regular security assessments to maintain security posture."

        return {
            "overall_risk": overall_risk,
            "conclusion": conclusion,
            "next_steps": [
                "Review and prioritize findings",
                "Implement remediation plan",
                "Schedule retest after remediation",
                "Continue regular security assessments",
            ],
        }

    def _convert_to_html(self, report: dict) -> str:
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Penetration Testing Report - {report['scope']['scope_name']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        .severity-critical {{ color: #d9534f; font-weight: bold; }}
        .severity-high {{ color: #f0ad4e; font-weight: bold; }}
        .severity-medium {{ color: #5bc0de; }}
        .severity-low {{ color: #5cb85c; }}
        .finding {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <h1>Penetration Testing Report</h1>
    <p><strong>Report ID:</strong> {report['report_metadata']['report_id']}</p>
    <p><strong>Generated:</strong> {report['report_metadata']['generated_at']}</p>

    <h2>Executive Summary</h2>
    <p><strong>Overall Risk Level:</strong> <span class="severity-{report['executive_summary']['risk_level'].lower()}">{report['executive_summary']['risk_level']}</span></p>
    <p>{report['executive_summary']['summary']}</p>
    <p><strong>Total Findings:</strong> {report['executive_summary']['total_findings']}</p>

    <h2>Scope</h2>
    <p><strong>Scope Name:</strong> {report['scope']['scope_name']}</p>
    <p><strong>Targets:</strong> {', '.join(report['scope']['targets'])}</p>
    <p><strong>Authorized By:</strong> {report['scope']['authorized_by']}</p>

    <h2>Findings</h2>
"""
        for finding in report['findings']:
            html += f"""
    <div class="finding">
        <h3>{finding['title']}</h3>
        <p><strong>Severity:</strong> <span class="severity-{finding['severity']}">{finding['severity'].upper()}</span></p>
        <p><strong>Target:</strong> {finding['target']}</p>
        <p><strong>Description:</strong> {finding['description']}</p>
        <p><strong>Remediation:</strong> {finding.get('remediation', 'N/A')}</p>
    </div>
"""
        html += """
</body>
</html>
"""
        return html

    def _convert_to_text(self, report: dict) -> str:
        text = f"""
PENETRATION TESTING REPORT
==========================

Report ID: {report['report_metadata']['report_id']}
Generated: {report['report_metadata']['generated_at']}

EXECUTIVE SUMMARY
-----------------
Overall Risk Level: {report['executive_summary']['risk_level']}
{report['executive_summary']['summary']}
Total Findings: {report['executive_summary']['total_findings']}

SCOPE
-----
Scope Name: {report['scope']['scope_name']}
Targets: {', '.join(report['scope']['targets'])}
Authorized By: {report['scope']['authorized_by']}

FINDINGS
--------
"""
        for i, finding in enumerate(report['findings'], 1):
            text += f"""
{i}. {finding['title']}
   Severity: {finding['severity'].upper()}
   Target: {finding['target']}
   Description: {finding['description']}
   Remediation: {finding.get('remediation', 'N/A')}
"""

        text += f"""
RECOMMENDATIONS
---------------
"""
        for i, rec in enumerate(report['recommendations'], 1):
            text += f"{i}. {rec}\n"

        text += f"""
CONCLUSION
----------
Overall Risk: {report['conclusion']['overall_risk']}
{report['conclusion']['conclusion']}
"""
        return text


_evidence_collector: Optional[EvidenceCollector] = None
_report_generator: Optional[PenTestReportGenerator] = None


def get_evidence_collector() -> EvidenceCollector:
    global _evidence_collector
    if _evidence_collector is None:
        _evidence_collector = EvidenceCollector()
    return _evidence_collector


def get_report_generator() -> PenTestReportGenerator:
    global _report_generator
    if _report_generator is None:
        _report_generator = PenTestReportGenerator()
    return _report_generator
