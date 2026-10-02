"""
Network Security Monitor for JARVIS cybersecurity module.

Inspects local network interfaces, connections, listening ports, DNS activity,
and connection metadata. Detects unusual or suspicious patterns.
Does not perform unauthorized scanning of external systems.
"""

import logging
import subprocess
import platform
import re
import socket
from typing import Optional

from .security_db import get_security_db

logger = logging.getLogger(__name__)


class NetworkSecurityMonitor:
    """
    Network security monitoring for local systems.
    
    Monitors network interfaces, connections, listening ports, and DNS activity.
    Only inspects local network state - does not scan external systems.
    """

    def __init__(self):
        self.db = get_security_db()
        self._findings: list[dict] = []
        
        logger.info("[NET_SEC] Network security monitor initialized")

    def check_listening_ports(self) -> dict:
        """
        Check listening ports on the local system.
        
        Returns:
            Dict with listening ports and findings
        """
        findings = []
        listening_ports = []
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    
                    for line in lines:
                        if 'LISTENING' in line:
                            parts = line.split()
                            if len(parts) >= 5:
                                local_address = parts[1]
                                pid = parts[4]
                                
                                # Extract port
                                match = re.search(r':(\d+)$', local_address)
                                if match:
                                    port = int(match.group(1))
                                    
                                    port_info = {
                                        "port": port,
                                        "address": local_address,
                                        "pid": pid,
                                    }
                                    listening_ports.append(port_info)
                                    
                                    # Check for suspicious ports
                                    suspicious_ports = {
                                        4444: "Common reverse shell port",
                                        5555: "Common backdoor port",
                                        6666: "Common backdoor port",
                                        1337: "Common hacker port",
                                        31337: "Common backdoor port (eleet)",
                                    }
                                    
                                    if port in suspicious_ports:
                                        findings.append({
                                            "type": "suspicious_port",
                                            "severity": "high",
                                            "port": port,
                                            "pid": pid,
                                            "description": suspicious_ports[port],
                                        })
            
            logger.info(f"[NET_SEC] Port check complete: {len(listening_ports)} ports, {len(findings)} findings")
            
            return {
                "success": True,
                "listening_ports": listening_ports,
                "total_ports": len(listening_ports),
                "findings": findings,
                "total_findings": len(findings),
            }
            
        except Exception as e:
            logger.error(f"[NET_SEC] Error checking listening ports: {e}")
            return {
                "success": False,
                "error": str(e),
                "listening_ports": [],
                "findings": [],
            }

    def check_active_connections(self) -> dict:
        """
        Check active network connections.
        
        Returns:
            Dict with active connections and findings
        """
        findings = []
        connections = []
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    
                    for line in lines:
                        if 'ESTABLISHED' in line:
                            parts = line.split()
                            if len(parts) >= 5:
                                local_address = parts[1]
                                remote_address = parts[2]
                                pid = parts[4]
                                
                                conn_info = {
                                    "local": local_address,
                                    "remote": remote_address,
                                    "pid": pid,
                                    "state": "ESTABLISHED",
                                }
                                connections.append(conn_info)
                                
                                # Check for suspicious remote addresses
                                suspicious_patterns = [
                                    r":4444$",
                                    r":5555$",
                                    r":6666$",
                                    r":1337$",
                                ]
                                
                                for pattern in suspicious_patterns:
                                    if re.search(pattern, remote_address):
                                        findings.append({
                                            "type": "suspicious_connection",
                                            "severity": "high",
                                            "remote": remote_address,
                                            "pid": pid,
                                            "description": f"Suspicious connection to {remote_address}",
                                        })
            
            logger.info(f"[NET_SEC] Connection check complete: {len(connections)} connections, {len(findings)} findings")
            
            return {
                "success": True,
                "connections": connections,
                "total_connections": len(connections),
                "findings": findings,
                "total_findings": len(findings),
            }
            
        except Exception as e:
            logger.error(f"[NET_SEC] Error checking connections: {e}")
            return {
                "success": False,
                "error": str(e),
                "connections": [],
                "findings": [],
            }

    def check_network_interfaces(self) -> dict:
        """
        Check network interfaces.
        
        Returns:
            Dict with network interface information
        """
        interfaces = []
        
        try:
            # Get hostname
            hostname = socket.gethostname()
            
            # Get IP addresses
            try:
                ip_addresses = socket.gethostbyname_ex(hostname)[2]
            except socket.gaierror:
                ip_addresses = []
            
            for ip in ip_addresses:
                interfaces.append({
                    "name": hostname,
                    "ip": ip,
                    "type": "ipv4",
                })
            
            # Add localhost
            interfaces.append({
                "name": "localhost",
                "ip": "127.0.0.1",
                "type": "loopback",
            })
            
            logger.info(f"[NET_SEC] Interface check complete: {len(interfaces)} interfaces")
            
            return {
                "success": True,
                "interfaces": interfaces,
                "total_interfaces": len(interfaces),
            }
            
        except Exception as e:
            logger.error(f"[NET_SEC] Error checking network interfaces: {e}")
            return {
                "success": False,
                "error": str(e),
                "interfaces": [],
            }

    def check_dns_configuration(self) -> dict:
        """
        Check DNS configuration.
        
        Returns:
            Dict with DNS configuration and findings
        """
        findings = []
        dns_config = {}
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["ipconfig", "/all"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                if result.returncode == 0:
                    # Extract DNS servers
                    dns_servers = re.findall(r"DNS Servers.*?(\d+\.\d+\.\d+\.\d+)", result.stdout)
                    dns_config["dns_servers"] = dns_servers
                    
                    # Check for suspicious DNS servers
                    suspicious_dns = ["8.8.8.8", "8.8.4.4"]  # Public DNS (not necessarily bad, but worth noting)
                    for dns in dns_servers:
                        if dns in suspicious_dns:
                            findings.append({
                                "type": "public_dns",
                                "severity": "low",
                                "dns": dns,
                                "description": f"Using public DNS server: {dns}",
                            })
            
            logger.info(f"[NET_SEC] DNS check complete: {len(findings)} findings")
            
            return {
                "success": True,
                "dns_config": dns_config,
                "findings": findings,
                "total_findings": len(findings),
            }
            
        except Exception as e:
            logger.error(f"[NET_SEC] Error checking DNS configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "dns_config": {},
                "findings": [],
            }

    def comprehensive_network_check(self) -> dict:
        """
        Perform comprehensive network security check.
        
        Returns:
            Dict with all findings
        """
        logger.info("[NET_SEC] Starting comprehensive network security check")
        
        all_findings = []
        
        # Check listening ports
        port_result = self.check_listening_ports()
        if port_result["success"]:
            all_findings.extend(port_result["findings"])
        
        # Check active connections
        conn_result = self.check_active_connections()
        if conn_result["success"]:
            all_findings.extend(conn_result["findings"])
        
        # Check DNS
        dns_result = self.check_dns_configuration()
        if dns_result["success"]:
            all_findings.extend(dns_result["findings"])
        
        # Log findings to database
        for finding in all_findings:
            self.db.insert_event(
                event_type=finding["type"],
                severity=finding["severity"],
                description=finding["description"],
                source="network_security_monitor",
                details=finding,
            )
        
        logger.info(f"[NET_SEC] Comprehensive check complete: {len(all_findings)} total findings")
        
        return {
            "success": True,
            "findings": all_findings,
            "total_findings": len(all_findings),
            "checks_performed": {
                "listening_ports": port_result.get("total_ports", 0),
                "active_connections": conn_result.get("total_connections", 0),
            },
        }


# Singleton instance
_network_security_monitor: Optional[NetworkSecurityMonitor] = None


def get_network_security_monitor() -> NetworkSecurityMonitor:
    """Get or create the network security monitor singleton."""
    global _network_security_monitor
    if _network_security_monitor is None:
        _network_security_monitor = NetworkSecurityMonitor()
    return _network_security_monitor
