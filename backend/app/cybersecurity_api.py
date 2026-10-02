"""
Cybersecurity API endpoints for JARVIS.

Provides REST API for all 20 cybersecurity capabilities.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cybersecurity", tags=["cybersecurity"])


class ScanRequest(BaseModel):
    target: str = ""
    path: str = ""
    options: dict = Field(default_factory=dict)


class WebAnalysisRequest(BaseModel):
    url: str
    headers: Optional[dict] = None
    cookies: Optional[list] = None
    response_content: str = ""


class CodeScanRequest(BaseModel):
    path: str
    extensions: Optional[list] = None


class DependencyScanRequest(BaseModel):
    project_path: str


class FileIntegrityRequest(BaseModel):
    path: str
    directory: Optional[str] = None
    extensions: Optional[list] = None


class MalwareAnalysisRequest(BaseModel):
    file_path: str


class LogAnalysisRequest(BaseModel):
    log_paths: Optional[list] = None


class AuthRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class SessionRequest(BaseModel):
    session_id: str


class SecretScanRequest(BaseModel):
    target_path: str


class DatabaseAuditRequest(BaseModel):
    db_path: str
    db_type: str = "sqlite"
    queries: Optional[list] = None
    connection_string: str = ""


class AlertRequest(BaseModel):
    alert_type: str
    severity: str
    title: str
    description: str = ""
    source: str = ""
    affected_system: str = ""


class IncidentRequest(BaseModel):
    incident_type: str
    severity: str
    title: str
    description: str = ""
    affected_systems: Optional[list] = None


class BackupRequest(BaseModel):
    backup_path: str
    backup_type: str = "full"
    max_age_hours: int = 24


class PrivacyScanRequest(BaseModel):
    target_path: str
    text: str = ""


class ReportRequest(BaseModel):
    report_type: str = "executive_summary"
    framework: str = "OWASP"
    days: int = 30


@router.get("/status")
async def get_security_status():
    """Get overall cybersecurity status."""
    try:
        from app.cybersecurity import get_security_db, get_alert_manager
        db = get_security_db()
        alert_mgr = get_alert_manager()

        stats = db.get_security_stats()
        alert_summary = alert_mgr.get_alert_summary()

        return {
            "status": "operational",
            "stats": stats,
            "alert_summary": alert_summary,
        }
    except Exception as e:
        logger.error(f"Error getting security status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/threat/scan")
async def run_threat_scan():
    """Run comprehensive threat detection scan."""
    try:
        from app.cybersecurity import get_threat_detection_engine
        engine = get_threat_detection_engine()
        result = engine.comprehensive_threat_scan()
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error in threat scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/endpoint/check")
async def run_endpoint_check():
    """Run Windows endpoint security check."""
    try:
        from app.cybersecurity import get_windows_endpoint_security
        endpoint = get_windows_endpoint_security()
        result = endpoint.comprehensive_endpoint_check()
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error in endpoint check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/network/check")
async def run_network_check():
    """Run network security check."""
    try:
        from app.cybersecurity import get_network_security_monitor
        monitor = get_network_security_monitor()
        result = monitor.comprehensive_network_check()
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error in network check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vulnerability/scan")
async def run_vulnerability_scan():
    """Run vulnerability scan."""
    try:
        from app.cybersecurity import get_vulnerability_scanner
        scanner = get_vulnerability_scanner()
        result = scanner.comprehensive_vulnerability_scan()
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error in vulnerability scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web/analyze")
async def analyze_web_application(request: WebAnalysisRequest):
    """Analyze web application security."""
    try:
        from app.cybersecurity import get_web_application_analyzer
        analyzer = get_web_application_analyzer()
        result = analyzer.analyze_web_application(
            url=request.url,
            headers=request.headers,
            cookies=request.cookies,
            response_content=request.response_content,
        )
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error in web analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code/scan")
async def scan_code(request: CodeScanRequest):
    """Scan source code for security issues."""
    try:
        from app.cybersecurity import get_secure_code_analyzer
        analyzer = get_secure_code_analyzer()
        result = analyzer.scan_project(request.path)
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error in code scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dependency/scan")
async def scan_dependencies(request: DependencyScanRequest):
    """Scan project dependencies for vulnerabilities."""
    try:
        from app.cybersecurity import get_dependency_scanner
        scanner = get_dependency_scanner()
        result = scanner.comprehensive_dependency_scan(request.project_path)
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error in dependency scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrity/baseline")
async def create_integrity_baseline(request: FileIntegrityRequest):
    """Create file integrity baseline."""
    try:
        from app.cybersecurity import get_file_integrity_monitor
        monitor = get_file_integrity_monitor()

        if request.directory:
            result = monitor.create_baseline_directory(
                request.directory, extensions=request.extensions
            )
        else:
            result = monitor.create_baseline(request.path)

        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error creating baseline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrity/verify")
async def verify_integrity(request: FileIntegrityRequest):
    """Verify file integrity."""
    try:
        from app.cybersecurity import get_file_integrity_monitor
        monitor = get_file_integrity_monitor()

        if request.directory:
            result = monitor.verify_directory(request.directory)
        else:
            result = monitor.verify_file(request.path)

        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error verifying integrity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/malware/analyze")
async def analyze_file(request: MalwareAnalysisRequest):
    """Analyze file for malware indicators."""
    try:
        from app.cybersecurity import get_malware_analyzer
        analyzer = get_malware_analyzer()
        result = analyzer.comprehensive_file_analysis(request.file_path)
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error in malware analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logs/analyze")
async def analyze_logs(request: LogAnalysisRequest):
    """Analyze logs for suspicious activity."""
    try:
        from app.cybersecurity import get_log_analyzer
        analyzer = get_log_analyzer()
        result = analyzer.comprehensive_log_analysis(log_paths=request.log_paths)
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error in log analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/register")
async def register_user(request: AuthRequest):
    """Register a new user."""
    try:
        from app.cybersecurity import get_auth_manager
        auth = get_auth_manager()
        result = auth.register_user(request.username, request.password, request.role)
        return result
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/login")
async def login(request: AuthRequest):
    """Authenticate user."""
    try:
        from app.cybersecurity import get_auth_manager
        auth = get_auth_manager()
        result = auth.authenticate(request.username, request.password)
        return result
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/validate")
async def validate_session(request: SessionRequest):
    """Validate session."""
    try:
        from app.cybersecurity import get_auth_manager
        auth = get_auth_manager()
        result = auth.validate_session(request.session_id)
        return result
    except Exception as e:
        logger.error(f"Error validating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/stats")
async def get_auth_stats():
    """Get authentication statistics."""
    try:
        from app.cybersecurity import get_auth_manager
        auth = get_auth_manager()
        return auth.get_auth_stats()
    except Exception as e:
        logger.error(f"Error getting auth stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/secrets/scan")
async def scan_secrets(request: SecretScanRequest):
    """Scan for exposed secrets."""
    try:
        from app.cybersecurity import get_secret_scanner
        scanner = get_secret_scanner()
        result = scanner.comprehensive_secret_scan(request.target_path)
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error in secret scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database/audit")
async def audit_database(request: DatabaseAuditRequest):
    """Audit database security."""
    try:
        from app.cybersecurity import get_database_auditor
        auditor = get_database_auditor()
        result = auditor.comprehensive_db_audit(
            db_path=request.db_path,
            db_type=request.db_type,
            queries=request.queries,
            connection_string=request.connection_string,
        )
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error in database audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(severity: Optional[str] = None, limit: int = 50):
    """Get active security alerts."""
    try:
        from app.cybersecurity import get_alert_manager
        alert_mgr = get_alert_manager()
        alerts = alert_mgr.get_active_alerts(severity=severity, limit=limit)
        return {"alerts": alerts, "total": len(alerts)}
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/create")
async def create_alert(request: AlertRequest):
    """Create a security alert."""
    try:
        from app.cybersecurity import get_alert_manager
        alert_mgr = get_alert_manager()
        result = alert_mgr.create_alert(
            alert_type=request.alert_type,
            severity=request.severity,
            title=request.title,
            description=request.description,
            source=request.source,
            affected_system=request.affected_system,
        )
        return result
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/incident/create")
async def create_incident(request: IncidentRequest):
    """Create a security incident."""
    try:
        from app.cybersecurity import get_incident_response_engine
        engine = get_incident_response_engine()
        result = engine.create_incident(
            incident_type=request.incident_type,
            severity=request.severity,
            title=request.title,
            description=request.description,
            affected_systems=request.affected_systems,
        )
        return result
    except Exception as e:
        logger.error(f"Error creating incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents")
async def get_incidents():
    """Get active incidents."""
    try:
        from app.cybersecurity import get_incident_response_engine
        engine = get_incident_response_engine()
        incidents = engine.get_active_incidents()
        stats = engine.get_incident_stats()
        return {"incidents": incidents, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/verify")
async def verify_backups(request: BackupRequest):
    """Verify backup integrity."""
    try:
        from app.cybersecurity import get_backup_verifier
        verifier = get_backup_verifier()
        result = verifier.verify_backup_integrity(request.backup_path)
        freshness = verifier.check_backup_freshness(request.backup_path, request.max_age_hours)
        return {"integrity": result, "freshness": freshness}
    except Exception as e:
        logger.error(f"Error verifying backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/register")
async def register_backup(request: BackupRequest):
    """Register a backup for monitoring."""
    try:
        from app.cybersecurity import get_backup_verifier
        verifier = get_backup_verifier()
        result = verifier.register_backup(
            request.backup_path, request.backup_type
        )
        return result
    except Exception as e:
        logger.error(f"Error registering backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/privacy/scan")
async def scan_privacy(request: PrivacyScanRequest):
    """Scan for PII and privacy issues."""
    try:
        from app.cybersecurity import get_privacy_protection
        privacy = get_privacy_protection()

        if request.text:
            findings = privacy.detect_pii(request.text)
            classification = privacy.classify_data(request.text)
            return {"findings": findings, "classification": classification}
        else:
            result = privacy.scan_directory_for_pii(request.target_path)
            return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error in privacy scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/privacy/redact")
async def redact_text(request: PrivacyScanRequest):
    """Redact PII from text."""
    try:
        from app.cybersecurity import get_privacy_protection
        privacy = get_privacy_protection()
        redacted = privacy.redact_text(request.text)
        return {"original_length": len(request.text), "redacted_text": redacted}
    except Exception as e:
        logger.error(f"Error redacting text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/owasp")
async def get_owasp_top_10():
    """Get OWASP Top 10."""
    try:
        from app.cybersecurity import get_security_knowledge_base
        kb = get_security_knowledge_base()
        return kb.get_owasp_top_10()
    except Exception as e:
        logger.error(f"Error getting OWASP data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/cwe")
async def get_cwe_list():
    """Get CWE list."""
    try:
        from app.cybersecurity import get_security_knowledge_base
        kb = get_security_knowledge_base()
        return kb.get_all_cwes()
    except Exception as e:
        logger.error(f"Error getting CWE data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/search")
async def search_knowledge(query: str):
    """Search security knowledge base."""
    try:
        from app.cybersecurity import get_security_knowledge_base
        kb = get_security_knowledge_base()
        results = kb.search_knowledge(query)
        return {"query": query, "results": results, "total": len(results)}
    except Exception as e:
        logger.error(f"Error searching knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report/generate")
async def generate_report(request: ReportRequest):
    """Generate security report."""
    try:
        from app.cybersecurity import get_report_generator
        generator = get_report_generator()
        result = generator.generate_report(
            report_type=request.report_type,
            framework=request.framework,
            days=request.days,
        )
        return {"status": "completed", "report": result}
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
async def get_security_events(limit: int = 50, severity: Optional[str] = None):
    """Get recent security events."""
    try:
        from app.cybersecurity import get_security_db
        db = get_security_db()
        events = db.get_recent_events(limit=limit, severity=severity)
        return {"events": events, "total": len(events)}
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vulnerabilities")
async def get_vulnerabilities(severity: Optional[str] = None):
    """Get open vulnerabilities."""
    try:
        from app.cybersecurity import get_security_db
        db = get_security_db()
        vulns = db.get_open_vulnerabilities(severity=severity)
        return {"vulnerabilities": vulns, "total": len(vulns)}
    except Exception as e:
        logger.error(f"Error getting vulnerabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/full-scan")
async def run_full_security_scan():
    """Run comprehensive security scan across all modules."""
    try:
        from app.cybersecurity import (
            get_threat_detection_engine,
            get_windows_endpoint_security,
            get_network_security_monitor,
            get_vulnerability_scanner,
            get_log_analyzer,
        )

        results = {}

        threat_engine = get_threat_detection_engine()
        results["threat_detection"] = threat_engine.comprehensive_threat_scan()

        endpoint = get_windows_endpoint_security()
        results["endpoint_security"] = endpoint.comprehensive_endpoint_check()

        network = get_network_security_monitor()
        results["network_security"] = network.comprehensive_network_check()

        vuln_scanner = get_vulnerability_scanner()
        results["vulnerability_scan"] = vuln_scanner.comprehensive_vulnerability_scan()

        log_analyzer = get_log_analyzer()
        results["log_analysis"] = log_analyzer.comprehensive_log_analysis()

        total_findings = sum(
            r.get("total", r.get("total_findings", 0))
            for r in results.values()
            if isinstance(r, dict)
        )

        return {
            "status": "completed",
            "total_findings": total_findings,
            "results": results,
        }
    except Exception as e:
        logger.error(f"Error in full scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))
