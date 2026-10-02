"""
Network Security Assessment and Configuration Security Testing.

Assesses network configurations, identifies insecure services, and audits
system configurations for security weaknesses.
"""

import logging
import socket
import subprocess
import platform
import re
from typing import Optional
from pathlib import Path

from .core import get_ethical_hacking_engine, Severity

logger = logging.getLogger(__name__)


class NetworkSecurityAssessor:
    """Assesses network security configurations."""

    def __init__(self):
        self.engine = get_ethical_hacking_engine()
        logger.info("[NET_SEC] Network security assessor initialized")

    def check_open_ports_system(self, scope_id: Optional[str] = None) -> dict:
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
            else:
                result = subprocess.run(
                    ["netstat", "-tuln"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout

            listening_ports = []
            for line in output.split('\n'):
                if 'LISTEN' in line or 'LISTENING' in line:
                    match = re.search(r':(\d+)\s', line)
                    if match:
                        port = int(match.group(1))
                        listening_ports.append(port)

            risky_ports = {
                21: "FTP - Unencrypted file transfer",
                23: "Telnet - Unencrypted remote access",
                135: "MS RPC - Windows RPC endpoint mapper",
                139: "NetBIOS - Windows file sharing",
                445: "SMB - Windows file sharing",
                3389: "RDP - Remote Desktop Protocol",
                5900: "VNC - Remote desktop",
            }

            for port in listening_ports:
                if port in risky_ports:
                    finding = self.engine.add_finding(
                        finding_type="risky_service",
                        severity="medium" if port < 1000 else "low",
                        title=f"Risky Service Listening: Port {port}",
                        description=risky_ports[port],
                        target="localhost",
                        scope_id=scope_id or "",
                        evidence={"port": port, "service": risky_ports[port]},
                        affected_component=f"port_{port}",
                        remediation=f"Review if {risky_ports[port]} is required and properly secured",
                    )
                    findings.append(finding)

        except Exception as e:
            logger.error(f"[NET_SEC] Error checking system ports: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def check_firewall_status(self, scope_id: Optional[str] = None) -> dict:
        findings = []

        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["netsh", "advfirewall", "show", "allprofiles", "state"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout

                if "OFF" in output.upper():
                    finding = self.engine.add_finding(
                        finding_type="firewall_disabled",
                        severity="high",
                        title="Windows Firewall Disabled",
                        description="One or more firewall profiles are disabled",
                        target="localhost",
                        scope_id=scope_id or "",
                        evidence={"status": "disabled"},
                        affected_component="Windows Firewall",
                        remediation="Enable Windows Firewall for all profiles",
                    )
                    findings.append(finding)

        except Exception as e:
            logger.error(f"[NET_SEC] Error checking firewall: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def check_network_shares(self, scope_id: Optional[str] = None) -> dict:
        findings = []

        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["net", "share"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout

                for line in output.split('\n'):
                    if line.strip() and not line.startswith('-') and not line.startswith('Share'):
                        parts = line.split()
                        if len(parts) >= 2:
                            share_name = parts[0]
                            if share_name not in ['IPC$', 'ADMIN$', 'C$']:
                                finding = self.engine.add_finding(
                                    finding_type="network_share",
                                    severity="low",
                                    title=f"Network Share Detected: {share_name}",
                                    description=f"Network share {share_name} is accessible",
                                    target="localhost",
                                    scope_id=scope_id or "",
                                    evidence={"share": share_name},
                                    affected_component="SMB Shares",
                                    remediation="Review share permissions and access controls",
                                )
                                findings.append(finding)

        except Exception as e:
            logger.error(f"[NET_SEC] Error checking network shares: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def comprehensive_network_assessment(self, scope_id: Optional[str] = None) -> dict:
        logger.info("[NET_SEC] Starting comprehensive network assessment")

        all_findings = []

        assessments = [
            self.check_open_ports_system,
            self.check_firewall_status,
            self.check_network_shares,
        ]

        for assessment in assessments:
            try:
                result = assessment(scope_id)
                if result["success"]:
                    all_findings.extend(result["findings"])
            except Exception as e:
                logger.error(f"[NET_SEC] Assessment failed: {e}")

        logger.info(f"[NET_SEC] Network assessment complete: {len(all_findings)} findings")

        return {
            "success": True,
            "findings": all_findings,
            "total_findings": len(all_findings),
        }


class ConfigurationSecurityAuditor:
    """Audits system and application configurations for security issues."""

    def __init__(self):
        self.engine = get_ethical_hacking_engine()
        logger.info("[CONFIG_SEC] Configuration security auditor initialized")

    def audit_windows_config(self, scope_id: Optional[str] = None) -> dict:
        findings = []

        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "os", "get", "Version", "/value"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                version_output = result.stdout

                result = subprocess.run(
                    ["systeminfo"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                systeminfo = result.stdout

                if "Hotfix" in systeminfo:
                    hotfix_count = systeminfo.count("KB")
                    if hotfix_count < 10:
                        finding = self.engine.add_finding(
                            finding_type="outdated_system",
                            severity="medium",
                            title="System May Be Missing Security Updates",
                            description=f"Only {hotfix_count} hotfixes detected",
                            target="localhost",
                            scope_id=scope_id or "",
                            evidence={"hotfix_count": hotfix_count},
                            affected_component="Windows Updates",
                            remediation="Run Windows Update to install latest security patches",
                        )
                        findings.append(finding)

        except Exception as e:
            logger.error(f"[CONFIG_SEC] Error auditing Windows config: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def audit_file_permissions(self, path: str, scope_id: Optional[str] = None) -> dict:
        findings = []

        try:
            file_path = Path(path)
            if not file_path.exists():
                return {"success": False, "error": "Path does not exist", "findings": []}

            if platform.system() != "Windows":
                import stat
                mode = file_path.stat().st_mode

                if mode & stat.S_IWOTH:
                    finding = self.engine.add_finding(
                        finding_type="insecure_permissions",
                        severity="high",
                        title="World-Writable File Detected",
                        description=f"File {path} is writable by all users",
                        target=path,
                        scope_id=scope_id or "",
                        evidence={"path": path, "permissions": oct(mode)},
                        affected_component="File Permissions",
                        remediation="Restrict file permissions to authorized users only",
                    )
                    findings.append(finding)

                if mode & stat.S_IXOTH and file_path.is_file():
                    finding = self.engine.add_finding(
                        finding_type="insecure_permissions",
                        severity="medium",
                        title="World-Executable File Detected",
                        description=f"File {path} is executable by all users",
                        target=path,
                        scope_id=scope_id or "",
                        evidence={"path": path, "permissions": oct(mode)},
                        affected_component="File Permissions",
                        remediation="Remove execute permission for other users",
                    )
                    findings.append(finding)

        except Exception as e:
            logger.error(f"[CONFIG_SEC] Error auditing file permissions: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def audit_environment_variables(self, scope_id: Optional[str] = None) -> dict:
        findings = []

        try:
            import os
            sensitive_vars = ['PASSWORD', 'SECRET', 'KEY', 'TOKEN', 'CREDENTIAL']

            for var_name, var_value in os.environ.items():
                for sensitive in sensitive_vars:
                    if sensitive in var_name.upper():
                        if var_value and len(var_value) > 5:
                            finding = self.engine.add_finding(
                                finding_type="exposed_secret",
                                severity="high",
                                title=f"Sensitive Data in Environment Variable: {var_name}",
                                description=f"Environment variable {var_name} may contain sensitive data",
                                target="localhost",
                                scope_id=scope_id or "",
                                evidence={"variable": var_name, "length": len(var_value)},
                                affected_component="Environment Configuration",
                                remediation="Use secure secret management instead of environment variables",
                            )
                            findings.append(finding)
                            break

        except Exception as e:
            logger.error(f"[CONFIG_SEC] Error auditing environment: {e}")

        return {
            "success": True,
            "findings": findings,
            "total_findings": len(findings),
        }

    def comprehensive_config_audit(self, scope_id: Optional[str] = None) -> dict:
        logger.info("[CONFIG_SEC] Starting comprehensive configuration audit")

        all_findings = []

        audits = [
            lambda: self.audit_windows_config(scope_id),
            lambda: self.audit_environment_variables(scope_id),
        ]

        for audit in audits:
            try:
                result = audit()
                if result["success"]:
                    all_findings.extend(result["findings"])
            except Exception as e:
                logger.error(f"[CONFIG_SEC] Audit failed: {e}")

        logger.info(f"[CONFIG_SEC] Configuration audit complete: {len(all_findings)} findings")

        return {
            "success": True,
            "findings": all_findings,
            "total_findings": len(all_findings),
        }


_network_security_assessor: Optional[NetworkSecurityAssessor] = None
_config_security_auditor: Optional[ConfigurationSecurityAuditor] = None


def get_network_security_assessor() -> NetworkSecurityAssessor:
    global _network_security_assessor
    if _network_security_assessor is None:
        _network_security_assessor = NetworkSecurityAssessor()
    return _network_security_assessor


def get_config_security_auditor() -> ConfigurationSecurityAuditor:
    global _config_security_auditor
    if _config_security_auditor is None:
        _config_security_auditor = ConfigurationSecurityAuditor()
    return _config_security_auditor
