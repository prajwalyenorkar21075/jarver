"""
Voice command handler for Ethical Hacking module.

Parses voice commands in English, Hindi, and Marathi and routes them
to the ethical hacking API endpoints.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


COMMAND_PATTERNS = {
    "port_scan": [
        r"(?:run|start|do|perform|execute)?\s*(?:port\s*scan|scan\s*ports?)\s*(?:on|for|of)?\s*(.+)?",
        r"(?:पोर्ट\s*स्कैन|पोर्ट\s*स्कॅन)\s*(?:करें|करा|on)?\s*(.+)?",
    ],
    "vuln_assess": [
        r"(?:run|start|do|perform)?\s*(?:vulnerability\s*(?:scan|assessment)|vuln\s*scan)\s*(?:on|for|of)?\s*(.+)?",
        r"(?:check|find|detect)\s*(?:vulnerabilit(?:y|ies))\s*(?:on|in|for)?\s*(.+)?",
        r"(?:भेद्यता\s*(?:स्कैन|जांच|तपासणी))\s*(?:करें|करा)?\s*(.+)?",
    ],
    "web_test": [
        r"(?:run|start|do|perform)?\s*(?:web\s*(?:security\s*)?test|web\s*assessment)\s*(?:on|for|of)?\s*(.+)?",
        r"(?:check|test)\s*(?:web\s*(?:security|application))\s*(?:on|for|of)?\s*(.+)?",
    ],
    "network_assess": [
        r"(?:run|start|do|perform)?\s*(?:network\s*(?:security\s*)?(?:assessment|scan|check))\s*(?:on|for|of)?\s*(.+)?",
        r"(?:check|assess)\s*(?:network\s*security)\s*(?:on|for|of)?\s*(.+)?",
        r"(?:नेटवर्क\s*(?:सुरक्षा\s*)?(?:जांच|तपासणी))\s*(?:करें|करा)?\s*(.+)?",
    ],
    "config_audit": [
        r"(?:run|start|do|perform)?\s*(?:config(?:uration)?\s*(?:audit|check|scan))\s*(?:on|for|of)?\s*(.+)?",
        r"(?:audit|check)\s*(?:system\s*)?config(?:uration)?\s*(?:on|for|of)?\s*(.+)?",
    ],
    "auth_audit": [
        r"(?:run|start|do|perform)?\s*(?:auth(?:entication)?\s*(?:audit|check))\s*(?:on|for|of)?\s*(.+)?",
        r"(?:check|audit)\s*(?:password\s*policy|auth(?:entication)?|user\s*accounts?)\s*(?:on|for|of)?\s*(.+)?",
    ],
    "misconfig_check": [
        r"(?:run|start|do|perform)?\s*(?:misconfig(?:uration)?\s*(?:check|scan|detect))\s*(?:on|for|of)?\s*(.+)?",
        r"(?:check|detect|find)\s*(?:misconfig(?:uration)?|exposed\s*(?:services|secrets))\s*(?:on|for|of)?\s*(.+)?",
    ],
    "generate_report": [
        r"(?:generate|create|make)\s*(?:pentest|penetration\s*test|security)\s*report\s*(?:for)?\s*(.+)?",
        r"(?:report|summary)\s*(?:generate|create)\s*(?:for)?\s*(.+)?",
        r"(?:रिपोर्ट|अहवाल)\s*(?:बनाएं|तयार\s*करा)\s*(.+)?",
    ],
    "create_scope": [
        r"(?:create|setup|define)\s*(?:test\s*)?scope\s*(?:for|named?)?\s*(.+)?",
        r"(?:authorize|allow)\s*(?:testing|scan)\s*(?:on|for|of)\s*(.+)?",
    ],
    "get_status": [
        r"(?:show|get|what(?:'s|is)\s*(?:the)?)\s*(?:security|pentest|ethical\s*hacking)\s*(?:status|stats|results|findings)",
        r"(?:any\s*)?(?:vulnerabilit(?:y|ies)|findings|issues)\s*(?:found|detected|reported)?",
        r"(?:सुरक्षा|security)\s*(?:स्थिति|status|results)\s*(?:दिखाएं|दाखवा)?",
    ],
    "check_firewall": [
        r"(?:check|test|verify)\s*(?:firewall)\s*(?:status|on|off)?",
        r"(?:firewall\s*(?:चालू|बंद|on|off|status))",
    ],
    "check_secrets": [
        r"(?:scan|check|find|detect)\s*(?:exposed\s*)?(?:secrets|passwords|api\s*keys?)\s*(?:in|for)?\s*(.+)?",
        r"(?:find|detect)\s*(?:hardcoded|embedded)\s*(?:secrets?|credentials?)\s*(?:in)?\s*(.+)?",
    ],
}


def parse_ethical_hacking_command(text: str) -> Optional[dict]:
    text_lower = text.lower().strip()

    for command, patterns in COMMAND_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                target = match.group(1).strip() if match.lastindex and match.group(1) else None
                return {
                    "command": command,
                    "target": target,
                    "raw_text": text,
                }

    if re.search(r"\b(pentest|penetration|ethical\s*hack|security\s*(?:test|scan|audit|assessment))\b", text_lower, re.IGNORECASE):
        return {
            "command": "get_status",
            "target": None,
            "raw_text": text,
        }

    return None


def generate_response(result: dict) -> str:
    command = result.get("command", "")
    success = result.get("success", False)
    data = result.get("data", {})

    if not success:
        error = result.get("error", "Unknown error")
        return f"Security test failed: {error}"

    responses = {
        "port_scan": _format_port_scan(data),
        "vuln_assess": _format_vuln_assess(data),
        "web_test": _format_web_test(data),
        "network_assess": _format_network_assess(data),
        "config_audit": _format_config_audit(data),
        "auth_audit": _format_auth_audit(data),
        "misconfig_check": _format_misconfig_check(data),
        "generate_report": _format_report(data),
        "create_scope": _format_scope(data),
        "get_status": _format_status(data),
        "check_firewall": _format_firewall(data),
        "check_secrets": _format_secrets(data),
    }

    return responses.get(command, "Command completed.")


def _format_port_scan(data: dict) -> str:
    host = data.get("host", "unknown")
    open_ports = data.get("open_ports", [])
    findings = data.get("findings", [])
    scan_time = data.get("scan_time", 0)

    if not open_ports:
        return f"Port scan complete on {host}. No open ports found. Scan took {scan_time:.2f} seconds."

    port_list = ", ".join(f"{p['port']}/{p['service']}" for p in open_ports[:10])
    return f"Port scan on {host}: Found {len(open_ports)} open ports ({port_list}). {len(findings)} findings recorded. Scan took {scan_time:.2f} seconds."


def _format_vuln_assess(data: dict) -> str:
    host = data.get("host", "unknown")
    total = data.get("total_findings", 0)
    findings = data.get("findings", [])

    critical = sum(1 for f in findings if f.get("severity") == "critical")
    high = sum(1 for f in findings if f.get("severity") == "high")

    msg = f"Vulnerability assessment on {host}: {total} findings"
    if critical:
        msg += f" ({critical} critical"
        if high:
            msg += f", {high} high"
        msg += ")"
    elif high:
        msg += f" ({high} high)"
    msg += "."
    return msg


def _format_web_test(data: dict) -> str:
    url = data.get("url", "unknown")
    total = data.get("total_findings", 0)
    return f"Web security test on {url}: {total} security issues found."


def _format_network_assess(data: dict) -> str:
    total = data.get("total_findings", 0)
    return f"Network security assessment complete: {total} issues found."


def _format_config_audit(data: dict) -> str:
    total = data.get("total_findings", 0)
    return f"Configuration audit complete: {total} security issues found."


def _format_auth_audit(data: dict) -> str:
    total = data.get("total_findings", 0)
    return f"Authentication audit complete: {total} issues found."


def _format_misconfig_check(data: dict) -> str:
    total = data.get("total_findings", 0)
    return f"Security misconfiguration check complete: {total} issues found."


def _format_report(data: dict) -> str:
    if not data.get("success"):
        return "Failed to generate report."
    report = data.get("report", {})
    summary = report.get("executive_summary", {})
    risk = summary.get("risk_level", "unknown")
    total = summary.get("total_findings", 0)
    return f"Penetration test report generated. Overall risk level: {risk}. Total findings: {total}."


def _format_scope(data: dict) -> str:
    scope = data.get("scope", {})
    name = scope.get("name", "unknown")
    targets = scope.get("targets", [])
    return f"Test scope '{name}' created for targets: {', '.join(targets)}. Authorization granted."


def _format_status(data: dict) -> str:
    stats = data.get("stats", {})
    total = stats.get("total_findings", 0)
    active = stats.get("active_scopes", 0)
    by_sev = stats.get("findings_by_severity", {})

    msg = f"Security status: {total} total findings across {active} active scopes."
    if by_sev:
        parts = [f"{count} {sev}" for sev, count in by_sev.items()]
        msg += f" Breakdown: {', '.join(parts)}."
    return msg


def _format_firewall(data: dict) -> str:
    total = data.get("total_findings", 0)
    if total == 0:
        return "Firewall check complete: No issues detected. Firewall appears to be properly configured."
    return f"Firewall check: {total} issues found. Review firewall configuration."


def _format_secrets(data: dict) -> str:
    total = data.get("total_findings", 0)
    if total == 0:
        return "Secret scan complete: No exposed secrets found."
    return f"Secret scan: {total} exposed secrets detected. Immediate remediation recommended."
