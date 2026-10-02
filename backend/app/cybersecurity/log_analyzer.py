"""
Log Analysis Engine for JARVIS cybersecurity module.

Analyzes various logs for suspicious activity:
- Windows Event Logs (security, system, application)
- Authentication logs
- Application logs
- Network logs
- Custom log files
"""

import subprocess
import re
import logging
import time
from typing import Optional
from pathlib import Path

from .security_db import get_security_db

logger = logging.getLogger(__name__)


SUSPICIOUS_EVENT_IDS = {
    "windows_security": {
        4625: {"description": "Failed logon attempt", "severity": "medium"},
        4624: {"description": "Successful logon", "severity": "info"},
        4672: {"description": "Special privileges assigned", "severity": "medium"},
        4720: {"description": "User account created", "severity": "high"},
        4722: {"description": "User account enabled", "severity": "medium"},
        4724: {"description": "Password reset attempted", "severity": "high"},
        4732: {"description": "Member added to security-enabled local group", "severity": "high"},
        4738: {"description": "User account changed", "severity": "medium"},
        4756: {"description": "Member added to universal group", "severity": "high"},
        4698: {"description": "Scheduled task created", "severity": "medium"},
        4699: {"description": "Scheduled task deleted", "severity": "medium"},
        4702: {"description": "Scheduled task updated", "severity": "medium"},
        1102: {"description": "Audit log cleared", "severity": "critical"},
    },
    "windows_system": {
        7045: {"description": "New service installed", "severity": "high"},
        6005: {"description": "Event Log service started (system boot)", "severity": "info"},
        6006: {"description": "Event Log service stopped (system shutdown)", "severity": "info"},
        6008: {"description": "Unexpected shutdown", "severity": "high"},
        41: {"description": "Unexpected shutdown (Kernel-Power)", "severity": "high"},
    },
}

SUSPICIOUS_LOG_PATTERNS = [
    (r"(?:failed|invalid|unauthorized|denied)\s+(?:login|logon|auth)", "Authentication failure", "medium"),
    (r"(?:error|exception|critical|fatal)", "Error/exception detected", "low"),
    (r"(?:brute\s*force|multiple\s+failed)", "Possible brute force attack", "high"),
    (r"(?:injection|XSS|CSRF|overflow)", "Possible attack attempt", "high"),
    (r"(?:malware|virus|trojan|ransomware)", "Malware reference detected", "critical"),
    (r"(?:privilege\s+escalation|root|admin\s+access)", "Privilege escalation attempt", "high"),
    (r"(?:suspicious|anomalous|unusual)", "Anomalous activity detected", "medium"),
    (r"(?:port\s*scan|reconnaissance|enumeration)", "Reconnaissance activity", "high"),
    (r"(?:exfiltrat|data\s+leak|unauthorized\s+transfer)", "Possible data exfiltration", "critical"),
    (r"(?:backdoor|reverse\s+shell|C2|command\s+and\s+control)", "Backdoor/C2 activity", "critical"),
]


class LogAnalysisEngine:
    """Analyzes system and application logs for suspicious activity."""

    def __init__(self):
        self.db = get_security_db()
        self.logger = logging.getLogger(__name__)

    def analyze_windows_security_log(self, max_events: int = 100) -> list[dict]:
        """Analyze Windows Security event log."""
        findings = []

        try:
            result = subprocess.run(
                ["wevtutil", "qe", "Security", f"/c:{max_events}", "/f:text"],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                events = result.stdout.split("\n\n")
                for event_text in events:
                    event_id_match = re.search(r'Event ID:\s*(\d+)', event_text)
                    if event_id_match:
                        event_id = int(event_id_match.group(1))
                        if event_id in SUSPICIOUS_EVENT_IDS.get("windows_security", {}):
                            info = SUSPICIOUS_EVENT_IDS["windows_security"][event_id]

                            time_match = re.search(r'Date:\s*(.+)', event_text)
                            timestamp = time_match.group(1).strip() if time_match else ""

                            findings.append({
                                "source": "windows_security",
                                "event_id": event_id,
                                "description": info["description"],
                                "severity": info["severity"],
                                "timestamp": timestamp,
                                "category": "suspicious_event",
                            })

        except Exception as e:
            self.logger.error(f"Error analyzing Windows Security log: {e}")

        return findings

    def analyze_windows_system_log(self, max_events: int = 100) -> list[dict]:
        """Analyze Windows System event log."""
        findings = []

        try:
            result = subprocess.run(
                ["wevtutil", "qe", "System", f"/c:{max_events}", "/f:text"],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                events = result.stdout.split("\n\n")
                for event_text in events:
                    event_id_match = re.search(r'Event ID:\s*(\d+)', event_text)
                    if event_id_match:
                        event_id = int(event_id_match.group(1))
                        if event_id in SUSPICIOUS_EVENT_IDS.get("windows_system", {}):
                            info = SUSPICIOUS_EVENT_IDS["windows_system"][event_id]

                            time_match = re.search(r'Date:\s*(.+)', event_text)
                            timestamp = time_match.group(1).strip() if time_match else ""

                            findings.append({
                                "source": "windows_system",
                                "event_id": event_id,
                                "description": info["description"],
                                "severity": info["severity"],
                                "timestamp": timestamp,
                                "category": "suspicious_event",
                            })

        except Exception as e:
            self.logger.error(f"Error analyzing Windows System log: {e}")

        return findings

    def analyze_log_file(self, file_path: str, max_lines: int = 1000) -> list[dict]:
        """Analyze a custom log file for suspicious patterns."""
        findings = []
        path = Path(file_path)

        if not path.exists():
            self.logger.warning(f"Log file not found: {file_path}")
            return findings

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)

            for line_num, line in enumerate(lines, 1):
                for pattern, description, severity in SUSPICIOUS_LOG_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append({
                            "source": file_path,
                            "line_number": line_num,
                            "description": description,
                            "severity": severity,
                            "pattern_matched": pattern,
                            "log_excerpt": line.strip()[:200],
                            "category": "suspicious_log_entry",
                        })

        except Exception as e:
            self.logger.error(f"Error analyzing log file {file_path}: {e}")

        return findings

    def detect_brute_force(self, auth_events: list[dict], threshold: int = 5,
                            time_window: int = 300) -> list[dict]:
        """Detect potential brute force attacks from authentication events."""
        findings = []

        failed_by_source = {}
        for event in auth_events:
            if "failed" in event.get("description", "").lower() or event.get("event_id") == 4625:
                source = event.get("source_ip", event.get("source", "unknown"))
                if source not in failed_by_source:
                    failed_by_source[source] = []
                failed_by_source[source].append(event)

        for source, events in failed_by_source.items():
            if len(events) >= threshold:
                findings.append({
                    "title": f"Potential brute force attack from {source}",
                    "severity": "high",
                    "category": "brute_force",
                    "description": f"{len(events)} failed authentication attempts from {source}",
                    "source": source,
                    "attempt_count": len(events),
                    "remediation": f"Block or rate-limit access from {source}",
                })

        return findings

    def comprehensive_log_analysis(self, log_paths: Optional[list] = None) -> dict:
        """Run comprehensive log analysis."""
        self.logger.info("[LOG_ANALYZER] Starting comprehensive log analysis")

        all_findings = []

        all_findings.extend(self.analyze_windows_security_log())
        all_findings.extend(self.analyze_windows_system_log())

        if log_paths:
            for log_path in log_paths:
                all_findings.extend(self.analyze_log_file(log_path))

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        source_counts = {}

        for finding in all_findings:
            severity = finding.get("severity", "info")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            source = finding.get("source", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1

        for finding in all_findings:
            self.db.insert_event(
                event_type="log_analysis_finding",
                severity=finding.get("severity", "info"),
                description=finding.get("description", ""),
                source=finding.get("source", "log_analyzer"),
                details=finding
            )

        scan_result = {
            "total": len(all_findings),
            "critical": severity_counts["critical"],
            "high": severity_counts["high"],
            "medium": severity_counts["medium"],
            "low": severity_counts["low"],
            "info": severity_counts["info"],
            "by_source": source_counts,
            "findings": all_findings,
            "analysis_time": time.time(),
        }

        scan_id = self.db.insert_scan_result(
            scan_type="log_analysis",
            target="system_logs",
            status="completed",
            findings=scan_result
        )

        self.logger.info(f"[LOG_ANALYZER] Analysis complete: {len(all_findings)} findings")

        return {
            "scan_id": scan_id,
            "result": scan_result,
        }


_log_analyzer: Optional[LogAnalysisEngine] = None


def get_log_analyzer() -> LogAnalysisEngine:
    """Get singleton instance of LogAnalysisEngine."""
    global _log_analyzer
    if _log_analyzer is None:
        _log_analyzer = LogAnalysisEngine()
    return _log_analyzer
