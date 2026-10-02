"""
Voice command handler for Cybersecurity module.

Parses voice commands in English, Hindi, and Marathi and routes them
to the cybersecurity API endpoints.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


COMMAND_PATTERNS = {
    "threat_scan": [
        r"(?:run|start|perform|execute)?\s*(?:threat\s*(?:detection|scan|analysis))",
        r"(?:detect|find|check)\s*(?:threats?|suspicious\s*(?:activity|process|behavior))",
        r"(?:check|scan|run)\s*(?:for\s*)?threats?",
        r"(?:सुरक्षा|threat)\s*(?:scan|check|जांच|तपासणी)",
    ],
    "endpoint_check": [
        r"(?:run|start|perform|execute)?\s*(?:endpoint\s*(?:security|check|scan))",
        r"(?:check|scan|monitor)\s*(?:endpoint|windows\s*security|system\s*security)",
        r"(?:monitor|check)\s*(?:endpoints?)",
    ],
    "network_check": [
        r"(?:run|start|perform|execute)?\s*(?:network\s*(?:security|check|scan|monitor))",
        r"(?:check|scan|monitor)\s*(?:network|ports?|connections?|listening)",
        r"(?:scan|check)\s*(?:my\s*)?network",
        r"(?:नेटवर्क|network)\s*(?:सुरक्षा|security|check|scan)",
    ],
    "vulnerability_scan": [
        r"(?:run|start|perform|execute)?\s*(?:vulnerability\s*(?:scan|assessment))",
        r"(?:scan|check|find)\s*(?:vulnerabilit(?:y|ies)|weakness(?:es)?|missing\s*patches?)",
        r"(?:check|scan)\s*(?:for\s*)?vulnerabilit(?:y|ies)",
    ],
    "web_security": [
        r"(?:run|start|perform|execute)?\s*(?:web\s*(?:security|application)\s*(?:scan|analysis|test|check))",
        r"(?:analyze|check|scan|test)\s*(?:web\s*(?:application|app|security))",
    ],
    "code_scan": [
        r"(?:run|start|perform|execute)?\s*(?:code\s*(?:security|scan|analysis))",
        r"(?:scan|check|analyze)\s*(?:source\s*code|code\s*(?:for\s*)?security|code\s*(?:for\s*)?vulnerabilities)",
    ],
    "dependency_scan": [
        r"(?:run|start|perform|execute)?\s*(?:dependency\s*(?:scan|check))",
        r"(?:scan|check)\s*(?:dependencies?|packages?|npm|pip)\s*(?:for\s*)?(?:vulnerabilities?|security)",
    ],
    "integrity_check": [
        r"(?:run|start|perform|execute)?\s*(?:file\s*integrity\s*(?:check|monitor|scan|baseline))",
        r"(?:check|monitor|verify)\s*(?:file\s*integrity|integrity\s*(?:of\s*)?files?)",
        r"(?:create|make|set)\s*(?:integrity\s*)?baseline",
    ],
    "malware_analysis": [
        r"(?:run|start|perform|execute)?\s*(?:malware\s*(?:analysis|scan|check))",
        r"(?:analyze|check|scan)\s*(?:file|suspicious\s*file)\s*(?:for\s*)?(?:malware|threats?)",
    ],
    "log_analysis": [
        r"(?:run|start|perform|execute)?\s*(?:log\s*(?:analysis|scan|check))",
        r"(?:analyze|check|scan)\s*(?:logs?|event\s*logs?|security\s*logs?)",
    ],
    "secret_scan": [
        r"(?:run|start|perform|execute)?\s*(?:secret\s*(?:scan|check))",
        r"(?:scan|check|find|detect)\s*(?:exposed\s*)?(?:secrets?|credentials?|api\s*keys?|passwords?)",
        r"(?:scan|check)\s*(?:for\s*)?(?:exposed\s*)?secrets?",
    ],
    "database_audit": [
        r"(?:run|start|perform|execute)?\s*(?:database\s*(?:security|audit|check))",
        r"(?:audit|check|scan)\s*(?:database|db)\s*(?:security|configuration)",
    ],
    "privacy_scan": [
        r"(?:run|start|perform|execute)?\s*(?:privacy\s*(?:scan|check))",
        r"(?:scan|check|find|detect)\s*(?:pii|personal\s*data|data\s*exposure|privacy\s*issues?)",
        r"(?:redact|mask|hide)\s*(?:sensitive\s*)?(?:data|information|text)",
    ],
    "get_alerts": [
        r"(?:show|get|display|list)\s*(?:active\s*)?(?:security\s*)?alerts?",
        r"(?:any\s*)?(?:alerts?|warnings?|notifications?)\s*(?:found|detected|active)?",
    ],
    "get_status": [
        r"(?:show|get|what(?:'s|is)\s*(?:the)?)\s*(?:cyber)?security\s*(?:status|stats|overview|dashboard|summary)",
        r"(?:show|get)\s*(?:security\s*)?(?:dashboard|overview|stats|summary)",
        r"(?:cyber\s*security|security)\s*(?:status|stats|overview|dashboard)",
        r"(?:run\s*)?(?:a\s*)?(?:security|cyber)\s*scan",
    ],
    "full_scan": [
        r"(?:run|start|perform|execute)\s*(?:full|comprehensive|complete|all)\s*(?:security\s*)?scan",
        r"(?:run|start|perform)\s*(?:all\s*)?security\s*(?:checks?|scans?)",
        r"(?:comprehensive|full)\s*(?:security|cybersecurity)\s*(?:scan|check|assessment)",
    ],
    "generate_report": [
        r"(?:generate|create|make)\s*(?:security|cybersecurity)\s*report",
        r"(?:security|cyber)\s*report\s*(?:generate|create|make)",
        r"(?:executive|technical|compliance|trend)\s*(?:security\s*)?report",
    ],
    "create_incident": [
        r"(?:create|report|log)\s*(?:security\s*)?incident",
        r"(?:report|log)\s*(?:a\s*)?(?:security\s*)?(?:breach|incident|issue)",
    ],
    "backup_verify": [
        r"(?:verify|check)\s*(?:backup|backups?)\s*(?:security|integrity|freshness)?",
        r"(?:backup|backups?)\s*(?:verify|check|integrity|security)",
    ],
    "knowledge_query": [
        r"(?:show|get|tell\s*me)\s*(?:about\s*)?(?:owasp|cwe|cve|security\s*knowledge)",
        r"(?:what\s*is|explain)\s*(?:owasp|cwe|cve)",
        r"(?:search|find)\s*(?:security\s*)?knowledge",
    ],
}


def parse_cybersecurity_command(text: str) -> Optional[dict]:
    """Parse cybersecurity voice command."""
    text_lower = text.lower().strip()

    for command, patterns in COMMAND_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                target = None
                groups = match.groups()
                if groups:
                    for g in groups:
                        if g and len(g.strip()) > 2:
                            target = g.strip()
                            break

                return {
                    "command": command,
                    "target": target,
                    "raw_text": text,
                }

    if re.search(r"\b(cyber\s*security|cybersecurity|defensive\s*security|security\s*(?:scan|check|monitor|dashboard))\b", text_lower, re.IGNORECASE):
        return {
            "command": "get_status",
            "target": None,
            "raw_text": text,
        }

    return None


def generate_response(command_result: dict, scan_result: Optional[dict] = None) -> str:
    """Generate human-readable response for cybersecurity command."""
    command = command_result.get("command", "")

    if command == "get_status":
        if scan_result:
            stats = scan_result.get("stats", {})
            total_alerts = stats.get("active_alerts", 0)
            total_vulns = stats.get("open_vulnerabilities", 0)
            total_events = stats.get("total_events", 0)
            return (
                f"Security Status: {total_events} events recorded, "
                f"{total_alerts} active alerts, {total_vulns} open vulnerabilities. "
                f"System is being monitored."
            )
        return "Security monitoring is active. All systems are being watched."

    if command == "threat_scan":
        if scan_result:
            total = scan_result.get("total", 0)
            return f"Threat scan complete. Found {total} potential threats."
        return "Running threat detection scan..."

    if command == "full_scan":
        if scan_result:
            total = scan_result.get("total_findings", 0)
            return f"Full security scan complete. Found {total} total findings across all modules."
        return "Running comprehensive security scan across all modules..."

    if command == "generate_report":
        return "Security report generated successfully."

    if command == "get_alerts":
        if scan_result:
            alerts = scan_result.get("alerts", [])
            count = len(alerts)
            if count == 0:
                return "No active security alerts. All clear."
            return f"There are {count} active security alerts requiring attention."
        return "Checking for active security alerts..."

    if command == "secret_scan":
        if scan_result:
            total = scan_result.get("total", 0)
            if total == 0:
                return "Secret scan complete. No exposed secrets found."
            return f"Secret scan complete. Found {total} exposed secrets that need attention."
        return "Scanning for exposed secrets..."

    if command == "code_scan":
        if scan_result:
            total = scan_result.get("total", 0)
            return f"Code security scan complete. Found {total} potential security issues."
        return "Scanning source code for security vulnerabilities..."

    return f"Cybersecurity command '{command}' executed successfully."
