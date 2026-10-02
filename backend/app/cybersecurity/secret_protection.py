"""
Secrets & Credential Protection for JARVIS cybersecurity module.

Detects exposed secrets and credentials in:
- Source code files
- Configuration files
- Environment files
- Log files
- Version control history
"""

import re
import logging
import time
from typing import Optional
from pathlib import Path

from .security_db import get_security_db

logger = logging.getLogger(__name__)


SECRET_PATTERNS = {
    "aws_access_key": {
        "pattern": r"(?:AKIA|A3T[A-Z0-9]|ABIA|ACCA|ASIA)[A-Z0-9]{16}",
        "severity": "critical",
        "description": "AWS Access Key ID",
        "remediation": "Rotate the key immediately and use IAM roles instead",
    },
    "aws_secret_key": {
        "pattern": r"""(?i)aws_secret_access_key\s*[=:]\s*['"]?([A-Za-z0-9/+=]{40})['"]?""",
        "severity": "critical",
        "description": "AWS Secret Access Key",
        "remediation": "Rotate the key immediately and use environment variables",
    },
    "github_token": {
        "pattern": r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}",
        "severity": "critical",
        "description": "GitHub Personal Access Token",
        "remediation": "Revoke the token and use GitHub Actions secrets",
    },
    "generic_api_key": {
        "pattern": r"""(?i)(?:api[_-]?key|apikey)\s*[=:]\s*['"]([A-Za-z0-9_\-]{20,})['"]""",
        "severity": "high",
        "description": "Generic API Key",
        "remediation": "Use environment variables or a secrets manager",
    },
    "private_key": {
        "pattern": r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP)\s+PRIVATE\s+KEY-----",
        "severity": "critical",
        "description": "Private Key",
        "remediation": "Remove from source code and use secure key storage",
    },
    "generic_secret": {
        "pattern": r"""(?i)(?:secret|password|passwd|pwd|token|auth)\s*[=:]\s*['"]([^'"]{8,})['"]""",
        "severity": "high",
        "description": "Hardcoded Secret/Password",
        "remediation": "Use environment variables or a secrets manager",
    },
    "database_url": {
        "pattern": r"""(?i)(?:mongodb|postgres|mysql|redis)://[^:]+:([^@]+)@""",
        "severity": "critical",
        "description": "Database connection string with credentials",
        "remediation": "Use environment variables for database credentials",
    },
    "jwt_token": {
        "pattern": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "severity": "high",
        "description": "JSON Web Token",
        "remediation": "JWTs should not be hardcoded; use short-lived tokens",
    },
    "slack_token": {
        "pattern": r"xox[baprs]-[A-Za-z0-9-]{10,}",
        "severity": "critical",
        "description": "Slack Token",
        "remediation": "Revoke and rotate the Slack token",
    },
    "google_api_key": {
        "pattern": r"AIza[0-9A-Za-z_-]{35}",
        "severity": "high",
        "description": "Google API Key",
        "remediation": "Restrict the API key and use environment variables",
    },
    "stripe_key": {
        "pattern": r"(?:sk|pk)_(?:test|live)_[A-Za-z0-9]{20,}",
        "severity": "critical",
        "description": "Stripe API Key",
        "remediation": "Rotate the key and use environment variables",
    },
    "sendgrid_key": {
        "pattern": r"SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}",
        "severity": "critical",
        "description": "SendGrid API Key",
        "remediation": "Rotate the key and use environment variables",
    },
    "heroku_api_key": {
        "pattern": r"""(?i)heroku.*[=:]\s*['"]?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})['"]?""",
        "severity": "high",
        "description": "Heroku API Key",
        "remediation": "Rotate the key and use environment variables",
    },
    "base64_encoded_secret": {
        "pattern": r"""(?i)(?:password|secret|key|token)\s*[=:]\s*['"]([A-Za-z0-9+/]{20,}={0,2})['"]""",
        "severity": "medium",
        "description": "Possible base64-encoded secret",
        "remediation": "Verify if this is a secret and move to environment variables",
    },
}

SENSITIVE_FILE_PATTERNS = [
    ".env", ".env.local", ".env.production",
    "config.json", "config.yaml", "config.yml",
    "secrets.json", "credentials.json",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "*.pem", "*.key", "*.p12", "*.pfx",
]


class SecretScanner:
    """Scans for exposed secrets and credentials."""

    def __init__(self):
        self.db = get_security_db()
        self.logger = logging.getLogger(__name__)

    def scan_file(self, file_path: str) -> list[dict]:
        """Scan a single file for exposed secrets."""
        findings = []
        path = Path(file_path)

        if not path.exists() or not path.is_file():
            return findings

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            for line_num, line in enumerate(content.split('\n'), 1):
                for secret_type, info in SECRET_PATTERNS.items():
                    matches = re.finditer(info["pattern"], line)
                    for match in matches:
                        secret_value = match.group(0)
                        redacted = self._redact_secret(secret_value)

                        findings.append({
                            "file_path": str(file_path),
                            "line_number": line_num,
                            "secret_type": secret_type,
                            "severity": info["severity"],
                            "description": info["description"],
                            "redacted_value": redacted,
                            "remediation": info["remediation"],
                            "category": "exposed_secret",
                        })

        except Exception as e:
            self.logger.error(f"Error scanning file {file_path}: {e}")

        return findings

    def _redact_secret(self, secret: str) -> str:
        """Redact a secret value for safe display."""
        if len(secret) <= 8:
            return "*" * len(secret)
        return secret[:4] + "*" * (len(secret) - 8) + secret[-4:]

    def scan_directory(self, directory: str,
                        exclude_patterns: Optional[list] = None) -> list[dict]:
        """Scan a directory for exposed secrets."""
        findings = []
        path = Path(directory)

        if not path.exists():
            return findings

        exclude_patterns = exclude_patterns or [
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            "dist", "build", ".next", "target", "vendor"
        ]

        scan_extensions = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb",
            ".php", ".cs", ".json", ".yaml", ".yml", ".toml", ".xml",
            ".env", ".cfg", ".conf", ".ini", ".properties",
            ".sh", ".bash", ".ps1", ".bat", ".cmd",
            ".md", ".txt", ".log", ".sql", ".html",
        }

        for file_path in path.rglob("*"):
            if file_path.is_file():
                if any(pattern in str(file_path) for pattern in exclude_patterns):
                    continue

                if file_path.suffix in scan_extensions or file_path.name.startswith(".env"):
                    file_findings = self.scan_file(str(file_path))
                    findings.extend(file_findings)

        return findings

    def scan_environment_files(self, project_path: str) -> list[dict]:
        """Specifically scan .env files for secrets."""
        findings = []
        path = Path(project_path)

        env_files = list(path.glob(".env*"))
        env_files.extend(path.glob("**/.env*"))

        for env_file in set(env_files):
            if env_file.is_file():
                file_findings = self.scan_file(str(env_file))
                for finding in file_findings:
                    finding["source"] = "environment_file"
                findings.extend(file_findings)

        return findings

    def redact_text(self, text: str) -> str:
        """Redact any secrets found in text."""
        redacted = text

        for secret_type, info in SECRET_PATTERNS.items():
            pattern = info["pattern"]
            redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)

        return redacted

    def comprehensive_secret_scan(self, target_path: str) -> dict:
        """Run comprehensive secret scan."""
        self.logger.info(f"[SECRET_SCANNER] Scanning: {target_path}")

        path = Path(target_path)

        if path.is_file():
            all_findings = self.scan_file(target_path)
        else:
            all_findings = self.scan_directory(target_path)

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        type_counts = {}

        for finding in all_findings:
            severity = finding.get("severity", "info")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            secret_type = finding.get("secret_type", "unknown")
            type_counts[secret_type] = type_counts.get(secret_type, 0) + 1

        for finding in all_findings:
            self.db.insert_event(
                event_type="exposed_secret",
                severity=finding.get("severity", "high"),
                description=f"{finding.get('description')}: {finding.get('file_path')}:{finding.get('line_number')}",
                source="secret_scanner",
                details=finding
            )

        scan_result = {
            "total": len(all_findings),
            "critical": severity_counts["critical"],
            "high": severity_counts["high"],
            "medium": severity_counts["medium"],
            "low": severity_counts["low"],
            "by_type": type_counts,
            "findings": all_findings,
            "target": target_path,
            "scan_time": time.time(),
        }

        scan_id = self.db.insert_scan_result(
            scan_type="secret_scan",
            target=target_path,
            status="completed",
            findings=scan_result
        )

        self.logger.info(f"[SECRET_SCANNER] Scan complete: {len(all_findings)} secrets found")

        return {
            "scan_id": scan_id,
            "result": scan_result,
        }


_secret_scanner: Optional[SecretScanner] = None


def get_secret_scanner() -> SecretScanner:
    """Get singleton instance of SecretScanner."""
    global _secret_scanner
    if _secret_scanner is None:
        _secret_scanner = SecretScanner()
    return _secret_scanner
