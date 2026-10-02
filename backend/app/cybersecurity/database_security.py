"""
Database Security Auditor for JARVIS cybersecurity module.

Audits database configurations and permissions:
- SQL injection pattern detection in queries
- Permission and privilege analysis
- Configuration security checks
- Connection string security
"""

import re
import logging
import time
from typing import Optional
from pathlib import Path

from .security_db import get_security_db

logger = logging.getLogger(__name__)


SQL_INJECTION_PATTERNS = [
    (r"(?:'|\"|;)\s*(?:OR|AND)\s+\d+\s*=\s*\d+", "Classic SQL injection (OR/AND)", "critical"),
    (r"(?:UNION\s+(?:ALL\s+)?SELECT)", "UNION-based injection", "critical"),
    (r"(?:DROP\s+TABLE|DROP\s+DATABASE)", "DROP statement", "critical"),
    (r"(?:INSERT\s+INTO.*VALUES.*--)", "INSERT injection with comment", "high"),
    (r"(?:UPDATE.*SET.*WHERE.*(?:'|\"|;))", "UPDATE injection", "high"),
    (r"(?:DELETE\s+FROM.*WHERE.*(?:'|\"|;))", "DELETE injection", "high"),
    (r"(?:EXEC(?:UTE)?\s+(?:sp_|xp_))", "Stored procedure execution", "high"),
    (r"(?:WAITFOR\s+DELAY|BENCHMARK\s*\(|SLEEP\s*\()", "Time-based injection", "high"),
    (r"(?:LOAD_FILE\s*\(|INTO\s+OUTFILE|INTO\s+DUMPFILE)", "File access injection", "critical"),
    (r"(?:1\s*=\s*1|'a'\s*=\s*'a'|\d+\s*=\s*\d+)", "Tautology injection", "medium"),
]


class DatabaseSecurityAuditor:
    """Audits database security configurations and queries."""

    def __init__(self):
        self.db = get_security_db()
        self.logger = logging.getLogger(__name__)

    def audit_sqlite_database(self, db_path: str) -> dict:
        """Audit a SQLite database for security issues."""
        findings = []
        path = Path(db_path)

        if not path.exists():
            return {"error": f"Database not found: {db_path}"}

        try:
            import sqlite3
            conn = sqlite3.connect(str(path))
            cursor = conn.cursor()

            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            if journal_mode != "wal":
                findings.append({
                    "title": "SQLite journal mode not set to WAL",
                    "severity": "low",
                    "category": "db_configuration",
                    "description": f"Current journal mode: {journal_mode}. WAL mode improves performance.",
                    "remediation": "Set PRAGMA journal_mode=WAL",
                })

            cursor.execute("PRAGMA foreign_keys")
            fk_status = cursor.fetchone()[0]
            if fk_status == 0:
                findings.append({
                    "title": "Foreign key constraints disabled",
                    "severity": "medium",
                    "category": "db_configuration",
                    "description": "Foreign key constraints are not enforced",
                    "remediation": "Enable with PRAGMA foreign_keys=ON",
                })

            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            for table_name, table_sql in tables:
                if table_sql and "WITHOUT ROWID" not in (table_sql or ""):
                    pass

            cursor.execute("SELECT sql FROM sqlite_master WHERE type='view'")
            views = cursor.fetchall()

            conn.close()

        except Exception as e:
            self.logger.error(f"Error auditing SQLite database: {e}")
            findings.append({
                "title": "Error auditing database",
                "severity": "info",
                "category": "audit_error",
                "description": str(e),
            })

        return {
            "database": db_path,
            "findings": findings,
            "total": len(findings),
        }

    def scan_sql_queries(self, queries: list[str]) -> list[dict]:
        """Scan SQL queries for injection patterns."""
        findings = []

        for i, query in enumerate(queries):
            for pattern, description, severity in SQL_INJECTION_PATTERNS:
                if re.search(pattern, query, re.IGNORECASE):
                    findings.append({
                        "query_index": i,
                        "title": f"SQL injection pattern: {description}",
                        "severity": severity,
                        "category": "sql_injection",
                        "description": f"Suspicious pattern detected in query",
                        "query_excerpt": query[:200],
                        "pattern": pattern,
                        "remediation": "Use parameterized queries or prepared statements",
                    })

        return findings

    def check_connection_string_security(self, connection_string: str) -> list[dict]:
        """Check connection string for security issues."""
        findings = []

        if re.search(r'password\s*=\s*[^;]+', connection_string, re.IGNORECASE):
            findings.append({
                "title": "Password in connection string",
                "severity": "high",
                "category": "credential_exposure",
                "description": "Database password is embedded in connection string",
                "remediation": "Use environment variables or a secrets manager for credentials",
            })

        if "sslmode=disable" in connection_string.lower():
            findings.append({
                "title": "SSL disabled in connection string",
                "severity": "high",
                "category": "insecure_connection",
                "description": "Database connection does not use encryption",
                "remediation": "Enable SSL/TLS for database connections",
            })

        if "trust_server_certificate=true" in connection_string.lower():
            findings.append({
                "title": "Server certificate trust enabled",
                "severity": "medium",
                "category": "insecure_connection",
                "description": "Server certificate is trusted without validation",
                "remediation": "Configure proper certificate validation",
            })

        return findings

    def audit_database_permissions(self, db_type: str = "sqlite",
                                     db_path: str = "") -> list[dict]:
        """Audit database user permissions."""
        findings = []

        if db_type == "sqlite":
            if db_path and Path(db_path).exists():
                import os
                file_stat = os.stat(db_path)
                mode = oct(file_stat.st_mode)[-3:]

                if int(mode[-1]) > 0:
                    findings.append({
                        "title": "Database file is world-readable/writable",
                        "severity": "high",
                        "category": "file_permissions",
                        "description": f"Database file permissions: {mode}",
                        "remediation": "Restrict file permissions to owner only (chmod 600)",
                    })

        return findings

    def comprehensive_db_audit(self, db_path: str, db_type: str = "sqlite",
                                 queries: Optional[list] = None,
                                 connection_string: str = "") -> dict:
        """Run comprehensive database security audit."""
        self.logger.info(f"[DB_AUDITOR] Starting database audit: {db_path}")

        all_findings = []

        if db_path:
            db_findings = self.audit_sqlite_database(db_path)
            all_findings.extend(db_findings.get("findings", []))

        perm_findings = self.audit_database_permissions(db_type, db_path)
        all_findings.extend(perm_findings)

        if queries:
            query_findings = self.scan_sql_queries(queries)
            all_findings.extend(query_findings)

        if connection_string:
            conn_findings = self.check_connection_string_security(connection_string)
            all_findings.extend(conn_findings)

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
            "findings": all_findings,
            "database": db_path,
            "db_type": db_type,
            "scan_time": time.time(),
        }

        scan_id = self.db.insert_scan_result(
            scan_type="database_audit",
            target=db_path or "database",
            status="completed",
            findings=scan_result
        )

        self.logger.info(f"[DB_AUDITOR] Audit complete: {len(all_findings)} findings")

        return {
            "scan_id": scan_id,
            "result": scan_result,
        }


_db_auditor: Optional[DatabaseSecurityAuditor] = None


def get_database_auditor() -> DatabaseSecurityAuditor:
    """Get singleton instance of DatabaseSecurityAuditor."""
    global _db_auditor
    if _db_auditor is None:
        _db_auditor = DatabaseSecurityAuditor()
    return _db_auditor
