"""
Ethical Hacking / Authorized Penetration Testing API Endpoints.

REST API for all ethical hacking operations with strict authorization controls.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ethical_hacking.core import (
    get_ethical_hacking_engine,
    TestMode,
)
from app.ethical_hacking.reconnaissance import get_recon_scanner
from app.ethical_hacking.vulnerability import get_vuln_assessor
from app.ethical_hacking.web_security import (
    get_web_security_tester,
    get_api_security_tester,
)
from app.ethical_hacking.network_config import (
    get_network_security_assessor,
    get_config_security_auditor,
)
from app.ethical_hacking.auth_misconfig import (
    get_auth_security_auditor,
    get_misconfig_detector,
)
from app.ethical_hacking.exploit_validation import get_safe_exploit_validator
from app.ethical_hacking.reporting import (
    get_evidence_collector,
    get_report_generator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ethical-hacking", tags=["ethical-hacking"])


# ============================================================================
# Request Models
# ============================================================================

class CreateScopeRequest(BaseModel):
    name: str
    targets: list[str]
    authorized_by: str
    excluded_targets: list[str] = Field(default_factory=list)
    allowed_ports: list[int] = Field(default_factory=list)
    excluded_ports: list[int] = Field(default_factory=list)
    test_types: list[str] = Field(default_factory=list)
    mode: str = "safe"
    duration_hours: float = 0

class PortScanRequest(BaseModel):
    host: str
    ports: Optional[list[int]] = None
    scope_id: Optional[str] = None
    timeout: float = 1.0

class VulnAssessRequest(BaseModel):
    host: str
    scope_id: Optional[str] = None
    ports: Optional[list[int]] = None

class WebTestRequest(BaseModel):
    url: str
    scope_id: Optional[str] = None

class APITestRequest(BaseModel):
    base_url: str
    endpoints: list[str] = Field(default_factory=list)
    scope_id: Optional[str] = None

class SecretScanRequest(BaseModel):
    directory: str
    scope_id: Optional[str] = None

class ExploitValidateRequest(BaseModel):
    finding_id: str
    scope_id: str
    validation_type: str = "safe"

class ReportRequest(BaseModel):
    scope_id: str
    report_format: str = "json"
    include_evidence: bool = True

class EvidenceRequest(BaseModel):
    finding_id: str
    evidence_type: str
    evidence_data: dict


# ============================================================================
# Scope Management
# ============================================================================

@router.post("/scope/create")
async def create_scope(req: CreateScopeRequest):
    try:
        engine = get_ethical_hacking_engine()
        scope = engine.create_test_scope(
            name=req.name,
            targets=req.targets,
            authorized_by=req.authorized_by,
            excluded_targets=req.excluded_targets,
            allowed_ports=req.allowed_ports,
            excluded_ports=req.excluded_ports,
            test_types=req.test_types,
            mode=TestMode(req.mode),
        )
        return {"success": True, "scope": scope}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scope/list")
async def list_scopes():
    engine = get_ethical_hacking_engine()
    return {
        "success": True,
        "active_scopes": engine.get_active_scopes(),
    }


@router.get("/scope/{scope_id}")
async def get_scope(scope_id: str):
    engine = get_ethical_hacking_engine()
    scope = engine.get_scope(scope_id)
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")
    return {"success": True, "scope": scope}


# ============================================================================
# Reconnaissance & Port Scanning
# ============================================================================

@router.post("/recon/port-scan")
async def port_scan(req: PortScanRequest):
    try:
        scanner = get_recon_scanner()
        result = scanner.port_scan(
            host=req.host,
            ports=req.ports,
            scope_id=req.scope_id,
            timeout=req.timeout,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recon/service-enum")
async def service_enumeration(host: str, port: int, scope_id: Optional[str] = None):
    try:
        scanner = get_recon_scanner()
        result = scanner.service_enumeration(host, port, scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recon/network-discovery")
async def network_discovery(network: str, scope_id: Optional[str] = None):
    try:
        scanner = get_recon_scanner()
        result = scanner.network_discovery(network, scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Vulnerability Assessment
# ============================================================================

@router.post("/vuln/assess")
async def vulnerability_assessment(req: VulnAssessRequest):
    try:
        assessor = get_vuln_assessor()
        result = assessor.assess_host(
            host=req.host,
            scope_id=req.scope_id,
            ports=req.ports,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vuln/cve/{cve_id}")
async def get_cve_info(cve_id: str):
    assessor = get_vuln_assessor()
    info = assessor.get_cve_info(cve_id)
    if not info:
        raise HTTPException(status_code=404, detail="CVE not found in local database")
    return {"success": True, "cve_id": cve_id, "info": info}


@router.get("/vuln/known/{service}/{version}")
async def check_known_vulns(service: str, version: str):
    assessor = get_vuln_assessor()
    vulns = assessor.check_known_vulnerabilities(service, version)
    return {"success": True, "service": service, "version": version, "vulnerabilities": vulns}


# ============================================================================
# Web Application Security Testing
# ============================================================================

@router.post("/web/comprehensive")
async def web_comprehensive_test(req: WebTestRequest):
    try:
        tester = get_web_security_tester()
        result = tester.comprehensive_test(req.url, req.scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web/headers")
async def web_security_headers(req: WebTestRequest):
    try:
        tester = get_web_security_tester()
        result = tester.test_security_headers(req.url, req.scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web/ssl")
async def web_ssl_test(req: WebTestRequest):
    try:
        tester = get_web_security_tester()
        result = tester.test_ssl_tls(req.url, req.scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web/xss")
async def web_xss_test(req: WebTestRequest):
    try:
        tester = get_web_security_tester()
        result = tester.test_xss(req.url, req.scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web/traversal")
async def web_traversal_test(req: WebTestRequest):
    try:
        tester = get_web_security_tester()
        result = tester.test_directory_traversal(req.url, req.scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Security Testing
# ============================================================================

@router.post("/api/test-auth")
async def api_auth_test(req: APITestRequest):
    try:
        tester = get_api_security_tester()
        result = tester.test_authentication(req.base_url, req.endpoints, req.scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/test-cors")
async def api_cors_test(base_url: str, scope_id: Optional[str] = None):
    try:
        tester = get_api_security_tester()
        result = tester.test_cors(base_url, scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/test-rate-limit")
async def api_rate_limit_test(base_url: str, endpoint: str = "/", scope_id: Optional[str] = None):
    try:
        tester = get_api_security_tester()
        result = tester.test_rate_limiting(base_url, endpoint, scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Network Security Assessment
# ============================================================================

@router.post("/network/comprehensive")
async def network_comprehensive(scope_id: Optional[str] = None):
    try:
        assessor = get_network_security_assessor()
        result = assessor.comprehensive_network_assessment(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/network/open-ports")
async def network_open_ports(scope_id: Optional[str] = None):
    try:
        assessor = get_network_security_assessor()
        result = assessor.check_open_ports_system(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/network/firewall")
async def network_firewall(scope_id: Optional[str] = None):
    try:
        assessor = get_network_security_assessor()
        result = assessor.check_firewall_status(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/network/shares")
async def network_shares(scope_id: Optional[str] = None):
    try:
        assessor = get_network_security_assessor()
        result = assessor.check_network_shares(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Configuration Security Testing
# ============================================================================

@router.post("/config/comprehensive")
async def config_comprehensive(scope_id: Optional[str] = None):
    try:
        auditor = get_config_security_auditor()
        result = auditor.comprehensive_config_audit(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/windows")
async def config_windows(scope_id: Optional[str] = None):
    try:
        auditor = get_config_security_auditor()
        result = auditor.audit_windows_config(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/file-permissions")
async def config_file_permissions(path: str, scope_id: Optional[str] = None):
    try:
        auditor = get_config_security_auditor()
        result = auditor.audit_file_permissions(path, scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/env-secrets")
async def config_env_secrets(scope_id: Optional[str] = None):
    try:
        auditor = get_config_security_auditor()
        result = auditor.audit_environment_variables(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Authentication Security Audit
# ============================================================================

@router.post("/auth/comprehensive")
async def auth_comprehensive(scope_id: Optional[str] = None):
    try:
        auditor = get_auth_security_auditor()
        result = auditor.comprehensive_auth_audit(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/password-policy")
async def auth_password_policy(scope_id: Optional[str] = None):
    try:
        auditor = get_auth_security_auditor()
        result = auditor.audit_password_policy(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/user-accounts")
async def auth_user_accounts(scope_id: Optional[str] = None):
    try:
        auditor = get_auth_security_auditor()
        result = auditor.audit_user_accounts(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/admin-accounts")
async def auth_admin_accounts(scope_id: Optional[str] = None):
    try:
        auditor = get_auth_security_auditor()
        result = auditor.audit_admin_accounts(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Security Misconfiguration Detection
# ============================================================================

@router.post("/misconfig/comprehensive")
async def misconfig_comprehensive(scope_id: Optional[str] = None):
    try:
        detector = get_misconfig_detector()
        result = detector.comprehensive_misconfig_check(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/misconfig/exposed-services")
async def misconfig_exposed_services(scope_id: Optional[str] = None):
    try:
        detector = get_misconfig_detector()
        result = detector.detect_exposed_services(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/misconfig/exposed-secrets")
async def misconfig_exposed_secrets(req: SecretScanRequest):
    try:
        detector = get_misconfig_detector()
        result = detector.detect_exposed_secrets(req.directory, req.scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/misconfig/weak-settings")
async def misconfig_weak_settings(scope_id: Optional[str] = None):
    try:
        detector = get_misconfig_detector()
        result = detector.detect_weak_security_settings(scope_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Safe Exploit Validation
# ============================================================================

@router.post("/exploit/validate")
async def exploit_validate(req: ExploitValidateRequest):
    try:
        validator = get_safe_exploit_validator()
        result = validator.validate_vulnerability(
            finding_id=req.finding_id,
            scope_id=req.scope_id,
            validation_type=req.validation_type,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/exploit/history")
async def exploit_validation_history(limit: int = 50):
    validator = get_safe_exploit_validator()
    return {
        "success": True,
        "history": validator.get_validation_history(limit),
        "stats": validator.get_validation_stats(),
    }


# ============================================================================
# Evidence Collection
# ============================================================================

@router.post("/evidence/collect")
async def collect_evidence(req: EvidenceRequest):
    try:
        collector = get_evidence_collector()
        result = collector.collect_evidence(
            finding_id=req.finding_id,
            evidence_type=req.evidence_type,
            evidence_data=req.evidence_data,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/evidence/{finding_id}")
async def get_finding_evidence(finding_id: str):
    collector = get_evidence_collector()
    return {
        "success": True,
        "finding_id": finding_id,
        "evidence": collector.get_evidence(finding_id),
    }


@router.get("/evidence")
async def get_all_evidence(scope_id: Optional[str] = None):
    collector = get_evidence_collector()
    return {
        "success": True,
        "evidence_map": collector.get_all_evidence(scope_id),
    }


# ============================================================================
# Report Generation
# ============================================================================

@router.post("/report/generate")
async def generate_report(req: ReportRequest):
    try:
        generator = get_report_generator()
        result = generator.generate_report(
            scope_id=req.scope_id,
            report_format=req.report_format,
            include_evidence=req.include_evidence,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Findings & Stats
# ============================================================================

@router.get("/findings")
async def get_findings(scope_id: Optional[str] = None, severity: Optional[str] = None, limit: int = 100):
    engine = get_ethical_hacking_engine()
    return {
        "success": True,
        "findings": engine.get_findings(scope_id, severity, limit),
    }


@router.get("/findings/{finding_id}")
async def get_finding(finding_id: str):
    engine = get_ethical_hacking_engine()
    finding = engine.get_finding(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return {"success": True, "finding": finding}


@router.get("/stats")
async def get_stats():
    engine = get_ethical_hacking_engine()
    return {
        "success": True,
        "stats": engine.get_stats(),
    }


@router.get("/audit-log")
async def get_audit_log(limit: int = 50):
    engine = get_ethical_hacking_engine()
    return {
        "success": True,
        "audit_log": engine.scope_manager.get_audit_log(limit),
    }


@router.get("/blocked-actions")
async def get_blocked_actions(limit: int = 50):
    engine = get_ethical_hacking_engine()
    return {
        "success": True,
        "blocked_actions": engine.safety_controller.get_blocked_actions(limit),
    }
