"""
Security Knowledge Base for JARVIS cybersecurity module.

Structured security knowledge including:
- OWASP Top 10
- CWE (Common Weakness Enumeration)
- CVE references
- Security best practices
- Attack patterns and mitigations
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


OWASP_TOP_10_2021 = {
    "A01:2021": {
        "title": "Broken Access Control",
        "description": "Restrictions on what authenticated users are allowed to do are not properly enforced",
        "examples": [
            "Violation of the principle of least privilege",
            "Bypassing access control checks by modifying the URL",
            "CORS misconfiguration allowing unauthorized API access",
            "Forced browsing to authenticated pages without authentication",
        ],
        "mitigations": [
            "Implement access control controls and enforce them server-side",
            "Deny by default - only grant access to specific resources",
            "Log access control failures and alert admins",
            "Rate limit API and controller access",
            "JWT tokens should be invalidated on logout",
        ],
        "related_cwes": ["CWE-200", "CWE-264", "CWE-284", "CWE-352", "CWE-538", "CWE-639"],
    },
    "A02:2021": {
        "title": "Cryptographic Failures",
        "description": "Failures related to cryptography that lead to exposure of sensitive data",
        "examples": [
            "Transmitting data in plaintext",
            "Using weak or deprecated cryptographic algorithms",
            "Using default or hardcoded cryptographic keys",
            "Not using proper certificate validation",
        ],
        "mitigations": [
            "Classify data and apply controls accordingly",
            "Don't use deprecated protocols (FTP, SMTP, Telnet)",
            "Use TLS 1.2+ with strong cipher suites",
            "Use authenticated encryption (AES-GCM, ChaCha20-Poly1305)",
            "Rotate keys and secrets regularly",
        ],
        "related_cwes": ["CWE-259", "CWE-310", "CWE-319", "CWE-326", "CWE-327", "CWE-331"],
    },
    "A03:2021": {
        "title": "Injection",
        "description": "Untrusted data is sent to an interpreter as part of a command or query",
        "examples": [
            "SQL injection",
            "OS command injection",
            "LDAP injection",
            "NoSQL injection",
            "XPath injection",
        ],
        "mitigations": [
            "Use parameterized queries or prepared statements",
            "Use ORM frameworks with proper escaping",
            "Validate and sanitize all user input",
            "Use LIMIT and other SQL controls to prevent mass data exposure",
            "Use allowlists for input validation",
        ],
        "related_cwes": ["CWE-79", "CWE-89", "CWE-73", "CWE-77", "CWE-78", "CWE-917"],
    },
    "A04:2021": {
        "title": "Insecure Design",
        "description": "Missing or ineffective control design leading to security weaknesses",
        "examples": [
            "Missing business logic validation",
            "Lack of threat modeling",
            "No rate limiting on sensitive operations",
            "Missing account lockout mechanisms",
        ],
        "mitigations": [
            "Establish a secure development lifecycle",
            "Use threat modeling for critical features",
            "Write unit and integration tests for security controls",
            "Implement proper error handling and logging",
            "Use resource limits and rate limiting",
        ],
        "related_cwes": ["CWE-209", "CWE-911", "CWE-1053"],
    },
    "A05:2021": {
        "title": "Security Misconfiguration",
        "description": "Security settings are defined, implemented, or maintained incorrectly",
        "examples": [
            "Unnecessary open ports or services",
            "Default accounts with default passwords",
            "Verbose error messages exposed to users",
            "Missing security headers",
            "Directory listing enabled",
        ],
        "mitigations": [
            "Implement a hardened deployment process",
            "Remove or disable unnecessary features and frameworks",
            "Review and update configurations regularly",
            "Use automated configuration verification",
            "Implement a proper security header policy",
        ],
        "related_cwes": ["CWE-2", "CWE-16", "CWE-388", "CWE-611", "CWE-1004", "CWE-1032"],
    },
    "A06:2021": {
        "title": "Vulnerable and Outdated Components",
        "description": "Using components with known vulnerabilities",
        "examples": [
            "Using outdated libraries with known CVEs",
            "Running unsupported software",
            "Not scanning for outdated dependencies",
        ],
        "mitigations": [
            "Remove unused dependencies and components",
            "Keep track of component versions (client and server)",
            "Use dependency scanning tools",
            "Only obtain components from official sources",
            "Monitor for deprecation and end-of-life status",
        ],
        "related_cwes": ["CWE-1104"],
    },
    "A07:2021": {
        "title": "Identification and Authentication Failures",
        "description": "Authentication and session management weaknesses",
        "examples": [
            "Permitting brute force attacks",
            "Using weak or predictable credentials",
            "Not enforcing multi-factor authentication",
            "Session IDs exposed in URLs",
        ],
        "mitigations": [
            "Implement multi-factor authentication",
            "Enforce strong password policies",
            "Implement account lockout and CAPTCHA",
            "Use server-side session management",
            "Rotate session IDs after authentication",
        ],
        "related_cwes": ["CWE-287", "CWE-384", "CWE-613", "CWE-798"],
    },
    "A08:2021": {
        "title": "Software and Data Integrity Failures",
        "description": "Code and infrastructure that does not protect against integrity violations",
        "examples": [
            "Using untrusted sources for updates",
            "Not verifying software update signatures",
            "Insecure deserialization",
        ],
        "mitigations": [
            "Use digital signatures for software updates",
            "Use trusted repositories for dependencies",
            "Review code changes before deployment",
            "Use serialization frameworks with safe defaults",
        ],
        "related_cwes": ["CWE-345", "CWE-502", "CWE-829"],
    },
    "A09:2021": {
        "title": "Security Logging and Monitoring Failures",
        "description": "Insufficient logging, detection, monitoring, and active response",
        "examples": [
            "Not logging security-relevant events",
            "Logs only stored locally",
            "No alerting on suspicious activity",
        ],
        "mitigations": [
            "Log authentication failures, access control errors, and input validation failures",
            "Use proper log formats and centralized logging",
            "Implement real-time alerting for suspicious activity",
            "Establish incident response procedures",
        ],
        "related_cwes": ["CWE-117", "CWE-223", "CWE-778"],
    },
    "A10:2021": {
        "title": "Server-Side Request Forgery (SSRF)",
        "description": "Server makes requests to unintended locations based on user input",
        "examples": [
            "Fetching URLs from user input without validation",
            "Accessing internal services via URL manipulation",
        ],
        "mitigations": [
            "Validate and sanitize all URLs from user input",
            "Use allowlists for allowed domains and IPs",
            "Disable HTTP redirections",
            "Don't send raw responses to clients",
        ],
        "related_cwes": ["CWE-918"],
    },
}


COMMON_CWE = {
    "CWE-79": {"name": "Cross-site Scripting (XSS)", "category": "injection"},
    "CWE-89": {"name": "SQL Injection", "category": "injection"},
    "CWE-78": {"name": "OS Command Injection", "category": "injection"},
    "CWE-22": {"name": "Path Traversal", "category": "access_control"},
    "CWE-798": {"name": "Hard-coded Credentials", "category": "credentials"},
    "CWE-200": {"name": "Information Exposure", "category": "information_disclosure"},
    "CWE-209": {"name": "Error Message Information Exposure", "category": "information_disclosure"},
    "CWE-287": {"name": "Improper Authentication", "category": "authentication"},
    "CWE-327": {"name": "Use of Broken Cryptographic Algorithm", "category": "cryptography"},
    "CWE-338": {"name": "Use of Cryptographically Weak PRNG", "category": "cryptography"},
    "CWE-352": {"name": "Cross-Site Request Forgery (CSRF)", "category": "session_management"},
    "CWE-502": {"name": "Deserialization of Untrusted Data", "category": "injection"},
    "CWE-611": {"name": "XML External Entity (XXE) Processing", "category": "injection"},
    "CWE-78": {"name": "OS Command Injection", "category": "injection"},
    "CWE-862": {"name": "Missing Authorization", "category": "access_control"},
    "CWE-863": {"name": "Incorrect Authorization", "category": "access_control"},
    "CWE-918": {"name": "Server-Side Request Forgery (SSRF)", "category": "injection"},
    "CWE-942": {"name": "Permissive Cross-domain Policy", "category": "configuration"},
}


class SecurityKnowledgeBase:
    """Provides structured security knowledge."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_owasp_top_10(self) -> dict:
        """Get OWASP Top 10 (2021)."""
        return {
            "version": "2021",
            "categories": OWASP_TOP_10_2021,
            "total": len(OWASP_TOP_10_2021),
        }

    def get_owasp_category(self, category_id: str) -> Optional[dict]:
        """Get specific OWASP category details."""
        return OWASP_TOP_10_2021.get(category_id)

    def get_cwe_info(self, cwe_id: str) -> Optional[dict]:
        """Get CWE information."""
        return COMMON_CWE.get(cwe_id)

    def get_all_cwes(self) -> dict:
        """Get all CWE entries."""
        return COMMON_CWE

    def search_knowledge(self, query: str) -> list[dict]:
        """Search security knowledge base."""
        results = []
        query_lower = query.lower()

        for cat_id, cat_info in OWASP_TOP_10_2021.items():
            if (query_lower in cat_info["title"].lower() or
                query_lower in cat_info["description"].lower()):
                results.append({
                    "type": "owasp",
                    "id": cat_id,
                    "title": cat_info["title"],
                    "description": cat_info["description"],
                })

        for cwe_id, cwe_info in COMMON_CWE.items():
            if (query_lower in cwe_info["name"].lower() or
                query_lower in cwe_info["category"].lower()):
                results.append({
                    "type": "cwe",
                    "id": cwe_id,
                    "title": cwe_info["name"],
                    "category": cwe_info["category"],
                })

        return results

    def get_mitigations_for_cwe(self, cwe_id: str) -> list[str]:
        """Get mitigations for a specific CWE."""
        mitigations = []
        for cat_id, cat_info in OWASP_TOP_10_2021.items():
            if cwe_id in cat_info.get("related_cwes", []):
                mitigations.extend(cat_info.get("mitigations", []))
        return list(set(mitigations))

    def get_security_best_practices(self, domain: str = "general") -> list[dict]:
        """Get security best practices for a domain."""
        practices = {
            "general": [
                {"practice": "Defense in Depth", "description": "Use multiple layers of security controls"},
                {"practice": "Least Privilege", "description": "Grant minimum necessary permissions"},
                {"practice": "Secure Defaults", "description": "Configure secure defaults out of the box"},
                {"practice": "Fail Securely", "description": "Handle errors without exposing sensitive information"},
                {"practice": "Zero Trust", "description": "Never trust, always verify - even internal traffic"},
            ],
            "web": [
                {"practice": "Input Validation", "description": "Validate all user input server-side"},
                {"practice": "Output Encoding", "description": "Encode output to prevent XSS"},
                {"practice": "Parameterized Queries", "description": "Use parameterized queries to prevent SQL injection"},
                {"practice": "Security Headers", "description": "Implement CSP, HSTS, X-Frame-Options, etc."},
                {"practice": "HTTPS Everywhere", "description": "Use TLS for all connections"},
            ],
            "authentication": [
                {"practice": "Multi-Factor Authentication", "description": "Require MFA for sensitive operations"},
                {"practice": "Password Policy", "description": "Enforce strong password requirements"},
                {"practice": "Account Lockout", "description": "Lock accounts after failed attempts"},
                {"practice": "Session Management", "description": "Use secure, server-side session management"},
                {"practice": "Credential Storage", "description": "Hash passwords with bcrypt/argon2"},
            ],
        }
        return practices.get(domain, practices["general"])


_knowledge_base: Optional[SecurityKnowledgeBase] = None


def get_security_knowledge_base() -> SecurityKnowledgeBase:
    """Get singleton instance of SecurityKnowledgeBase."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = SecurityKnowledgeBase()
    return _knowledge_base
