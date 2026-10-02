"""SSRF protection — validates URLs before fetching."""

import re
import ipaddress
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_BLOCKED_SCHEMES = {"file", "ftp", "gopher", "dict", "ldap"}
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

_DNS_REBINDING_HOSTS = {
    "localhost", "0.0.0.0", "127.0.0.1", "::1",
    "metadata.google.internal", "169.254.169.254",
}


class SSRFChecker:
    """Validates URLs to prevent Server-Side Request Forgery."""

    def __init__(self, allow_internal: bool = False):
        self.allow_internal = allow_internal

    def check(self, url: str) -> tuple[bool, str]:
        try:
            parsed = urlparse(url)
        except Exception:
            return False, "Invalid URL"

        if parsed.scheme not in ("http", "https"):
            return False, f"Blocked scheme: {parsed.scheme}"

        hostname = parsed.hostname
        if not hostname:
            return False, "No hostname"

        if hostname.lower() in _DNS_REBINDING_HOSTS:
            if not self.allow_internal:
                return False, f"Blocked internal host: {hostname}"

        try:
            addr = ipaddress.ip_address(hostname)
            if not self.allow_internal:
                for net in _PRIVATE_NETWORKS:
                    if addr in net:
                        return False, f"Blocked private IP: {hostname}"
        except ValueError:
            pass

        return True, "OK"

    def is_safe(self, url: str) -> bool:
        safe, _ = self.check(url)
        return safe


ssrf_checker = SSRFChecker()
