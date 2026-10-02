"""
Web Application Security Analyzer for JARVIS cybersecurity module.

OWASP-aligned web application security testing for authorized local targets.
Checks for common web vulnerabilities like XSS, SQL injection, insecure headers, etc.
"""

import logging
import re
import time
import socket
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .security_db import get_security_db

logger = logging.getLogger(__name__)


@dataclass
class WebSecurityFinding:
    """Represents a web security finding."""
    finding_id: str
    title: str
    severity: str
    category: str
    description: str
    url: str
    evidence: str = ""
    remediation: str = ""
    owasp_reference: str = ""
    cwe_id: str = ""


class WebApplicationSecurityAnalyzer:
    """Analyzes web applications for security vulnerabilities."""

    SECURITY_HEADERS = {
        "X-Content-Type-Options": {
            "expected": "nosniff",
            "severity": "medium",
            "description": "Prevents MIME type sniffing",
            "remediation": "Add 'X-Content-Type-Options: nosniff' header",
            "owasp": "A05:2021 Security Misconfiguration"
        },
        "X-Frame-Options": {
            "expected_values": ["DENY", "SAMEORIGIN"],
            "severity": "medium",
            "description": "Prevents clickjacking attacks",
            "remediation": "Add 'X-Frame-Options: DENY' or 'SAMEORIGIN' header",
            "owasp": "A05:2021 Security Misconfiguration"
        },
        "X-XSS-Protection": {
            "expected": "1; mode=block",
            "severity": "low",
            "description": "Enables browser XSS filtering",
            "remediation": "Add 'X-XSS-Protection: 1; mode=block' header",
            "owasp": "A03:2021 Injection"
        },
        "Strict-Transport-Security": {
            "severity": "high",
            "description": "Enforces HTTPS connections",
            "remediation": "Add 'Strict-Transport-Security' header with max-age",
            "owasp": "A02:2021 Cryptographic Failures"
        },
        "Content-Security-Policy": {
            "severity": "high",
            "description": "Controls resource loading to prevent XSS",
            "remediation": "Implement a Content-Security-Policy header",
            "owasp": "A03:2021 Injection"
        },
        "Referrer-Policy": {
            "severity": "low",
            "description": "Controls referrer information",
            "remediation": "Add 'Referrer-Policy: strict-origin-when-cross-origin' header",
            "owasp": "A05:2021 Security Misconfiguration"
        },
    }

    INSECURE_PATTERNS = {
        "sql_error_mysql": {
            "pattern": r"(?:mysql|mysqli|sql)\s*(?:warning|error|syntax)",
            "severity": "high",
            "title": "MySQL error message exposed",
            "owasp": "A04:2021 Insecure Design",
            "cwe": "CWE-209"
        },
        "sql_error_postgres": {
            "pattern": r"postgresql.*error|pg_query.*error",
            "severity": "high",
            "title": "PostgreSQL error message exposed",
            "owasp": "A04:2021 Insecure Design",
            "cwe": "CWE-209"
        },
        "sql_error_mssql": {
            "pattern": r"(?:microsoft|msql|sql server).*error",
            "severity": "high",
            "title": "MSSQL error message exposed",
            "owasp": "A04:2021 Insecure Design",
            "cwe": "CWE-209"
        },
        "path_disclosure": {
            "pattern": r"(?:/[a-zA-Z]:\\\\|/[a-z]+/[a-z]+/[a-z]+).*\.(?:php|asp|jsp|py)",
            "severity": "medium",
            "title": "Server path disclosed",
            "owasp": "A05:2021 Security Misconfiguration",
            "cwe": "CWE-200"
        },
        "stack_trace": {
            "pattern": r"(?:stack\s*trace|traceback|at\s+\w+\.\w+\(|Exception\s+in)",
            "severity": "medium",
            "title": "Stack trace exposed",
            "owasp": "A05:2021 Security Misconfiguration",
            "cwe": "CWE-209"
        },
        "version_disclosure": {
            "pattern": r"(?:powered\s*by|server:)\s*(?:php|apache|nginx|iis)[/\s]*\d",
            "severity": "low",
            "title": "Server version disclosed",
            "owasp": "A05:2021 Security Misconfiguration",
            "cwe": "CWE-200"
        },
    }

    def __init__(self):
        self.db = get_security_db()
        self.logger = logging.getLogger(__name__)

    def check_security_headers(self, headers: dict) -> list[dict]:
        """Check for missing or misconfigured security headers."""
        findings = []
        headers_lower = {k.lower(): v for k, v in headers.items()}

        for header_name, header_info in self.SECURITY_HEADERS.items():
            header_lower = header_name.lower()
            if header_lower not in headers_lower:
                findings.append({
                    "title": f"Missing security header: {header_name}",
                    "severity": header_info["severity"],
                    "category": "missing_security_header",
                    "description": header_info["description"],
                    "remediation": header_info["remediation"],
                    "owasp_reference": header_info.get("owasp", ""),
                })
            else:
                value = headers_lower[header_lower]
                if "expected" in header_info:
                    if header_info["expected"].lower() not in value.lower():
                        findings.append({
                            "title": f"Misconfigured header: {header_name}",
                            "severity": header_info["severity"],
                            "category": "misconfigured_security_header",
                            "description": f"{header_name} has incorrect value: {value}",
                            "remediation": header_info["remediation"],
                            "owasp_reference": header_info.get("owasp", ""),
                        })
                elif "expected_values" in header_info:
                    if value.upper() not in [v.upper() for v in header_info["expected_values"]]:
                        findings.append({
                            "title": f"Misconfigured header: {header_name}",
                            "severity": header_info["severity"],
                            "category": "misconfigured_security_header",
                            "description": f"{header_name} has incorrect value: {value}",
                            "remediation": header_info["remediation"],
                            "owasp_reference": header_info.get("owasp", ""),
                        })

        return findings

    def check_cookie_security(self, cookies: list[dict]) -> list[dict]:
        """Check cookie security attributes."""
        findings = []

        for cookie in cookies:
            name = cookie.get("name", "unknown")
            flags = cookie.get("flags", "").lower()

            if "secure" not in flags:
                findings.append({
                    "title": f"Cookie missing Secure flag: {name}",
                    "severity": "medium",
                    "category": "insecure_cookie",
                    "description": f"Cookie '{name}' can be sent over unencrypted connections",
                    "remediation": "Set the Secure flag on all cookies",
                    "owasp_reference": "A02:2021 Cryptographic Failures",
                })

            if "httponly" not in flags:
                findings.append({
                    "title": f"Cookie missing HttpOnly flag: {name}",
                    "severity": "medium",
                    "category": "insecure_cookie",
                    "description": f"Cookie '{name}' is accessible via JavaScript",
                    "remediation": "Set the HttpOnly flag on session cookies",
                    "owasp_reference": "A03:2021 Injection",
                })

            if "samesite" not in flags:
                findings.append({
                    "title": f"Cookie missing SameSite attribute: {name}",
                    "severity": "low",
                    "category": "insecure_cookie",
                    "description": f"Cookie '{name}' may be vulnerable to CSRF",
                    "remediation": "Set SameSite=Strict or SameSite=Lax attribute",
                    "owasp_reference": "A01:2021 Broken Access Control",
                })

        return findings

    def analyze_response_content(self, content: str, url: str) -> list[dict]:
        """Analyze response content for information disclosure."""
        findings = []

        for pattern_name, pattern_info in self.INSECURE_PATTERNS.items():
            if re.search(pattern_info["pattern"], content, re.IGNORECASE):
                findings.append({
                    "title": pattern_info["title"],
                    "severity": pattern_info["severity"],
                    "category": "information_disclosure",
                    "description": f"Sensitive information detected in response from {url}",
                    "url": url,
                    "owasp_reference": pattern_info.get("owasp", ""),
                    "cwe_id": pattern_info.get("cwe", ""),
                    "remediation": "Configure application to suppress detailed error messages in production",
                })

        return findings

    def check_https_configuration(self, url: str) -> list[dict]:
        """Check HTTPS configuration and certificate."""
        findings = []
        parsed = urlparse(url)

        if parsed.scheme == "http":
            findings.append({
                "title": "Application uses HTTP instead of HTTPS",
                "severity": "high",
                "category": "insecure_transport",
                "description": f"Application at {url} does not use encryption",
                "url": url,
                "remediation": "Configure HTTPS with a valid TLS certificate",
                "owasp_reference": "A02:2021 Cryptographic Failures",
            })

        return findings

    def analyze_web_application(self, url: str, headers: Optional[dict] = None,
                                 cookies: Optional[list] = None,
                                 response_content: str = "") -> dict:
        """Comprehensive web application security analysis."""
        self.logger.info(f"[WEB_SEC] Analyzing web application: {url}")

        all_findings = []

        all_findings.extend(self.check_https_configuration(url))

        if headers:
            all_findings.extend(self.check_security_headers(headers))

        if cookies:
            all_findings.extend(self.check_cookie_security(cookies))

        if response_content:
            all_findings.extend(self.analyze_response_content(response_content, url))

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for finding in all_findings:
            severity = finding.get("severity", "info")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        scan_result = {
            "total": len(all_findings),
            "critical": severity_counts["critical"],
            "high": severity_counts["high"],
            "medium": severity_counts["medium"],
            "low": severity_counts["low"],
            "info": severity_counts["info"],
            "findings": all_findings,
            "url": url,
            "scan_time": time.time(),
        }

        scan_id = self.db.insert_scan_result(
            scan_type="web_security_scan",
            target=url,
            status="completed",
            findings=scan_result
        )

        self.logger.info(f"[WEB_SEC] Analysis complete: {len(all_findings)} findings")

        return {
            "scan_id": scan_id,
            "result": scan_result,
        }


_web_analyzer: Optional[WebApplicationSecurityAnalyzer] = None


def get_web_application_analyzer() -> WebApplicationSecurityAnalyzer:
    """Get singleton instance of WebApplicationSecurityAnalyzer."""
    global _web_analyzer
    if _web_analyzer is None:
        _web_analyzer = WebApplicationSecurityAnalyzer()
    return _web_analyzer
