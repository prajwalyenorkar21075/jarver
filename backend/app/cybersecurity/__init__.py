"""
Cybersecurity & Defensive Security Module for JARVIS.

Provides 20 integrated security capabilities:
1.  Security Orchestrator - coordinates all operations
2.  Threat Detection Engine - detects suspicious activity
3.  Windows Endpoint Security - monitors Windows systems
4.  Network Security Monitor - inspects network state
5.  Vulnerability Scanner - scans for vulnerabilities
6.  Web Application Security Analyzer - OWASP testing
7.  Secure Code Analyzer - source code security scanning
8.  Dependency Security Scanner - dependency vulnerability checks
9.  File Integrity Monitor - file change detection
10. Malware/Suspicious File Analyzer - static analysis
11. Log Analysis Engine - log security analysis
12. Authentication & Access Control - secure auth
13. Secrets & Credential Protection - secret detection
14. Database Security - database auditing
15. Security Alert Manager - alert lifecycle
16. Incident Response Engine - incident workflows
17. Backup & Recovery Security - backup verification
18. Privacy Protection - PII detection and redaction
19. Security Knowledge Base - OWASP/CWE/CVE knowledge
20. Security Report Generator - report generation
"""

from .orchestrator import SecurityOrchestrator, get_security_orchestrator
from .threat_detection import ThreatDetectionEngine, get_threat_detection_engine
from .windows_security import WindowsEndpointSecurity, get_windows_endpoint_security
from .network_security import NetworkSecurityMonitor, get_network_security_monitor
from .vulnerability_scanner import VulnerabilityScanner, get_vulnerability_scanner
from .web_security_analyzer import WebApplicationSecurityAnalyzer, get_web_application_analyzer
from .secure_code_analyzer import SecureCodeAnalyzer, get_secure_code_analyzer
from .dependency_scanner import DependencySecurityScanner, get_dependency_scanner
from .file_integrity import FileIntegrityMonitor, get_file_integrity_monitor
from .malware_analyzer import MalwareAnalyzer, get_malware_analyzer
from .log_analyzer import LogAnalysisEngine, get_log_analyzer
from .auth_manager import AuthenticationManager, get_auth_manager
from .secret_protection import SecretScanner, get_secret_scanner
from .database_security import DatabaseSecurityAuditor, get_database_auditor
from .alert_manager import SecurityAlertManager, get_alert_manager
from .incident_response import IncidentResponseEngine, get_incident_response_engine
from .backup_security import BackupSecurityVerifier, get_backup_verifier
from .privacy_protection import PrivacyProtection, get_privacy_protection
from .knowledge_base import SecurityKnowledgeBase, get_security_knowledge_base
from .report_generator import SecurityReportGenerator, get_report_generator
from .security_db import SecurityDatabase, get_security_db
from .asset_graph import SecurityAssetGraph, get_security_graph

__all__ = [
    "SecurityAssetGraph", "get_security_graph",
    "SecurityOrchestrator", "get_security_orchestrator",
    "ThreatDetectionEngine", "get_threat_detection_engine",
    "WindowsEndpointSecurity", "get_windows_endpoint_security",
    "NetworkSecurityMonitor", "get_network_security_monitor",
    "VulnerabilityScanner", "get_vulnerability_scanner",
    "WebApplicationSecurityAnalyzer", "get_web_application_analyzer",
    "SecureCodeAnalyzer", "get_secure_code_analyzer",
    "DependencySecurityScanner", "get_dependency_scanner",
    "FileIntegrityMonitor", "get_file_integrity_monitor",
    "MalwareAnalyzer", "get_malware_analyzer",
    "LogAnalysisEngine", "get_log_analyzer",
    "AuthenticationManager", "get_auth_manager",
    "SecretScanner", "get_secret_scanner",
    "DatabaseSecurityAuditor", "get_database_auditor",
    "SecurityAlertManager", "get_alert_manager",
    "IncidentResponseEngine", "get_incident_response_engine",
    "BackupSecurityVerifier", "get_backup_verifier",
    "PrivacyProtection", "get_privacy_protection",
    "SecurityKnowledgeBase", "get_security_knowledge_base",
    "SecurityReportGenerator", "get_report_generator",
    "SecurityDatabase", "get_security_db",
]
