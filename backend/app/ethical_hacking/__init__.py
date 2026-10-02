"""
Ethical Hacking / Authorized Penetration Testing Module for JARVIS.

Provides 12 core capabilities:
1.  Reconnaissance (asset/service discovery)
2.  Port & Service Assessment
3.  Vulnerability Assessment (CVE/CWE)
4.  Web Application Security Testing (OWASP)
5.  API Security Testing
6.  Network Security Assessment
7.  Configuration Security Testing
8.  Authentication Security Audit
9.  Security Misconfiguration Detection
10. Safe Exploit Validation
11. Security Evidence Collection
12. Penetration Testing Reports

CRITICAL: All operations require explicit authorization and scope definition.
"""

from .core import (
    EthicalHackingEngine,
    ScopeManager,
    SafetyController,
    TestMode,
    AuthorizationStatus,
    Severity,
    TestScope,
    SecurityFinding,
    get_ethical_hacking_engine,
)

from .reconnaissance import (
    ReconnaissanceScanner,
    get_recon_scanner,
)

from .vulnerability import (
    VulnerabilityAssessor,
    get_vuln_assessor,
)

from .web_security import (
    WebSecurityTester,
    APISecurityTester,
    get_web_security_tester,
    get_api_security_tester,
)

from .network_config import (
    NetworkSecurityAssessor,
    ConfigurationSecurityAuditor,
    get_network_security_assessor,
    get_config_security_auditor,
)

from .auth_misconfig import (
    AuthenticationSecurityAuditor,
    SecurityMisconfigurationDetector,
    get_auth_security_auditor,
    get_misconfig_detector,
)

from .exploit_validation import (
    SafeExploitValidator,
    get_safe_exploit_validator,
)

from .reporting import (
    EvidenceCollector,
    PenTestReportGenerator,
    get_evidence_collector,
    get_report_generator,
)
