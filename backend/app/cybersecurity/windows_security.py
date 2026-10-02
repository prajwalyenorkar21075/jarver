"""
Windows Endpoint Security for JARVIS cybersecurity module.

Monitors Windows processes, services, startup entries, firewall state,
and security configuration. Uses safe read-only inspection by default.
"""

import logging
import subprocess
import platform
import re
from typing import Optional
from pathlib import Path

from .security_db import get_security_db

logger = logging.getLogger(__name__)


class WindowsEndpointSecurity:
    """
    Windows endpoint security monitoring and configuration.
    
    Provides read-only inspection of Windows security state by default.
    Requires explicit authorization for configuration changes.
    """

    def __init__(self):
        self.db = get_security_db()
        self._findings: list[dict] = []
        
        if platform.system() != "Windows":
            logger.warning("[WIN_SEC] Windows endpoint security only available on Windows")
        
        logger.info("[WIN_SEC] Windows endpoint security initialized")

    def check_running_processes(self) -> dict:
        """
        Check running processes for security issues.
        
        Returns:
            Dict with process information and findings
        """
        findings = []
        processes = []
        
        try:
            if platform.system() != "Windows":
                return {
                    "success": False,
                    "error": "Windows endpoint security only available on Windows",
                    "processes": [],
                    "findings": [],
                }
            
            # Get running processes
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                
                for line in lines:
                    if not line.strip():
                        continue
                    
                    parts = line.split(',')
                    if len(parts) >= 5:
                        process_name = parts[0].strip('"')
                        pid = parts[1].strip('"')
                        session = parts[2].strip('"')
                        mem_usage = parts[4].strip('"')
                        
                        process_info = {
                            "name": process_name,
                            "pid": pid,
                            "session": session,
                            "memory": mem_usage,
                        }
                        processes.append(process_info)
                        
                        # Check for suspicious processes
                        suspicious_patterns = [
                            r"mimikatz",
                            r"keylogger",
                            r"rat\.exe",
                            r"cryptominer",
                        ]
                        
                        for pattern in suspicious_patterns:
                            if re.search(pattern, process_name, re.IGNORECASE):
                                findings.append({
                                    "type": "suspicious_process",
                                    "severity": "high",
                                    "process": process_name,
                                    "pid": pid,
                                    "description": f"Suspicious process detected: {process_name}",
                                })
            
            logger.info(f"[WIN_SEC] Process check complete: {len(processes)} processes, {len(findings)} findings")
            
            return {
                "success": True,
                "processes": processes,
                "total_processes": len(processes),
                "findings": findings,
                "total_findings": len(findings),
            }
            
        except Exception as e:
            logger.error(f"[WIN_SEC] Error checking processes: {e}")
            return {
                "success": False,
                "error": str(e),
                "processes": [],
                "findings": [],
            }

    def check_services(self) -> dict:
        """
        Check Windows services for security issues.
        
        Returns:
            Dict with service information and findings
        """
        findings = []
        services = []
        
        try:
            if platform.system() != "Windows":
                return {
                    "success": False,
                    "error": "Windows endpoint security only available on Windows",
                    "services": [],
                    "findings": [],
                }
            
            # Get running services
            result = subprocess.run(
                ["sc", "query", "type=service", "state=all"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode == 0:
                # Parse service output
                current_service = {}
                for line in result.stdout.split('\n'):
                    if line.strip().startswith("SERVICE_NAME:"):
                        if current_service:
                            services.append(current_service)
                        current_service = {"name": line.split(":", 1)[1].strip()}
                    elif "STATE" in line and current_service:
                        match = re.search(r"STATE\s*:\s*(\w+)", line)
                        if match:
                            current_service["state"] = match.group(1)
                
                if current_service:
                    services.append(current_service)
                
                # Check for disabled security services
                critical_services = ["WinDefend", "wuauserv", "MpsSvc"]
                for service in services:
                    if service.get("name") in critical_services and service.get("state") != "RUNNING":
                        findings.append({
                            "type": "disabled_security_service",
                            "severity": "high",
                            "service": service["name"],
                            "description": f"Critical security service not running: {service['name']}",
                        })
            
            logger.info(f"[WIN_SEC] Service check complete: {len(services)} services, {len(findings)} findings")
            
            return {
                "success": True,
                "services": services,
                "total_services": len(services),
                "findings": findings,
                "total_findings": len(findings),
            }
            
        except Exception as e:
            logger.error(f"[WIN_SEC] Error checking services: {e}")
            return {
                "success": False,
                "error": str(e),
                "services": [],
                "findings": [],
            }

    def check_startup_entries(self) -> dict:
        """
        Check startup entries for suspicious items.
        
        Returns:
            Dict with startup entries and findings
        """
        findings = []
        startup_items = []
        
        try:
            if platform.system() != "Windows":
                return {
                    "success": False,
                    "error": "Windows endpoint security only available on Windows",
                    "startup_items": [],
                    "findings": [],
                }
            
            # Check common startup locations
            startup_paths = [
                r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup",
                Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
            ]
            
            for startup_path in startup_paths:
                path = Path(startup_path)
                if path.exists():
                    for item in path.iterdir():
                        if item.is_file():
                            startup_items.append({
                                "name": item.name,
                                "path": str(item),
                                "location": "startup_folder",
                            })
                            
                            # Check for suspicious extensions
                            suspicious_ext = [".scr", ".pif", ".vbs", ".js"]
                            if item.suffix.lower() in suspicious_ext:
                                findings.append({
                                    "type": "suspicious_startup",
                                    "severity": "medium",
                                    "item": item.name,
                                    "path": str(item),
                                    "description": f"Suspicious startup item: {item.name}",
                                })
            
            logger.info(f"[WIN_SEC] Startup check complete: {len(startup_items)} items, {len(findings)} findings")
            
            return {
                "success": True,
                "startup_items": startup_items,
                "total_items": len(startup_items),
                "findings": findings,
                "total_findings": len(findings),
            }
            
        except Exception as e:
            logger.error(f"[WIN_SEC] Error checking startup entries: {e}")
            return {
                "success": False,
                "error": str(e),
                "startup_items": [],
                "findings": [],
            }

    def check_firewall_status(self) -> dict:
        """
        Check Windows Firewall status and configuration.
        
        Returns:
            Dict with firewall status and findings
        """
        findings = []
        firewall_status = {}
        
        try:
            if platform.system() != "Windows":
                return {
                    "success": False,
                    "error": "Windows endpoint security only available on Windows",
                    "firewall_status": {},
                    "findings": [],
                }
            
            # Check firewall status
            result = subprocess.run(
                ["netsh", "advfirewall", "show", "allprofiles", "state"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode == 0:
                # Parse firewall status
                for profile in ["Domain", "Private", "Public"]:
                    match = re.search(
                        rf"{profile} Profile Settings:.*?State\s+(\w+)",
                        result.stdout,
                        re.DOTALL | re.IGNORECASE,
                    )
                    if match:
                        state = match.group(1)
                        firewall_status[profile] = state
                        
                        if state.upper() != "ON":
                            findings.append({
                                "type": "firewall_disabled",
                                "severity": "high",
                                "profile": profile,
                                "description": f"Firewall disabled for {profile} profile",
                            })
            
            logger.info(f"[WIN_SEC] Firewall check complete: {len(findings)} findings")
            
            return {
                "success": True,
                "firewall_status": firewall_status,
                "findings": findings,
                "total_findings": len(findings),
            }
            
        except Exception as e:
            logger.error(f"[WIN_SEC] Error checking firewall: {e}")
            return {
                "success": False,
                "error": str(e),
                "firewall_status": {},
                "findings": [],
            }

    def check_security_configuration(self) -> dict:
        """
        Check Windows security configuration.
        
        Returns:
            Dict with security configuration and findings
        """
        findings = []
        config = {}
        
        try:
            if platform.system() != "Windows":
                return {
                    "success": False,
                    "error": "Windows endpoint security only available on Windows",
                    "configuration": {},
                    "findings": [],
                }
            
            # Check Windows Update status
            result = subprocess.run(
                ["wuauclt", "/detectnow"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            config["windows_update_check"] = "initiated"
            
            # Check user account control
            result = subprocess.run(
                ["reg", "query", "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System", "/v", "EnableLUA"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode == 0:
                match = re.search(r"EnableLUA\s+REG_DWORD\s+(0x\d+)", result.stdout)
                if match:
                    uac_enabled = match.group(1) != "0x0"
                    config["uac_enabled"] = uac_enabled
                    
                    if not uac_enabled:
                        findings.append({
                            "type": "uac_disabled",
                            "severity": "high",
                            "description": "User Account Control (UAC) is disabled",
                        })
            
            logger.info(f"[WIN_SEC] Security config check complete: {len(findings)} findings")
            
            return {
                "success": True,
                "configuration": config,
                "findings": findings,
                "total_findings": len(findings),
            }
            
        except Exception as e:
            logger.error(f"[WIN_SEC] Error checking security configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "configuration": {},
                "findings": [],
            }

    def comprehensive_endpoint_check(self) -> dict:
        """
        Perform comprehensive Windows endpoint security check.
        
        Returns:
            Dict with all findings
        """
        logger.info("[WIN_SEC] Starting comprehensive endpoint security check")
        
        all_findings = []
        
        # Check processes
        process_result = self.check_running_processes()
        if process_result["success"]:
            all_findings.extend(process_result["findings"])
        
        # Check services
        service_result = self.check_services()
        if service_result["success"]:
            all_findings.extend(service_result["findings"])
        
        # Check startup
        startup_result = self.check_startup_entries()
        if startup_result["success"]:
            all_findings.extend(startup_result["findings"])
        
        # Check firewall
        firewall_result = self.check_firewall_status()
        if firewall_result["success"]:
            all_findings.extend(firewall_result["findings"])
        
        # Check security config
        config_result = self.check_security_configuration()
        if config_result["success"]:
            all_findings.extend(config_result["findings"])
        
        # Log findings to database
        for finding in all_findings:
            self.db.insert_event(
                event_type=finding["type"],
                severity=finding["severity"],
                description=finding["description"],
                source="windows_endpoint_security",
                details=finding,
            )
        
        logger.info(f"[WIN_SEC] Comprehensive check complete: {len(all_findings)} total findings")
        
        return {
            "success": True,
            "findings": all_findings,
            "total_findings": len(all_findings),
            "checks_performed": {
                "processes": process_result.get("total_processes", 0),
                "services": service_result.get("total_services", 0),
                "startup_items": startup_result.get("total_items", 0),
            },
        }


# Singleton instance
_windows_endpoint_security: Optional[WindowsEndpointSecurity] = None


def get_windows_endpoint_security() -> WindowsEndpointSecurity:
    """Get or create the Windows endpoint security singleton."""
    global _windows_endpoint_security
    if _windows_endpoint_security is None:
        _windows_endpoint_security = WindowsEndpointSecurity()
    return _windows_endpoint_security
