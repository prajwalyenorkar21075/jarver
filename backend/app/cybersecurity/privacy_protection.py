"""
Privacy Protection for JARVIS cybersecurity module.

Detects data exposure and provides redaction:
- PII detection in text and files
- Data classification
- Automatic secret redaction
- Privacy compliance checks
"""

import re
import logging
import time
from typing import Optional
from pathlib import Path

from .security_db import get_security_db

logger = logging.getLogger(__name__)


PII_PATTERNS = {
    "ssn": {
        "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
        "description": "Social Security Number",
        "severity": "critical",
        "category": "pii",
    },
    "credit_card": {
        "pattern": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",
        "description": "Credit Card Number",
        "severity": "critical",
        "category": "pii",
    },
    "email": {
        "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "description": "Email Address",
        "severity": "medium",
        "category": "pii",
    },
    "phone_us": {
        "pattern": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "description": "US Phone Number",
        "severity": "medium",
        "category": "pii",
    },
    "ip_address": {
        "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "description": "IP Address",
        "severity": "low",
        "category": "technical_data",
    },
    "mac_address": {
        "pattern": r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b",
        "description": "MAC Address",
        "severity": "low",
        "category": "technical_data",
    },
    "passport_number": {
        "pattern": r"\b[A-Z]{1,2}\d{6,9}\b",
        "description": "Possible Passport Number",
        "severity": "high",
        "category": "pii",
    },
    "date_of_birth": {
        "pattern": r"\b(?:DOB|Date\s+of\s+Birth|Born)\s*[:=]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "description": "Date of Birth",
        "severity": "high",
        "category": "pii",
    },
    "bank_account": {
        "pattern": r"\b(?:account\s*(?:no|number|#)\s*[:=]?\s*\d{8,17})\b",
        "description": "Bank Account Number",
        "severity": "critical",
        "category": "financial",
    },
}


class PrivacyProtection:
    """Provides privacy protection and PII detection."""

    def __init__(self):
        self.db = get_security_db()
        self.logger = logging.getLogger(__name__)

    def detect_pii(self, text: str) -> list[dict]:
        """Detect PII in text."""
        findings = []

        for pii_type, info in PII_PATTERNS.items():
            matches = list(re.finditer(info["pattern"], text, re.IGNORECASE))
            for match in matches:
                findings.append({
                    "pii_type": pii_type,
                    "description": info["description"],
                    "severity": info["severity"],
                    "category": info["category"],
                    "position": match.start(),
                    "matched_text": self._redact_value(match.group(), pii_type),
                })

        return findings

    def _redact_value(self, value: str, pii_type: str) -> str:
        """Redact a PII value for safe display."""
        if len(value) <= 4:
            return "*" * len(value)
        return value[:2] + "*" * (len(value) - 4) + value[-2:]

    def redact_text(self, text: str) -> str:
        """Redact all PII from text."""
        redacted = text

        for pii_type, info in PII_PATTERNS.items():
            def replace_match(match):
                original = match.group()
                if len(original) <= 4:
                    return "[REDACTED]"
                return original[:2] + "[REDACTED]" + original[-2:]

            redacted = re.sub(info["pattern"], replace_match, redacted, flags=re.IGNORECASE)

        return redacted

    def scan_file_for_pii(self, file_path: str) -> dict:
        """Scan a file for PII."""
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            findings = self.detect_pii(content)

            pii_counts = {}
            for finding in findings:
                pii_type = finding["pii_type"]
                pii_counts[pii_type] = pii_counts.get(pii_type, 0) + 1

            severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for finding in findings:
                sev = finding.get("severity", "low")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            return {
                "file_path": file_path,
                "total_pii_found": len(findings),
                "by_type": pii_counts,
                "by_severity": severity_counts,
                "findings": findings,
                "scan_time": time.time(),
            }

        except Exception as e:
            self.logger.error(f"Error scanning file for PII: {e}")
            return {"error": str(e)}

    def scan_directory_for_pii(self, directory: str,
                                 extensions: Optional[list] = None) -> dict:
        """Scan a directory for PII."""
        path = Path(directory)
        if not path.exists():
            return {"error": f"Directory not found: {directory}"}

        valid_extensions = set(extensions or [
            ".txt", ".csv", ".json", ".xml", ".log",
            ".py", ".js", ".ts", ".java", ".sql",
            ".md", ".yaml", ".yml", ".toml",
        ])

        all_findings = []
        files_scanned = 0
        files_with_pii = 0

        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix in valid_extensions:
                if any(pattern in str(file_path) for pattern in
                       ["node_modules", ".git", "__pycache__", ".venv"]):
                    continue

                files_scanned += 1
                result = self.scan_file_for_pii(str(file_path))
                if result.get("total_pii_found", 0) > 0:
                    files_with_pii += 1
                    all_findings.extend(result.get("findings", []))

        return {
            "directory": directory,
            "files_scanned": files_scanned,
            "files_with_pii": files_with_pii,
            "total_pii_found": len(all_findings),
            "findings": all_findings,
            "scan_time": time.time(),
        }

    def classify_data(self, text: str) -> dict:
        """Classify data sensitivity level."""
        findings = self.detect_pii(text)

        severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        total_score = sum(
            severity_weights.get(f["severity"], 0) for f in findings
        )

        if total_score >= 10:
            classification = "highly_confidential"
        elif total_score >= 5:
            classification = "confidential"
        elif total_score >= 2:
            classification = "internal"
        else:
            classification = "public"

        return {
            "classification": classification,
            "score": total_score,
            "pii_types_found": list(set(f["pii_type"] for f in findings)),
            "total_pii_instances": len(findings),
        }


_privacy_protection: Optional[PrivacyProtection] = None


def get_privacy_protection() -> PrivacyProtection:
    """Get singleton instance of PrivacyProtection."""
    global _privacy_protection
    if _privacy_protection is None:
        _privacy_protection = PrivacyProtection()
    return _privacy_protection
