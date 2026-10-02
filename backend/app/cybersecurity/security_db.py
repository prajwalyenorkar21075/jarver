"""Security database models for JARVIS cybersecurity module."""

import sqlite3
import logging
import time
import json
import uuid
from typing import Optional, Any
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

SECURITY_DB_PATH = Path(__file__).parent.parent.parent / "security.db"


class SecurityDatabase:
    """Manages security-related database tables and operations."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or SECURITY_DB_PATH
        self._init_database()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[SECURITY_DB] Error: {e}")
            raise
        finally:
            conn.close()

    def _init_database(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    source TEXT,
                    description TEXT,
                    details TEXT,
                    resolved INTEGER DEFAULT 0,
                    resolved_at REAL,
                    resolved_by TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_alerts (
                    id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    source TEXT,
                    affected_system TEXT,
                    indicators TEXT,
                    recommended_actions TEXT,
                    status TEXT DEFAULT 'active',
                    acknowledged INTEGER DEFAULT 0,
                    acknowledged_at REAL,
                    acknowledged_by TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vulnerabilities (
                    id TEXT PRIMARY KEY,
                    discovered_at REAL NOT NULL,
                    vuln_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    cve_id TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    affected_system TEXT,
                    affected_component TEXT,
                    cvss_score REAL,
                    exploit_available INTEGER DEFAULT 0,
                    patch_available INTEGER DEFAULT 0,
                    remediation TEXT,
                    status TEXT DEFAULT 'open',
                    resolved_at REAL,
                    resolved_by TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_results (
                    id TEXT PRIMARY KEY,
                    scan_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    target TEXT,
                    status TEXT NOT NULL,
                    findings_count INTEGER DEFAULT 0,
                    critical_count INTEGER DEFAULT 0,
                    high_count INTEGER DEFAULT 0,
                    medium_count INTEGER DEFAULT 0,
                    low_count INTEGER DEFAULT 0,
                    results_summary TEXT,
                    raw_results TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_integrity (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    hash_algorithm TEXT DEFAULT 'sha256',
                    file_size INTEGER,
                    last_modified REAL,
                    baseline_hash TEXT,
                    baseline_at REAL,
                    status TEXT DEFAULT 'baseline',
                    change_detected_at REAL,
                    change_type TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    created_at REAL NOT NULL,
                    incident_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    affected_systems TEXT,
                    indicators TEXT,
                    timeline TEXT,
                    response_actions TEXT,
                    status TEXT DEFAULT 'detected',
                    assigned_to TEXT,
                    resolved_at REAL,
                    resolved_by TEXT,
                    post_mortem TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT,
                    target TEXT,
                    result TEXT,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_reports (
                    id TEXT PRIMARY KEY,
                    report_type TEXT NOT NULL,
                    generated_at REAL NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    findings TEXT,
                    recommendations TEXT,
                    metrics TEXT,
                    format TEXT DEFAULT 'json',
                    file_path TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS threat_intelligence (
                    id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    threat_type TEXT NOT NULL,
                    source TEXT,
                    indicator TEXT,
                    indicator_type TEXT,
                    severity TEXT,
                    description TEXT,
                    ref_links TEXT,
                    confidence INTEGER DEFAULT 50
                )
            """)

            for table in ['security_events', 'security_alerts', 'scan_results',
                          'audit_logs', 'threat_intelligence']:
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table}_timestamp
                    ON {table}(timestamp)
                """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vulnerabilities_discovered
                ON vulnerabilities(discovered_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_incidents_created
                ON incidents(created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_security_reports_generated
                ON security_reports(generated_at)
            """)

            logger.info("[SECURITY_DB] Security database initialized with 9 tables")

            logger.info("[SECURITY_DB] Security database initialized with 9 tables")

    def generate_id(self) -> str:
        return str(uuid.uuid4())[:12]

    def insert_event(self, event_type: str, severity: str, description: str,
                     source: str = "", details: Optional[dict] = None) -> str:
        event_id = self.generate_id()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO security_events (id, timestamp, event_type, severity, source, description, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (event_id, time.time(), event_type, severity, source, description,
                  json.dumps(details) if details else None))
        return event_id

    def insert_alert(self, alert_type: str, severity: str, title: str,
                     description: str = "", source: str = "", **kwargs) -> str:
        alert_id = self.generate_id()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO security_alerts
                (id, timestamp, alert_type, severity, title, description, source,
                 affected_system, indicators, recommended_actions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (alert_id, time.time(), alert_type, severity, title, description, source,
                  kwargs.get('affected_system'), json.dumps(kwargs.get('indicators', [])),
                  json.dumps(kwargs.get('recommended_actions', []))))
        return alert_id

    def insert_vulnerability(self, vuln_type: str, severity: str, title: str,
                             affected_system: str = "", **kwargs) -> str:
        vuln_id = self.generate_id()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO vulnerabilities
                (id, discovered_at, vuln_type, severity, cve_id, title, description,
                 affected_system, affected_component, cvss_score, exploit_available,
                 patch_available, remediation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (vuln_id, time.time(), vuln_type, severity, kwargs.get('cve_id'),
                  title, kwargs.get('description'), affected_system,
                  kwargs.get('affected_component'), kwargs.get('cvss_score'),
                  1 if kwargs.get('exploit_available') else 0,
                  1 if kwargs.get('patch_available') else 0,
                  kwargs.get('remediation')))
        return vuln_id

    def insert_scan_result(self, scan_type: str, target: str, status: str,
                           findings: dict) -> str:
        scan_id = self.generate_id()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO scan_results
                (id, scan_type, timestamp, target, status, findings_count,
                 critical_count, high_count, medium_count, low_count,
                 results_summary, raw_results)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (scan_id, scan_type, time.time(), target, status,
                  findings.get('total', 0), findings.get('critical', 0),
                  findings.get('high', 0), findings.get('medium', 0),
                  findings.get('low', 0), findings.get('summary'),
                  json.dumps(findings.get('findings', findings.get('details', [])))))
        return scan_id

    def insert_file_baseline(self, file_path: str, file_hash: str,
                             file_size: int, last_modified: float) -> str:
        file_id = self.generate_id()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO file_integrity
                (id, file_path, file_hash, file_size, last_modified, baseline_hash, baseline_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (file_id, file_path, file_hash, file_size, last_modified,
                  file_hash, time.time()))
        return file_id

    def insert_incident(self, incident_type: str, severity: str, title: str,
                        description: str = "", **kwargs) -> str:
        incident_id = self.generate_id()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO incidents
                (id, created_at, incident_type, severity, title, description,
                 affected_systems, indicators, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (incident_id, time.time(), incident_type, severity, title,
                  description, json.dumps(kwargs.get('affected_systems', [])),
                  json.dumps(kwargs.get('indicators', [])), 'detected'))
        return incident_id

    def insert_audit_log(self, action: str, actor: str = "", target: str = "",
                         result: str = "", **kwargs) -> str:
        log_id = self.generate_id()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO audit_logs
                (id, timestamp, action, actor, target, result, details, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (log_id, time.time(), action, actor, target, result,
                  json.dumps(kwargs.get('details', {})), kwargs.get('ip_address'),
                  kwargs.get('user_agent')))
        return log_id

    def get_recent_events(self, limit: int = 50, severity: Optional[str] = None) -> list[dict]:
        with self._get_connection() as conn:
            if severity:
                rows = conn.execute("""
                    SELECT * FROM security_events WHERE severity = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (severity, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM security_events ORDER BY timestamp DESC LIMIT ?
                """, (limit,)).fetchall()
        return [dict(row) for row in rows]

    def get_active_alerts(self, limit: int = 50) -> list[dict]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM security_alerts WHERE status = 'active'
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
        return [dict(row) for row in rows]

    def get_open_vulnerabilities(self, severity: Optional[str] = None) -> list[dict]:
        with self._get_connection() as conn:
            if severity:
                rows = conn.execute("""
                    SELECT * FROM vulnerabilities WHERE status = 'open' AND severity = ?
                    ORDER BY discovered_at DESC
                """, (severity,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM vulnerabilities WHERE status = 'open'
                    ORDER BY discovered_at DESC
                """).fetchall()
        return [dict(row) for row in rows]

    def get_security_stats(self) -> dict:
        with self._get_connection() as conn:
            events_count = conn.execute("SELECT COUNT(*) FROM security_events").fetchone()[0]
            alerts_count = conn.execute("SELECT COUNT(*) FROM security_alerts WHERE status = 'active'").fetchone()[0]
            vulns_count = conn.execute("SELECT COUNT(*) FROM vulnerabilities WHERE status = 'open'").fetchone()[0]
            incidents_count = conn.execute("SELECT COUNT(*) FROM incidents WHERE status != 'resolved'").fetchone()[0]
            critical_alerts = conn.execute("SELECT COUNT(*) FROM security_alerts WHERE severity = 'critical' AND status = 'active'").fetchone()[0]
            high_vulns = conn.execute("SELECT COUNT(*) FROM vulnerabilities WHERE severity IN ('critical', 'high') AND status = 'open'").fetchone()[0]

        return {
            "total_events": events_count,
            "active_alerts": alerts_count,
            "open_vulnerabilities": vulns_count,
            "active_incidents": incidents_count,
            "critical_alerts": critical_alerts,
            "high_severity_vulns": high_vulns,
        }


_security_db: Optional[SecurityDatabase] = None


def get_security_db() -> SecurityDatabase:
    global _security_db
    if _security_db is None:
        _security_db = SecurityDatabase()
    return _security_db
