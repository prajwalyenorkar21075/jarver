"""
Threat Detection Engine for JARVIS cybersecurity module.

Detects suspicious processes, files, network behavior, authentication events,
and system changes. Generates structured security events.
"""

import logging
import time
import subprocess
import platform
import re
from typing import Optional
from pathlib import Path
from dataclasses import dataclass

from .security_db import get_security_db

logger = logging.getLogger(__name__)


@dataclass
class ThreatEvent:
    """Represents a detected threat or suspicious activity."""
    event_id: str
    timestamp: float
    threat_type: str
    severity: str
    source: str
    description: str
    indicators: list[str]
    evidence: dict
    recommended_actions: list[str]


class ThreatDetectionEngine:
    """
    Detects suspicious activity across the system.
    
    Monitors processes, files, network connections, authentication events,
    and system changes to identify potential security threats.
    """

    def __init__(self):
        self.db = get_security_db()
        self._detection_rules: list[dict] = []
        self._threat_history: list[ThreatEvent] = []
        
        # Initialize default detection rules
        self._init_default_rules()
        
        logger.info("[THREAT_DET] Threat detection engine initialized")

    def _init_default_rules(self):
        """Initialize default threat detection rules."""
        self._detection_rules = [
            {
                "name": "suspicious_process",
                "type": "process",
                "patterns": [
                    r"mimikatz",
                    r"keylogger",
                    r"rat\.exe",
                    r"trojan",
                    r"cryptominer",
                    r"bitcoin.*miner",
                ],
                "severity": "critical",
            },
            {
                "name": "suspicious_network",
                "type": "network",
                "patterns": [
                    r":4444",  # Common reverse shell port
                    r":5555",
                    r":6666",
                    r":1337",
                    r":31337",
                ],
                "severity": "high",
            },
            {
                "name": "suspicious_file",
                "type": "file",
                "patterns": [
                    r"\.exe\.jpg",  # Double extension
                    r"\.scr$",
                    r"\.pif$",
                    r"autorun\.inf",
                ],
                "severity": "high",
            },
        ]

    def detect_suspicious_processes(self) -> dict:
        """
        Detect suspicious processes running on the system.
        
        Returns:
            Dict with findings and threat events
        """
        findings = []
        events = []
        
        try:
            if platform.system() == "Windows":
                # Use tasklist to get running processes
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
                        
                        # Parse CSV format
                        parts = line.split(',')
                        if len(parts) >= 2:
                            process_name = parts[0].strip('"')
                            pid = parts[1].strip('"')
                            
                            # Check against suspicious patterns
                            for rule in self._detection_rules:
                                if rule["type"] == "process":
                                    for pattern in rule["patterns"]:
                                        if re.search(pattern, process_name, re.IGNORECASE):
                                            event = ThreatEvent(
                                                event_id=self.db.generate_id(),
                                                timestamp=time.time(),
                                                threat_type="suspicious_process",
                                                severity=rule["severity"],
                                                source="process_monitor",
                                                description=f"Suspicious process detected: {process_name} (PID: {pid})",
                                                indicators=[pattern],
                                                evidence={"process_name": process_name, "pid": pid},
                                                recommended_actions=[
                                                    f"Investigate process {process_name}",
                                                    "Verify if this is legitimate software",
                                                    "Consider terminating if malicious",
                                                ],
                                            )
                                            events.append(event)
                                            findings.append({
                                                "process": process_name,
                                                "pid": pid,
                                                "pattern": pattern,
                                                "severity": rule["severity"],
                                            })
            
            # Log events to database
            for event in events:
                self.db.insert_event(
                    event_type="suspicious_process",
                    severity=event.severity,
                    description=event.description,
                    source=event.source,
                    details={"indicators": event.indicators, "evidence": event.evidence},
                )
                self._threat_history.append(event)
            
            logger.info(f"[THREAT_DET] Process scan complete: {len(findings)} suspicious processes found")
            
            return {
                "success": True,
                "findings": findings,
                "total_findings": len(findings),
                "events": [
                    {
                        "event_id": e.event_id,
                        "threat_type": e.threat_type,
                        "severity": e.severity,
                        "description": e.description,
                    }
                    for e in events
                ],
            }
            
        except Exception as e:
            logger.error(f"[THREAT_DET] Error detecting suspicious processes: {e}")
            return {
                "success": False,
                "error": str(e),
                "findings": [],
                "total_findings": 0,
            }

    def detect_suspicious_network_connections(self) -> dict:
        """
        Detect suspicious network connections.
        
        Returns:
            Dict with findings and threat events
        """
        findings = []
        events = []
        
        try:
            if platform.system() == "Windows":
                # Use netstat to get network connections
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    
                    for line in lines:
                        if 'ESTABLISHED' in line or 'LISTENING' in line:
                            # Check against suspicious patterns
                            for rule in self._detection_rules:
                                if rule["type"] == "network":
                                    for pattern in rule["patterns"]:
                                        if re.search(pattern, line):
                                            event = ThreatEvent(
                                                event_id=self.db.generate_id(),
                                                timestamp=time.time(),
                                                threat_type="suspicious_network",
                                                severity=rule["severity"],
                                                source="network_monitor",
                                                description=f"Suspicious network connection detected: {pattern}",
                                                indicators=[pattern],
                                                evidence={"connection": line.strip()},
                                                recommended_actions=[
                                                    "Investigate the connection",
                                                    "Identify the process using this port",
                                                    "Block if malicious",
                                                ],
                                            )
                                            events.append(event)
                                            findings.append({
                                                "connection": line.strip(),
                                                "pattern": pattern,
                                                "severity": rule["severity"],
                                            })
            
            # Log events to database
            for event in events:
                self.db.insert_event(
                    event_type="suspicious_network",
                    severity=event.severity,
                    description=event.description,
                    source=event.source,
                    details={"indicators": event.indicators, "evidence": event.evidence},
                )
                self._threat_history.append(event)
            
            logger.info(f"[THREAT_DET] Network scan complete: {len(findings)} suspicious connections found")
            
            return {
                "success": True,
                "findings": findings,
                "total_findings": len(findings),
                "events": [
                    {
                        "event_id": e.event_id,
                        "threat_type": e.threat_type,
                        "severity": e.severity,
                        "description": e.description,
                    }
                    for e in events
                ],
            }
            
        except Exception as e:
            logger.error(f"[THREAT_DET] Error detecting suspicious network connections: {e}")
            return {
                "success": False,
                "error": str(e),
                "findings": [],
                "total_findings": 0,
            }

    def detect_suspicious_files(self, directory: str) -> dict:
        """
        Detect suspicious files in a directory.
        
        Args:
            directory: Directory to scan
            
        Returns:
            Dict with findings and threat events
        """
        findings = []
        events = []
        
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return {
                    "success": False,
                    "error": "Directory does not exist",
                    "findings": [],
                    "total_findings": 0,
                }
            
            # Scan files
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    file_name = file_path.name
                    
                    # Check against suspicious patterns
                    for rule in self._detection_rules:
                        if rule["type"] == "file":
                            for pattern in rule["patterns"]:
                                if re.search(pattern, file_name, re.IGNORECASE):
                                    event = ThreatEvent(
                                        event_id=self.db.generate_id(),
                                        timestamp=time.time(),
                                        threat_type="suspicious_file",
                                        severity=rule["severity"],
                                        source="file_monitor",
                                        description=f"Suspicious file detected: {file_path}",
                                        indicators=[pattern],
                                        evidence={"file_path": str(file_path), "file_name": file_name},
                                        recommended_actions=[
                                            "Investigate the file",
                                            "Check file hash against known malware",
                                            "Quarantine if malicious",
                                        ],
                                    )
                                    events.append(event)
                                    findings.append({
                                        "file_path": str(file_path),
                                        "pattern": pattern,
                                        "severity": rule["severity"],
                                    })
            
            # Log events to database
            for event in events:
                self.db.insert_event(
                    event_type="suspicious_file",
                    severity=event.severity,
                    description=event.description,
                    source=event.source,
                    details={"indicators": event.indicators, "evidence": event.evidence},
                )
                self._threat_history.append(event)
            
            logger.info(f"[THREAT_DET] File scan complete: {len(findings)} suspicious files found")
            
            return {
                "success": True,
                "findings": findings,
                "total_findings": len(findings),
                "events": [
                    {
                        "event_id": e.event_id,
                        "threat_type": e.threat_type,
                        "severity": e.severity,
                        "description": e.description,
                    }
                    for e in events
                ],
            }
            
        except Exception as e:
            logger.error(f"[THREAT_DET] Error detecting suspicious files: {e}")
            return {
                "success": False,
                "error": str(e),
                "findings": [],
                "total_findings": 0,
            }

    def detect_authentication_anomalies(self) -> dict:
        """
        Detect authentication anomalies from Windows security logs.
        
        Returns:
            Dict with findings and threat events
        """
        findings = []
        events = []
        
        try:
            if platform.system() == "Windows":
                # Check for failed login attempts
                result = subprocess.run(
                    ["wevtutil", "qe", "Security", "/q:*[System[(EventID=4625)]]", "/c:10", "/rd:true", "/f:text"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                if result.returncode == 0 and result.stdout:
                    # Count failed logins
                    failed_count = result.stdout.count("EventID=4625")
                    
                    if failed_count > 5:  # Threshold for suspicious activity
                        event = ThreatEvent(
                            event_id=self.db.generate_id(),
                            timestamp=time.time(),
                            threat_type="authentication_anomaly",
                            severity="high",
                            source="auth_monitor",
                            description=f"Multiple failed login attempts detected: {failed_count} failures",
                            indicators=["multiple_failed_logins"],
                            evidence={"failed_count": failed_count},
                            recommended_actions=[
                                "Check for brute force attack",
                                "Review account lockout policies",
                                "Investigate source IP addresses",
                            ],
                        )
                        events.append(event)
                        findings.append({
                            "type": "failed_logins",
                            "count": failed_count,
                            "severity": "high",
                        })
            
            # Log events to database
            for event in events:
                self.db.insert_event(
                    event_type="authentication_anomaly",
                    severity=event.severity,
                    description=event.description,
                    source=event.source,
                    details={"indicators": event.indicators, "evidence": event.evidence},
                )
                self._threat_history.append(event)
            
            logger.info(f"[THREAT_DET] Auth scan complete: {len(findings)} anomalies found")
            
            return {
                "success": True,
                "findings": findings,
                "total_findings": len(findings),
                "events": [
                    {
                        "event_id": e.event_id,
                        "threat_type": e.threat_type,
                        "severity": e.severity,
                        "description": e.description,
                    }
                    for e in events
                ],
            }
            
        except Exception as e:
            logger.error(f"[THREAT_DET] Error detecting authentication anomalies: {e}")
            return {
                "success": False,
                "error": str(e),
                "findings": [],
                "total_findings": 0,
            }

    def comprehensive_threat_scan(self) -> dict:
        """
        Perform comprehensive threat detection across all vectors.
        
        Returns:
            Dict with all findings
        """
        logger.info("[THREAT_DET] Starting comprehensive threat scan")
        
        all_findings = []
        all_events = []
        
        # Scan processes
        process_result = self.detect_suspicious_processes()
        if process_result["success"]:
            all_findings.extend(process_result["findings"])
            all_events.extend(process_result["events"])
        
        # Scan network
        network_result = self.detect_suspicious_network_connections()
        if network_result["success"]:
            all_findings.extend(network_result["findings"])
            all_events.extend(network_result["events"])
        
        # Check authentication
        auth_result = self.detect_authentication_anomalies()
        if auth_result["success"]:
            all_findings.extend(auth_result["findings"])
            all_events.extend(auth_result["events"])
        
        logger.info(f"[THREAT_DET] Comprehensive scan complete: {len(all_findings)} total findings")
        
        return {
            "success": True,
            "findings": all_findings,
            "total_findings": len(all_findings),
            "events": all_events,
            "scan_summary": {
                "process_findings": process_result.get("total_findings", 0),
                "network_findings": network_result.get("total_findings", 0),
                "auth_findings": auth_result.get("total_findings", 0),
            },
        }

    def get_threat_history(self, limit: int = 50) -> list[dict]:
        """Get recent threat detection history."""
        return [
            {
                "event_id": event.event_id,
                "timestamp": event.timestamp,
                "threat_type": event.threat_type,
                "severity": event.severity,
                "description": event.description,
            }
            for event in self._threat_history[-limit:]
        ][::-1]

    def get_threat_stats(self) -> dict:
        """Get threat detection statistics."""
        return {
            "total_threats": len(self._threat_history),
            "by_type": {
                "process": sum(1 for e in self._threat_history if e.threat_type == "suspicious_process"),
                "network": sum(1 for e in self._threat_history if e.threat_type == "suspicious_network"),
                "file": sum(1 for e in self._threat_history if e.threat_type == "suspicious_file"),
                "auth": sum(1 for e in self._threat_history if e.threat_type == "authentication_anomaly"),
            },
            "by_severity": {
                "critical": sum(1 for e in self._threat_history if e.severity == "critical"),
                "high": sum(1 for e in self._threat_history if e.severity == "high"),
                "medium": sum(1 for e in self._threat_history if e.severity == "medium"),
                "low": sum(1 for e in self._threat_history if e.severity == "low"),
            },
        }


# Singleton instance
_threat_detection_engine: Optional[ThreatDetectionEngine] = None


def get_threat_detection_engine() -> ThreatDetectionEngine:
    """Get or create the threat detection engine singleton."""
    global _threat_detection_engine
    if _threat_detection_engine is None:
        _threat_detection_engine = ThreatDetectionEngine()
    return _threat_detection_engine
