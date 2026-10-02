"""
Secure Code Analyzer for JARVIS cybersecurity module.

Scans source code for security vulnerabilities including:
- Hardcoded secrets and credentials
- SQL injection patterns
- XSS vulnerabilities
- Insecure cryptographic usage
- Path traversal risks
- Command injection patterns
"""

import re
import logging
import time
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field

from .security_db import get_security_db

logger = logging.getLogger(__name__)


@dataclass
class CodeSecurityFinding:
    """Represents a code security finding."""
    file_path: str
    line_number: int
    title: str
    severity: str
    category: str
    description: str
    code_snippet: str = ""
    remediation: str = ""
    cwe_id: str = ""


SECURITY_RULES = {
    "hardcoded_secrets": {
        "patterns": [
            (r"""(?:password|passwd|pwd)\s*=\s*['"][^'"]{3,}['"]""", "Hardcoded password"),
            (r"""(?:api_key|apikey|api_secret)\s*=\s*['"][^'"]{3,}['"]""", "Hardcoded API key"),
            (r"""(?:secret|token)\s*=\s*['"][^'"]{8,}['"]""", "Hardcoded secret/token"),
            (r"""(?:aws_access_key_id|aws_secret_access_key)\s*=\s*['"][^'"]+['"]""", "AWS credentials"),
            (r"""PRIVATE\s+KEY""", "Private key reference"),
        ],
        "severity": "critical",
        "category": "hardcoded_secret",
        "cwe": "CWE-798",
        "remediation": "Use environment variables or a secrets manager",
    },
    "sql_injection": {
        "patterns": [
            (r"""(?:execute|query)\s*\(\s*['"].*%s""", "SQL with string formatting"),
            (r"""(?:execute|query)\s*\(\s*['"].*\+\s*\w+""", "SQL with string concatenation"),
            (r"""(?:execute|query)\s*\(\s*f['"]""", "SQL with f-string"),
            (r"""(?:execute|query)\s*\(\s*['"].*\.format\(""", "SQL with .format()"),
            (r"""(?:SELECT|INSERT|UPDATE|DELETE).*\+\s*\w+""", "SQL query concatenation"),
        ],
        "severity": "critical",
        "category": "sql_injection",
        "cwe": "CWE-89",
        "remediation": "Use parameterized queries or prepared statements",
    },
    "xss": {
        "patterns": [
            (r"""innerHTML\s*=""", "Direct innerHTML assignment"),
            (r"""document\.write\s*\(""", "document.write usage"),
            (r"""\.html\s*\(\s*[^)]*\+""", "jQuery .html() with concatenation"),
            (r"""dangerouslySetInnerHTML""", "React dangerouslySetInnerHTML usage"),
            (r"""\{\{\s*\w+\s*\|\s*safe\s*\}\}""", "Template safe filter usage"),
        ],
        "severity": "high",
        "category": "xss",
        "cwe": "CWE-79",
        "remediation": "Use proper output encoding and sanitization",
    },
    "command_injection": {
        "patterns": [
            (r"""os\.system\s*\(""", "os.system() usage"),
            (r"""os\.popen\s*\(""", "os.popen() usage"),
            (r"""subprocess\.call\s*\(.*shell\s*=\s*True""", "subprocess with shell=True"),
            (r"""subprocess\.run\s*\(.*shell\s*=\s*True""", "subprocess.run with shell=True"),
            (r"""eval\s*\(""", "eval() usage"),
            (r"""exec\s*\(""", "exec() usage"),
        ],
        "severity": "critical",
        "category": "command_injection",
        "cwe": "CWE-78",
        "remediation": "Use subprocess with argument list, avoid shell=True",
    },
    "path_traversal": {
        "patterns": [
            (r"""open\s*\(.*\+.*\)""", "File open with concatenation"),
            (r"""os\.path\.join\s*\(.*input""", "Path join with user input"),
            (r"""send_file\s*\(.*request""", "send_file with user input"),
            (r"""\.\.[\\/]""", "Path traversal pattern"),
        ],
        "severity": "high",
        "category": "path_traversal",
        "cwe": "CWE-22",
        "remediation": "Validate and sanitize file paths, use allowlists",
    },
    "insecure_crypto": {
        "patterns": [
            (r"""MD5\s*\(""", "MD5 usage (weak hash)"),
            (r"""SHA1\s*\(""", "SHA1 usage (weak hash)"),
            (r"""DES\s*\(""", "DES usage (weak cipher)"),
            (r"""RC4\s*\(""", "RC4 usage (weak cipher)"),
            (r"""(?:encrypt|decrypt).*ECB""", "ECB mode usage"),
        ],
        "severity": "high",
        "category": "insecure_cryptography",
        "cwe": "CWE-327",
        "remediation": "Use strong algorithms: SHA-256+, AES-256 with GCM mode",
    },
    "insecure_random": {
        "patterns": [
            (r"""random\.random\s*\(""", "Non-cryptographic random"),
            (r"""random\.randint\s*\(""", "Non-cryptographic random"),
            (r"""Math\.random\s*\(""", "Non-cryptographic random (JS)"),
        ],
        "severity": "medium",
        "category": "insecure_random",
        "cwe": "CWE-338",
        "remediation": "Use cryptographically secure random: secrets module (Python), crypto.randomBytes (Node.js)",
    },
    "cors_misconfiguration": {
        "patterns": [
            (r"""Access-Control-Allow-Origin.*\*""", "Wildcard CORS origin"),
            (r"""CORS_ORIGIN\s*=\s*\*""", "Wildcard CORS configuration"),
            (r"""cors\(\s*\)""", "Permissive CORS"),
        ],
        "severity": "medium",
        "category": "cors_misconfiguration",
        "cwe": "CWE-942",
        "remediation": "Restrict CORS to specific trusted origins",
    },
}

FILE_EXTENSIONS = {
    "python": [".py"],
    "javascript": [".js", ".jsx", ".ts", ".tsx"],
    "java": [".java"],
    "php": [".php"],
    "ruby": [".rb"],
    "go": [".go"],
    "csharp": [".cs"],
    "all": [".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".php", ".rb", ".go", ".cs"],
}


class SecureCodeAnalyzer:
    """Analyzes source code for security vulnerabilities."""

    def __init__(self):
        self.db = get_security_db()
        self.logger = logging.getLogger(__name__)

    def scan_file(self, file_path: str) -> list[dict]:
        """Scan a single file for security issues."""
        findings = []
        path = Path(file_path)

        if not path.exists():
            self.logger.warning(f"File not found: {file_path}")
            return findings

        if path.suffix not in FILE_EXTENSIONS["all"]:
            return findings

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                for rule_name, rule in SECURITY_RULES.items():
                    for pattern, description in rule["patterns"]:
                        if re.search(pattern, line, re.IGNORECASE):
                            snippet = line.strip()[:120]
                            findings.append({
                                "file_path": str(file_path),
                                "line_number": line_num,
                                "title": description,
                                "severity": rule["severity"],
                                "category": rule["category"],
                                "description": f"{description} found in {path.name}:{line_num}",
                                "code_snippet": snippet,
                                "remediation": rule["remediation"],
                                "cwe_id": rule.get("cwe", ""),
                                "rule": rule_name,
                            })

        except Exception as e:
            self.logger.error(f"Error scanning file {file_path}: {e}")

        return findings

    def scan_directory(self, directory: str, extensions: Optional[list] = None,
                        exclude_patterns: Optional[list] = None) -> list[dict]:
        """Scan a directory recursively for security issues."""
        findings = []
        path = Path(directory)

        if not path.exists():
            self.logger.warning(f"Directory not found: {directory}")
            return findings

        exclude_patterns = exclude_patterns or [
            "node_modules", ".git", "__pycache__", "venv", ".venv",
            "dist", "build", ".next", "target", "vendor"
        ]

        valid_extensions = set(extensions or FILE_EXTENSIONS["all"])

        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix in valid_extensions:
                if any(pattern in str(file_path) for pattern in exclude_patterns):
                    continue
                file_findings = self.scan_file(str(file_path))
                findings.extend(file_findings)

        return findings

    def scan_project(self, project_path: str) -> dict:
        """Comprehensive project security scan."""
        self.logger.info(f"[CODE_ANALYZER] Scanning project: {project_path}")

        all_findings = self.scan_directory(project_path)

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        category_counts = {}

        for finding in all_findings:
            severity = finding.get("severity", "info")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            category = finding.get("category", "unknown")
            category_counts[category] = category_counts.get(category, 0) + 1

        scan_result = {
            "total": len(all_findings),
            "critical": severity_counts["critical"],
            "high": severity_counts["high"],
            "medium": severity_counts["medium"],
            "low": severity_counts["low"],
            "info": severity_counts["info"],
            "by_category": category_counts,
            "findings": all_findings,
            "project_path": project_path,
            "scan_time": time.time(),
        }

        scan_id = self.db.insert_scan_result(
            scan_type="code_security_scan",
            target=project_path,
            status="completed",
            findings=scan_result
        )

        self.logger.info(f"[CODE_ANALYZER] Scan complete: {len(all_findings)} findings")

        return {
            "scan_id": scan_id,
            "result": scan_result,
        }


_code_analyzer: Optional[SecureCodeAnalyzer] = None


def get_secure_code_analyzer() -> SecureCodeAnalyzer:
    """Get singleton instance of SecureCodeAnalyzer."""
    global _code_analyzer
    if _code_analyzer is None:
        _code_analyzer = SecureCodeAnalyzer()
    return _code_analyzer
