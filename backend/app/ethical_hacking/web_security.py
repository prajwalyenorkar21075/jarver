"""
Web Application and API Security Testing for Ethical Hacking.

Tests for OWASP Top 10 vulnerabilities, authentication issues, input validation,
and API security weaknesses.
"""

import logging
import time
import re
import json
from typing import Optional
from urllib.parse import urljoin, urlparse
import httpx

from .core import get_ethical_hacking_engine, Severity

logger = logging.getLogger(__name__)


class WebSecurityTester:
    """Tests web applications for security vulnerabilities."""

    def __init__(self):
        self.engine = get_ethical_hacking_engine()
        self.client = httpx.Client(timeout=10.0, follow_redirects=True)
        logger.info("[WEB_SEC] Web security tester initialized")

    def test_security_headers(self, url: str, scope_id: Optional[str] = None) -> dict:
        authorized, msg = self.engine.safety_controller.verify_authorization(url, "web_test", scope_id)
        if not authorized:
            return {"success": False, "error": msg, "findings": []}

        findings = []

        try:
            response = self.client.get(url)
            headers = response.headers

            security_headers = {
                "Strict-Transport-Security": {
                    "severity": "high",
                    "description": "Missing HSTS header allows downgrade attacks",
                    "remediation": "Add Strict-Transport-Security header with max-age=31536000",
                },
                "Content-Security-Policy": {
                    "severity": "medium",
                    "description": "Missing CSP header increases XSS risk",
                    "remediation": "Implement Content-Security-Policy header",
                },
                "X-Content-Type-Options": {
                    "severity": "low",
                    "description": "Missing X-Content-Type-Options header",
                    "remediation": "Add X-Content-Type-Options: nosniff header",
                },
                "X-Frame-Options": {
                    "severity": "medium",
                    "description": "Missing X-Frame-Options allows clickjacking",
                    "remediation": "Add X-Frame-Options: DENY or SAMEORIGIN header",
                },
                "X-XSS-Protection": {
                    "severity": "low",
                    "description": "Missing X-XSS-Protection header",
                    "remediation": "Add X-XSS-Protection: 1; mode=block header",
                },
                "Referrer-Policy": {
                    "severity": "low",
                    "description": "Missing Referrer-Policy header",
                    "remediation": "Add Referrer-Policy header",
                },
            }

            for header, info in security_headers.items():
                if header not in headers:
                    finding = self.engine.add_finding(
                        finding_type="missing_security_header",
                        severity=info["severity"],
                        title=f"Missing Security Header: {header}",
                        description=info["description"],
                        target=url,
                        scope_id=scope_id or "",
                        evidence={"header": header, "url": url},
                        affected_component="HTTP Headers",
                        remediation=info["remediation"],
                        references=["https://owasp.org/www-project-secure-headers/"],
                    )
                    findings.append(finding)

        except Exception as e:
            logger.error(f"[WEB_SEC] Error testing {url}: {e}")
            return {"success": False, "error": str(e), "findings": []}

        return {"success": True, "findings": findings, "url": url}

    def test_ssl_tls(self, url: str, scope_id: Optional[str] = None) -> dict:
        authorized, msg = self.engine.safety_controller.verify_authorization(url, "ssl_test", scope_id)
        if not authorized:
            return {"success": False, "error": msg, "findings": []}

        findings = []

        if url.startswith("http://"):
            finding = self.engine.add_finding(
                finding_type="insecure_protocol",
                severity="high",
                title="Application Using HTTP Instead of HTTPS",
                description="Application is not using TLS encryption",
                target=url,
                scope_id=scope_id or "",
                evidence={"url": url},
                affected_component="Transport Layer",
                remediation="Configure application to use HTTPS with valid TLS certificate",
                references=["https://owasp.org/www-community/controls/Transport_Layer_Protection_Cheat_Sheet"],
            )
            findings.append(finding)

        return {"success": True, "findings": findings, "url": url}

    def test_directory_traversal(self, url: str, scope_id: Optional[str] = None) -> dict:
        authorized, msg = self.engine.safety_controller.verify_authorization(url, "traversal_test", scope_id)
        if not authorized:
            return {"success": False, "error": msg, "findings": []}

        findings = []
        test_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]

        for test_path in test_paths:
            test_url = urljoin(url, test_path)
            try:
                response = self.client.get(test_url)
                if response.status_code == 200:
                    if "root:" in response.text or "[extensions]" in response.text:
                        finding = self.engine.add_finding(
                            finding_type="directory_traversal",
                            severity="critical",
                            title="Directory Traversal Vulnerability",
                            description="Application is vulnerable to path traversal attacks",
                            target=url,
                            scope_id=scope_id or "",
                            evidence={"test_path": test_path, "url": test_url},
                            affected_component="File Access Control",
                            remediation="Implement proper input validation and path canonicalization",
                            references=["https://owasp.org/www-community/attacks/Path_Traversal"],
                        )
                        findings.append(finding)
                        break
            except Exception:
                pass

        return {"success": True, "findings": findings, "url": url}

    def test_xss(self, url: str, scope_id: Optional[str] = None) -> dict:
        authorized, msg = self.engine.safety_controller.verify_authorization(url, "xss_test", scope_id)
        if not authorized:
            return {"success": False, "error": msg, "findings": []}

        findings = []
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
        ]

        parsed = urlparse(url)
        if parsed.query:
            for payload in xss_payloads:
                test_url = url.replace(parsed.query, f"test={payload}")
                try:
                    response = self.client.get(test_url)
                    if payload in response.text:
                        finding = self.engine.add_finding(
                            finding_type="xss",
                            severity="high",
                            title="Cross-Site Scripting (XSS) Vulnerability",
                            description="Application reflects user input without proper sanitization",
                            target=url,
                            scope_id=scope_id or "",
                            evidence={"payload": payload, "url": test_url},
                            affected_component="Input Validation",
                            remediation="Implement proper input validation and output encoding",
                            references=["https://owasp.org/www-community/attacks/xss/"],
                        )
                        findings.append(finding)
                        break
                except Exception:
                    pass

        return {"success": True, "findings": findings, "url": url}

    def test_information_disclosure(self, url: str, scope_id: Optional[str] = None) -> dict:
        authorized, msg = self.engine.safety_controller.verify_authorization(url, "info_disclosure", scope_id)
        if not authorized:
            return {"success": False, "error": msg, "findings": []}

        findings = []

        try:
            response = self.client.get(url)

            server_header = response.headers.get("Server", "")
            if server_header and re.search(r'\d+\.\d+', server_header):
                finding = self.engine.add_finding(
                    finding_type="information_disclosure",
                    severity="low",
                    title="Server Version Disclosure",
                    description=f"Server header reveals version information: {server_header}",
                    target=url,
                    scope_id=scope_id or "",
                    evidence={"header": "Server", "value": server_header},
                    affected_component="HTTP Headers",
                    remediation="Remove or genericize Server header to prevent version disclosure",
                    references=["https://owasp.org/www-project-web-security-testing-guide/"],
                )
                findings.append(finding)

            x_powered_by = response.headers.get("X-Powered-By", "")
            if x_powered_by:
                finding = self.engine.add_finding(
                    finding_type="information_disclosure",
                    severity="low",
                    title="Technology Stack Disclosure",
                    description=f"X-Powered-By header reveals technology: {x_powered_by}",
                    target=url,
                    scope_id=scope_id or "",
                    evidence={"header": "X-Powered-By", "value": x_powered_by},
                    affected_component="HTTP Headers",
                    remediation="Remove X-Powered-By header",
                    references=["https://owasp.org/www-project-web-security-testing-guide/"],
                )
                findings.append(finding)

        except Exception as e:
            logger.error(f"[WEB_SEC] Error testing {url}: {e}")

        return {"success": True, "findings": findings, "url": url}

    def comprehensive_test(self, url: str, scope_id: Optional[str] = None) -> dict:
        authorized, msg = self.engine.safety_controller.verify_authorization(url, "web_comprehensive", scope_id)
        if not authorized:
            return {"success": False, "error": msg, "findings": []}

        logger.info(f"[WEB_SEC] Starting comprehensive web test: {url}")

        all_findings = []

        tests = [
            self.test_security_headers,
            self.test_ssl_tls,
            self.test_information_disclosure,
            self.test_directory_traversal,
            self.test_xss,
        ]

        for test in tests:
            try:
                result = test(url, scope_id)
                if result["success"]:
                    all_findings.extend(result["findings"])
            except Exception as e:
                logger.error(f"[WEB_SEC] Test failed: {e}")

        logger.info(f"[WEB_SEC] Comprehensive test complete: {len(all_findings)} findings")

        return {
            "success": True,
            "url": url,
            "findings": all_findings,
            "total_findings": len(all_findings),
        }


class APISecurityTester:
    """Tests APIs for security vulnerabilities."""

    def __init__(self):
        self.engine = get_ethical_hacking_engine()
        self.client = httpx.Client(timeout=10.0)
        logger.info("[API_SEC] API security tester initialized")

    def test_authentication(self, base_url: str, endpoints: list[str],
                            scope_id: Optional[str] = None) -> dict:
        authorized, msg = self.engine.safety_controller.verify_authorization(base_url, "api_auth_test", scope_id)
        if not authorized:
            return {"success": False, "error": msg, "findings": []}

        findings = []

        for endpoint in endpoints:
            url = urljoin(base_url, endpoint)
            try:
                response = self.client.get(url)

                if response.status_code not in [401, 403]:
                    finding = self.engine.add_finding(
                        finding_type="missing_authentication",
                        severity="high",
                        title=f"API Endpoint Missing Authentication: {endpoint}",
                        description=f"Endpoint {endpoint} is accessible without authentication",
                        target=base_url,
                        scope_id=scope_id or "",
                        evidence={"endpoint": endpoint, "status_code": response.status_code},
                        affected_component="Authentication",
                        remediation="Implement proper authentication for all API endpoints",
                        references=["https://owasp.org/API-Security/"],
                    )
                    findings.append(finding)

            except Exception as e:
                logger.debug(f"[API_SEC] Error testing {url}: {e}")

        return {"success": True, "findings": findings, "base_url": base_url}

    def test_cors(self, base_url: str, scope_id: Optional[str] = None) -> dict:
        authorized, msg = self.engine.safety_controller.verify_authorization(base_url, "api_cors_test", scope_id)
        if not authorized:
            return {"success": False, "error": msg, "findings": []}

        findings = []

        try:
            headers = {"Origin": "https://evil.com"}
            response = self.client.get(base_url, headers=headers)

            acao = response.headers.get("Access-Control-Allow-Origin", "")
            if acao == "*" or acao == "https://evil.com":
                finding = self.engine.add_finding(
                    finding_type="cors_misconfiguration",
                    severity="medium",
                    title="Overly Permissive CORS Configuration",
                    description="API allows requests from any origin",
                    target=base_url,
                    scope_id=scope_id or "",
                    evidence={"header": acao},
                    affected_component="CORS Configuration",
                    remediation="Restrict CORS to specific trusted origins",
                    references=["https://owasp.org/www-community/attacks/CORS_OriginHeaderScrutiny"],
                )
                findings.append(finding)

        except Exception as e:
            logger.debug(f"[API_SEC] Error testing CORS: {e}")

        return {"success": True, "findings": findings, "base_url": base_url}

    def test_rate_limiting(self, base_url: str, endpoint: str = "/",
                          scope_id: Optional[str] = None) -> dict:
        authorized, msg = self.engine.safety_controller.verify_authorization(base_url, "api_rate_test", scope_id)
        if not authorized:
            return {"success": False, "error": msg, "findings": []}

        findings = []
        url = urljoin(base_url, endpoint)

        try:
            responses = []
            for _ in range(100):
                response = self.client.get(url)
                responses.append(response.status_code)

            if all(code == 200 for code in responses):
                finding = self.engine.add_finding(
                    finding_type="missing_rate_limiting",
                    severity="medium",
                    title="API Missing Rate Limiting",
                    description="API does not implement rate limiting",
                    target=base_url,
                    scope_id=scope_id or "",
                    evidence={"requests": 100, "all_successful": True},
                    affected_component="Rate Limiting",
                    remediation="Implement rate limiting to prevent abuse",
                    references=["https://owasp.org/API-Security/"],
                )
                findings.append(finding)

        except Exception as e:
            logger.debug(f"[API_SEC] Error testing rate limiting: {e}")

        return {"success": True, "findings": findings, "base_url": base_url}


_web_security_tester: Optional[WebSecurityTester] = None
_api_security_tester: Optional[APISecurityTester] = None


def get_web_security_tester() -> WebSecurityTester:
    global _web_security_tester
    if _web_security_tester is None:
        _web_security_tester = WebSecurityTester()
    return _web_security_tester


def get_api_security_tester() -> APISecurityTester:
    global _api_security_tester
    if _api_security_tester is None:
        _api_security_tester = APISecurityTester()
    return _api_security_tester
