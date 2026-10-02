"""
Reconnaissance and Port/Service Assessment for Ethical Hacking.

Provides real port scanning, service detection, and asset discovery
with strict authorization controls.
"""

import socket
import logging
import time
import concurrent.futures
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager

from .core import get_ethical_hacking_engine, Severity

logger = logging.getLogger(__name__)


@dataclass
class PortResult:
    port: int
    state: str
    service: str = ""
    version: str = ""
    banner: str = ""
    protocol: str = "tcp"


@dataclass
class HostResult:
    host: str
    is_up: bool
    open_ports: list[PortResult]
    os_guess: str = ""
    hostname: str = ""
    scan_time: float = 0.0


COMMON_PORTS = [
    20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995,
    1723, 3306, 3389, 5900, 8080, 8443, 8888, 5432, 1433, 27017, 6379, 9200,
    5672, 15672, 11211, 2181, 9092, 8081, 8082, 8083, 8084, 8085, 8086, 8087,
    8088, 8089, 8090, 9000, 9001, 9090, 9091, 4443, 8443, 8888, 9999, 10000,
]

SERVICE_SIGNATURES = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    993: "IMAPS",
    995: "POP3S",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5900: "VNC",
    6379: "Redis",
    8080: "HTTP-Proxy",
    1433: "MSSQL",
    27017: "MongoDB",
}


class ReconnaissanceScanner:
    """Performs reconnaissance and port scanning on authorized targets."""

    def __init__(self):
        self.engine = get_ethical_hacking_engine()
        logger.info("[RECON] Reconnaissance scanner initialized")

    def scan_port(self, host: str, port: int, timeout: float = 1.0) -> PortResult:
        result = PortResult(port=port, state="closed")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock_result = sock.connect_ex((host, port))

            if sock_result == 0:
                result.state = "open"
                result.service = SERVICE_SIGNATURES.get(port, "unknown")

                if port in [80, 8080, 8000, 8888, 3000, 5000]:
                    result.banner = self._grab_http_banner(host, port, timeout)
                elif port == 22:
                    result.banner = self._grab_ssh_banner(host, port, timeout)
                elif port == 21:
                    result.banner = self._grab_ftp_banner(host, port, timeout)

            sock.close()
        except Exception as e:
            logger.debug(f"[RECON] Port {port} scan error: {e}")
            result.state = "error"

        return result

    def _grab_http_banner(self, host: str, port: int, timeout: float) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))

            request = f"HEAD / HTTP/1.0\r\nHost: {host}\r\n\r\n"
            sock.send(request.encode())

            response = sock.recv(1024).decode('utf-8', errors='ignore')
            sock.close()

            for line in response.split('\n'):
                if 'Server:' in line:
                    return line.strip()
            return response.split('\n')[0] if response else ""
        except Exception:
            return ""

    def _grab_ssh_banner(self, host: str, port: int, timeout: float) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            banner = sock.recv(256).decode('utf-8', errors='ignore').strip()
            sock.close()
            return banner
        except Exception:
            return ""

    def _grab_ftp_banner(self, host: str, port: int, timeout: float) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
            sock.close()
            return banner
        except Exception:
            return ""

    def host_discovery(self, host: str, timeout: float = 1.0) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, 80))
            sock.close()
            return result == 0
        except Exception:
            return False

    def port_scan(self, host: str, ports: Optional[list[int]] = None,
                  scope_id: Optional[str] = None, timeout: float = 1.0) -> dict:
        authorized, msg = self.engine.safety_controller.verify_authorization(host, "port_scan", scope_id)
        if not authorized:
            return {"success": False, "error": msg, "findings": []}

        if not self.engine.safety_controller.check_rate_limit(host, "port_scan"):
            return {"success": False, "error": "Rate limit exceeded", "findings": []}

        ports = ports or COMMON_PORTS[:100]

        start_time = time.time()
        open_ports = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            future_to_port = {executor.submit(self.scan_port, host, port, timeout): port
                              for port in ports}

            for future in concurrent.futures.as_completed(future_to_port):
                port_result = future.result()
                if port_result.state == "open":
                    open_ports.append(port_result)

        scan_time = time.time() - start_time

        host_result = HostResult(
            host=host,
            is_up=len(open_ports) > 0,
            open_ports=open_ports,
            scan_time=scan_time,
        )

        findings = []
        for port_result in open_ports:
            finding = self.engine.add_finding(
                finding_type="open_port",
                severity="info" if port_result.port in [80, 443] else "low",
                title=f"Open Port: {port_result.port}/{port_result.protocol}",
                description=f"Port {port_result.port} is open running {port_result.service}",
                target=host,
                scope_id=scope_id or "",
                evidence={
                    "port": port_result.port,
                    "service": port_result.service,
                    "banner": port_result.banner,
                    "protocol": port_result.protocol,
                },
                affected_component=f"port_{port_result.port}",
                remediation=self._get_port_remediation(port_result),
            )
            findings.append(finding)

        logger.info(f"[RECON] Port scan complete: {host} - {len(open_ports)} open ports in {scan_time:.2f}s")

        return {
            "success": True,
            "host": host,
            "is_up": host_result.is_up,
            "open_ports": [p.__dict__ for p in open_ports],
            "scan_time": scan_time,
            "findings": findings,
        }

    def _get_port_remediation(self, port_result: PortResult) -> str:
        risky_services = {
            "Telnet": "Replace Telnet with SSH for encrypted communication",
            "FTP": "Replace FTP with SFTP or FTPS for encrypted file transfer",
            "RDP": "Ensure RDP is secured with NLA and strong authentication",
            "SMB": "Ensure SMB is properly secured and not exposed to internet",
            "VNC": "Use SSH tunneling for VNC connections",
        }

        if port_result.service in risky_services:
            return risky_services[port_result.service]

        if port_result.port < 1024:
            return "Verify this service is required and properly secured"

        return "Verify this service is authorized and properly secured"

    def service_enumeration(self, host: str, port: int,
                            scope_id: Optional[str] = None) -> dict:
        authorized, msg = self.engine.safety_controller.verify_authorization(host, "service_enum", scope_id)
        if not authorized:
            return {"success": False, "error": msg}

        result = {
            "success": True,
            "host": host,
            "port": port,
            "service": SERVICE_SIGNATURES.get(port, "unknown"),
            "banner": "",
            "version": "",
        }

        if port in [80, 8080, 8000, 8888, 3000, 5000, 443]:
            result["banner"] = self._grab_http_banner(host, port)
        elif port == 22:
            result["banner"] = self._grab_ssh_banner(host, port)
        elif port == 21:
            result["banner"] = self._grab_ftp_banner(host, port)

        return result

    def network_discovery(self, network: str, scope_id: Optional[str] = None) -> dict:
        authorized, msg = self.engine.safety_controller.verify_authorization(network, "network_discovery", scope_id)
        if not authorized:
            return {"success": False, "error": msg}

        import ipaddress
        try:
            network_obj = ipaddress.ip_network(network, strict=False)
        except ValueError as e:
            return {"success": False, "error": f"Invalid network: {e}"}

        hosts = []
        for ip in network_obj.hosts():
            ip_str = str(ip)
            if self.host_discovery(ip_str):
                hosts.append(ip_str)

        return {
            "success": True,
            "network": network,
            "discovered_hosts": hosts,
            "total_hosts": len(hosts),
        }


_recon_scanner: Optional[ReconnaissanceScanner] = None


def get_recon_scanner() -> ReconnaissanceScanner:
    global _recon_scanner
    if _recon_scanner is None:
        _recon_scanner = ReconnaissanceScanner()
    return _recon_scanner
