"""Secret and PII scanning with regex-based pattern detection."""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ScanMatch:
    pattern_name: str
    value: str
    start: int
    end: int
    severity: str
    line: int = 0


@dataclass
class ScanResult:
    clean: bool = True
    matches: list = field(default_factory=list)
    alerts: list = field(default_factory=list)

    def add(self, match: ScanMatch):
        self.matches.append(match)
        self.clean = False
        self.alerts.append({
            "pattern": match.pattern_name,
            "severity": match.severity,
            "position": f"{match.start}-{match.end}",
            "line": match.line,
        })


class SecretScanner:
    """Scans text for leaked secrets (API keys, tokens, passwords)."""

    PATTERNS = [
        ("openai_key", r"sk-[A-Za-z0-9_-]{20,}", "CRITICAL"),
        ("anthropic_key", r"sk-ant-[A-Za-z0-9_-]{20,}", "CRITICAL"),
        ("aws_access_key", r"AKIA[0-9A-Z]{16}", "CRITICAL"),
        ("github_token", r"(?:ghp|gho|ghs|ghr|github_pat)_[A-Za-z0-9_]{36,}", "CRITICAL"),
        ("google_api_key", r"AIza[0-9A-Za-z_-]{35}", "HIGH"),
        ("slack_token", r"xox[baprs]-[0-9A-Za-z-]{10,}", "HIGH"),
        ("stripe_key", r"(?:sk|pk)_(?:test|live)_[0-9A-Za-z]{20,}", "HIGH"),
        ("private_key", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "CRITICAL"),
        ("password_assignment", r'(?:password|passwd|pwd)\s*[=:]\s*["\'][^\s"\']{6,}["\']', "HIGH"),
        ("db_connection_string", r"(?:mongodb|postgres|mysql|redis)://[^\s\"']+", "HIGH"),
        ("generic_api_key", r'(?:api_key|apikey|api-key)\s*[=:]\s*["\'][A-Za-z0-9_-]{16,}["\']', "MEDIUM"),
        ("jwt_token", r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "MEDIUM"),
        ("bearer_token", r"(?:Bearer|bearer)\s+[A-Za-z0-9._-]{20,}", "MEDIUM"),
    ]

    def __init__(self):
        self._compiled = []
        for name, pattern, severity in self.PATTERNS:
            self._compiled.append((name, re.compile(pattern, re.IGNORECASE), severity))

    def scan(self, text: str) -> ScanResult:
        result = ScanResult()
        if not text:
            return result

        for line_num, line in enumerate(text.splitlines(), 1):
            for name, regex, severity in self._compiled:
                for m in regex.finditer(line):
                    result.add(ScanMatch(
                        pattern_name=name,
                        value=m.group()[:20] + "...",
                        start=m.start(),
                        end=m.end(),
                        severity=severity,
                        line=line_num,
                    ))
                    logger.warning(f"[SECRET SCAN] {severity} {name} detected at line {line_num}")

        return result

    def redact(self, text: str) -> str:
        for name, regex, _ in self._compiled:
            text = regex.sub(f"[REDACTED:{name}]", text)
        return text


class PIIScanner:
    """Scans text for personally identifiable information."""

    PATTERNS = [
        ("email", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "MEDIUM"),
        ("us_ssn", r"\b\d{3}-\d{2}-\d{4}\b", "CRITICAL"),
        ("credit_card_visa", r"\b4[0-9]{12}(?:[0-9]{3})?\b", "CRITICAL"),
        ("credit_card_mastercard", r"\b5[1-5][0-9]{14}\b", "CRITICAL"),
        ("credit_card_amex", r"\b3[47][0-9]{13}\b", "CRITICAL"),
        ("us_phone", r"\b(?:\+?1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "MEDIUM"),
        ("ipv4_public", r"\b(?:(?:[1-9]|1[0-9]|2[0-4])\d|25[0-5])\.(?:(?:\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5]))\.(?:(?:\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5]))\.(?:(?:\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5]))\b", "LOW"),
        ("indian_aadhaar", r"\b[2-9]{1}[0-9]{3}[0-9]{4}[0-9]{4}\b", "CRITICAL"),
        ("indian_pan", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", "HIGH"),
    ]

    _PRIVATE_IP_PREFIXES = ("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.",
                           "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
                           "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
                           "127.", "0.", "169.254.")

    def __init__(self):
        self._compiled = []
        for name, pattern, severity in self.PATTERNS:
            self._compiled.append((name, re.compile(pattern), severity))

    def scan(self, text: str) -> ScanResult:
        result = ScanResult()
        if not text:
            return result

        for line_num, line in enumerate(text.splitlines(), 1):
            for name, regex, severity in self._compiled:
                for m in regex.finditer(line):
                    if name == "ipv4_public" and m.group().startswith(self._PRIVATE_IP_PREFIXES):
                        continue
                    result.add(ScanMatch(
                        pattern_name=name,
                        value=m.group()[:10] + "...",
                        start=m.start(),
                        end=m.end(),
                        severity=severity,
                        line=line_num,
                    ))

        return result

    def redact(self, text: str) -> str:
        replacements = {
            "email": "[EMAIL]",
            "us_ssn": "[SSN]",
            "credit_card_visa": "[CARD]",
            "credit_card_mastercard": "[CARD]",
            "credit_card_amex": "[CARD]",
            "us_phone": "[PHONE]",
            "ipv4_public": "[IP]",
            "indian_aadhaar": "[AADHAAR]",
            "indian_pan": "[PAN]",
        }
        for name, regex, _ in self._compiled:
            text = regex.sub(replacements.get(name, "[REDACTED]"), text)
        return text
