"""
Authentication Security Audit and Security Misconfiguration Detection.

Audits authentication mechanisms, password policies, and detects security
misconfigurations across systems.
"""

import logging
import subprocess
import platform
import re
from typing import Optional
from pathlib import Path

from .core import get_ethical_hacking_engine, Severity

logger = logging.getLogger(__name__)


class AuthenticationSecurityAuditor:
    """Audits authentication and access control mechanisms."""

    def __init__(self):
        self.engine = get_ethical_hacking_engine()
        logger.info("[AUTH_SEC] Authentication security auditor initialized")

    def audit_password_policy(self, scope_id: Optional[str] = None) -> dict:
        findings = []

        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["net", "accounts"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout

                min_length_match = re.search(r"Minimum password length:\s*(\d+)", output)
                if min_length_match:
                    min_length = int(min_length_match.group(1))
                    if min_length < 8:
                        finding = self.engine.add_finding(
                            finding_type="weak_password_policy",
                            severity="high",
                            title="Weak Password Length Requirement",
                            description=f"Minimum password length is {min_length} characters (should be at least 8)",
                            target="localhost",
                            scope_id=scope_id or "",
                            evidence={"min_length": min_length},
                            affected_component="Password Policy",
                            remediation="Increase minimum password length to at least 12 characters",
                        )
                        findings.append(finding)

                max_age_match = re.search(r"Maximum password age \(days\):\s*(\d+)", output)
                if max_age_match:
                    max_age = int(max_age_match.group(1))
                    if max_age > 90 or max_age == -1:
                        finding = self.engine.add_finding(
                            finding_type="weak_password_policy",
                            severity="medium",
                            title="Password Maximum Age Too Long",
                            description=f"Password maximum age is {max_age} days (should be 90 or less)",
                            target="localhost",
                            scope_id=scope_id or "",
                            evidence={"max_age": max_age},
                            affected_component="Password Policy",
                            remediation="Set maximum password age to 90 days or less",
                        )
                        findings.append(finding)

        except Exception as e:
            logger.error(f"[AUTH_SEC] Error auditing password policy: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def audit_user_accounts(self, scope_id: Optional[str] = None) -> dict:
        findings = []

        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["net", "user"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout

                lines = output.split('\n')
                user_list_started = False
                for line in lines:
                    if '-------' in line:
                        user_list_started = True
                        continue
                    if user_list_started and line.strip():
                        users = [u.strip() for u in line.split() if u.strip()]
                        for user in users:
                            if user.lower() in ['guest', 'defaultaccount']:
                                finding = self.engine.add_finding(
                                    finding_type="default_account",
                                    severity="medium",
                                    title=f"Default/Guest Account Detected: {user}",
                                    description=f"Account {user} should be disabled or removed",
                                    target="localhost",
                                    scope_id=scope_id or "",
                                    evidence={"account": user},
                                    affected_component="User Accounts",
                                    remediation=f"Disable or remove the {user} account",
                                )
                                findings.append(finding)

        except Exception as e:
            logger.error(f"[AUTH_SEC] Error auditing user accounts: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def audit_admin_accounts(self, scope_id: Optional[str] = None) -> dict:
        findings = []

        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["net", "localgroup", "administrators"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout

                lines = output.split('\n')
                member_list_started = False
                admin_count = 0

                for line in lines:
                    if '-------' in line:
                        member_list_started = True
                        continue
                    if member_list_started and line.strip() and 'command completed' not in line.lower():
                        admin_count += 1

                if admin_count > 3:
                    finding = self.engine.add_finding(
                        finding_type="excessive_admins",
                        severity="medium",
                        title="Excessive Administrator Accounts",
                        description=f"Found {admin_count} administrator accounts (should be minimized)",
                        target="localhost",
                        scope_id=scope_id or "",
                        evidence={"admin_count": admin_count},
                        affected_component="Administrative Access",
                        remediation="Reduce number of administrator accounts to only those necessary",
                    )
                    findings.append(finding)

        except Exception as e:
            logger.error(f"[AUTH_SEC] Error auditing admin accounts: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def comprehensive_auth_audit(self, scope_id: Optional[str] = None) -> dict:
        logger.info("[AUTH_SEC] Starting comprehensive authentication audit")

        all_findings = []

        audits = [
            lambda: self.audit_password_policy(scope_id),
            lambda: self.audit_user_accounts(scope_id),
            lambda: self.audit_admin_accounts(scope_id),
        ]

        for audit in audits:
            try:
                result = audit()
                if result["success"]:
                    all_findings.extend(result["findings"])
            except Exception as e:
                logger.error(f"[AUTH_SEC] Audit failed: {e}")

        logger.info(f"[AUTH_SEC] Authentication audit complete: {len(all_findings)} findings")

        return {
            "success": True,
            "findings": all_findings,
            "total_findings": len(all_findings),
        }


class SecurityMisconfigurationDetector:
    """Detects security misconfigurations across systems."""

    def __init__(self):
        self.engine = get_ethical_hacking_engine()
        logger.info("[MISCONFIG] Security misconfiguration detector initialized")

    def detect_unsafe_permissions(self, path: str, scope_id: Optional[str] = None) -> dict:
        findings = []

        try:
            file_path = Path(path)
            if not file_path.exists():
                return {"success": False, "error": "Path does not exist", "findings": []}

            if platform.system() != "Windows":
                import stat
                mode = file_path.stat().st_mode

                if file_path.is_file() and (mode & stat.S_IWOTH):
                    finding = self.engine.add_finding(
                        finding_type="unsafe_permissions",
                        severity="high",
                        title="World-Writable File",
                        description=f"File {path} can be modified by any user",
                        target=path,
                        scope_id=scope_id or "",
                        evidence={"path": path, "mode": oct(mode)},
                        affected_component="File Permissions",
                        remediation="Remove world-writable permission",
                    )
                    findings.append(finding)

        except Exception as e:
            logger.error(f"[MISCONFIG] Error detecting unsafe permissions: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def detect_exposed_services(self, scope_id: Optional[str] = None) -> dict:
        findings = []

        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["netstat", "-an"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout

                for line in output.split('\n'):
                    if 'LISTENING' in line and '0.0.0.0:' in line:
                        match = re.search(r'0\.0\.0\.0:(\d+)', line)
                        if match:
                            port = int(match.group(1))
                            if port not in [80, 443]:
                                finding = self.engine.add_finding(
                                    finding_type="exposed_service",
                                    severity="medium",
                                    title=f"Service Listening on All Interfaces: Port {port}",
                                    description=f"Service on port {port} is accessible from all network interfaces",
                                    target="localhost",
                                    scope_id=scope_id or "",
                                    evidence={"port": port, "binding": "0.0.0.0"},
                                    affected_component=f"port_{port}",
                                    remediation="Bind service to specific interface if external access not required",
                                )
                                findings.append(finding)

        except Exception as e:
            logger.error(f"[MISCONFIG] Error detecting exposed services: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def detect_exposed_secrets(self, directory: str, scope_id: Optional[str] = None) -> dict:
        findings = []

        try:
            dir_path = Path(directory)
            if not dir_path.exists() or not dir_path.is_dir():
                return {"success": False, "error": "Directory does not exist", "findings": []}

            secret_patterns = [
                (r'password\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded password"),
                (r'api[_-]?key\s*=\s*["\'][^"\']{16,}["\']', "Hardcoded API key"),
                (r'secret\s*=\s*["\'][^"\']{16,}["\']', "Hardcoded secret"),
                (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', "Private key file"),
            ]

            for file_path in dir_path.rglob('*'):
                if file_path.is_file() and file_path.stat().st_size < 1024 * 1024:
                    try:
                        content = file_path.read_text(errors='ignore')
                        for pattern, description in secret_patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                finding = self.engine.add_finding(
                                    finding_type="exposed_secret",
                                    severity="critical",
                                    title=description,
                                    description=f"Found {description.lower()} in {file_path}",
                                    target=str(file_path),
                                    scope_id=scope_id or "",
                                    evidence={"file": str(file_path), "pattern": description},
                                    affected_component="Source Code",
                                    remediation="Remove hardcoded secrets and use secure secret management",
                                )
                                findings.append(finding)
                                break
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"[MISCONFIG] Error detecting exposed secrets: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def detect_weak_security_settings(self, scope_id: Optional[str] = None) -> dict:
        findings = []

        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["secedit", "/export", "/cfg", "C:\\Windows\\Temp\\security_policy.txt"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                policy_file = Path("C:\\Windows\\Temp\\security_policy.txt")
                if policy_file.exists():
                    content = policy_file.read_text()

                    if "EnableAdminAccount = 1" in content:
                        finding = self.engine.add_finding(
                            finding_type="weak_security_setting",
                            severity="medium",
                            title="Built-in Administrator Account Enabled",
                            description="The built-in Administrator account is enabled",
                            target="localhost",
                            scope_id=scope_id or "",
                            evidence={"setting": "EnableAdminAccount"},
                            affected_component="Security Policy",
                            remediation="Disable the built-in Administrator account",
                        )
                        findings.append(finding)

                    policy_file.unlink()

        except Exception as e:
            logger.error(f"[MISCONFIG] Error detecting weak security settings: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def comprehensive_misconfig_check(self, scope_id: Optional[str] = None) -> dict:
        logger.info("[MISCONFIG] Starting comprehensive misconfiguration check")

        all_findings = []

        checks = [
            lambda: self.detect_exposed_services(scope_id),
            lambda: self.detect_weak_security_settings(scope_id),
        ]

        for check in checks:
            try:
                result = check()
                if result["success"]:
                    all_findings.extend(result["findings"])
            except Exception as e:
                logger.error(f"[MISCONFIG] Check failed: {e}")

        logger.info(f"[MISCONFIG] Misconfiguration check complete: {len(all_findings)} findings")

        return {
            "success": True,
            "findings": all_findings,
            "total_findings": len(all_findings),
        }


_auth_security_auditor: Optional[AuthenticationSecurityAuditor] = None
_misconfig_detector: Optional[SecurityMisconfigurationDetector] = None


def get_auth_security_auditor() -> AuthenticationSecurityAuditor:
    global _auth_security_auditor
    if _auth_security_auditor is None:
        _auth_security_auditor = AuthenticationSecurityAuditor()
    return _auth_security_auditor


def get_misconfig_detector() -> SecurityMisconfigurationDetector:
    global _misconfig_detector
    if _misconfig_detector is None:
        _misconfig_detector = SecurityMisconfigurationDetector()
    return _misconfig_detector
