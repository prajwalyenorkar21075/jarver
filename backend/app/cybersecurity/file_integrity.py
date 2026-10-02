"""
File Integrity Monitor for JARVIS cybersecurity module.

Monitors files for unauthorized modifications using:
- Cryptographic hash baselining (SHA-256)
- Periodic integrity verification
- Change detection and alerting
- Critical system file monitoring
"""

import hashlib
import logging
import time
import os
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field

from .security_db import get_security_db

logger = logging.getLogger(__name__)


@dataclass
class IntegrityFinding:
    """Represents a file integrity finding."""
    file_path: str
    status: str  # modified, deleted, new, baseline
    previous_hash: str = ""
    current_hash: str = ""
    change_type: str = ""
    severity: str = "medium"
    description: str = ""


CRITICAL_PATHS_WINDOWS = [
    r"C:\Windows\System32\drivers\etc\hosts",
    r"C:\Windows\System32\config\SAM",
    r"C:\Windows\System32\cmd.exe",
    r"C:\Windows\System32\powershell.exe",
]


class FileIntegrityMonitor:
    """Monitors files for unauthorized modifications."""

    def __init__(self):
        self.db = get_security_db()
        self.logger = logging.getLogger(__name__)
        self.baseline_files = {}

    def compute_file_hash(self, file_path: str, algorithm: str = "sha256") -> Optional[str]:
        """Compute cryptographic hash of a file."""
        try:
            path = Path(file_path)
            if not path.exists():
                return None

            hash_func = hashlib.new(algorithm)
            with open(path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    hash_func.update(chunk)
            return hash_func.hexdigest()

        except Exception as e:
            self.logger.error(f"Error computing hash for {file_path}: {e}")
            return None

    def create_baseline(self, file_path: str) -> dict:
        """Create integrity baseline for a file."""
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        file_hash = self.compute_file_hash(file_path)
        file_stat = path.stat()

        baseline_id = self.db.insert_file_baseline(
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_stat.st_size,
            last_modified=file_stat.st_mtime
        )

        self.baseline_files[file_path] = {
            "id": baseline_id,
            "hash": file_hash,
            "size": file_stat.st_size,
            "last_modified": file_stat.st_mtime,
            "baseline_at": time.time(),
        }

        return {
            "file_path": file_path,
            "hash": file_hash,
            "size": file_stat.st_size,
            "baseline_id": baseline_id,
            "status": "baseline_created",
        }

    def create_baseline_directory(self, directory: str,
                                   extensions: Optional[list] = None,
                                   exclude_patterns: Optional[list] = None) -> dict:
        """Create integrity baseline for all files in a directory."""
        self.logger.info(f"[FIM] Creating baseline for directory: {directory}")

        path = Path(directory)
        if not path.exists():
            return {"error": f"Directory not found: {directory}"}

        exclude_patterns = exclude_patterns or [
            "node_modules", ".git", "__pycache__", ".venv", "venv"
        ]

        baselined = 0
        errors = 0

        for file_path in path.rglob("*"):
            if file_path.is_file():
                if any(pattern in str(file_path) for pattern in exclude_patterns):
                    continue
                if extensions and file_path.suffix not in extensions:
                    continue

                result = self.create_baseline(str(file_path))
                if "error" not in result:
                    baselined += 1
                else:
                    errors += 1

        return {
            "directory": directory,
            "files_baselined": baselined,
            "errors": errors,
            "status": "completed",
        }

    def verify_file(self, file_path: str) -> dict:
        """Verify file integrity against baseline."""
        current_hash = self.compute_file_hash(file_path)

        if current_hash is None:
            return {
                "file_path": file_path,
                "status": "deleted",
                "severity": "high",
                "description": f"File has been deleted: {file_path}",
            }

        if file_path in self.baseline_files:
            baseline_hash = self.baseline_files[file_path]["hash"]

            if current_hash == baseline_hash:
                return {
                    "file_path": file_path,
                    "status": "unchanged",
                    "hash": current_hash,
                    "severity": "info",
                }
            else:
                return {
                    "file_path": file_path,
                    "status": "modified",
                    "previous_hash": baseline_hash,
                    "current_hash": current_hash,
                    "severity": "high",
                    "description": f"File has been modified: {file_path}",
                    "change_type": "content_changed",
                }
        else:
            return {
                "file_path": file_path,
                "status": "no_baseline",
                "hash": current_hash,
                "severity": "info",
                "description": "No baseline exists for this file",
            }

    def verify_directory(self, directory: str) -> dict:
        """Verify integrity of all baselined files in a directory."""
        self.logger.info(f"[FIM] Verifying directory integrity: {directory}")

        findings = []
        unchanged = 0
        modified = 0
        deleted = 0

        for file_path in list(self.baseline_files.keys()):
            if file_path.startswith(directory):
                result = self.verify_file(file_path)
                status = result.get("status")

                if status == "unchanged":
                    unchanged += 1
                elif status == "modified":
                    modified += 1
                    findings.append(result)
                    self.db.insert_event(
                        event_type="file_integrity_violation",
                        severity="high",
                        description=f"File modified: {file_path}",
                        source="file_integrity_monitor",
                        details=result
                    )
                elif status == "deleted":
                    deleted += 1
                    findings.append(result)
                    self.db.insert_event(
                        event_type="file_deleted",
                        severity="high",
                        description=f"File deleted: {file_path}",
                        source="file_integrity_monitor",
                        details=result
                    )

        return {
            "directory": directory,
            "total_monitored": len([f for f in self.baseline_files if f.startswith(directory)]),
            "unchanged": unchanged,
            "modified": modified,
            "deleted": deleted,
            "findings": findings,
            "verification_time": time.time(),
        }

    def monitor_critical_system_files(self) -> dict:
        """Monitor critical system files for unauthorized changes."""
        self.logger.info("[FIM] Monitoring critical system files")

        findings = []

        for file_path in CRITICAL_PATHS_WINDOWS:
            if Path(file_path).exists():
                result = self.verify_file(file_path)
                if result.get("status") not in ("unchanged", "no_baseline"):
                    findings.append(result)

        return {
            "monitored_files": len(CRITICAL_PATHS_WINDOWS),
            "findings": findings,
            "check_time": time.time(),
        }

    def comprehensive_integrity_check(self, paths: Optional[list] = None) -> dict:
        """Run comprehensive file integrity check."""
        self.logger.info("[FIM] Starting comprehensive integrity check")

        all_findings = []

        for file_path in list(self.baseline_files.keys()):
            result = self.verify_file(file_path)
            if result.get("status") not in ("unchanged",):
                all_findings.append(result)

        system_check = self.monitor_critical_system_files()
        all_findings.extend(system_check.get("findings", []))

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for finding in all_findings:
            severity = finding.get("severity", "info")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "total_findings": len(all_findings),
            "baselined_files": len(self.baseline_files),
            "critical": severity_counts["critical"],
            "high": severity_counts["high"],
            "medium": severity_counts["medium"],
            "low": severity_counts["low"],
            "findings": all_findings,
            "check_time": time.time(),
        }


_fim: Optional[FileIntegrityMonitor] = None


def get_file_integrity_monitor() -> FileIntegrityMonitor:
    """Get singleton instance of FileIntegrityMonitor."""
    global _fim
    if _fim is None:
        _fim = FileIntegrityMonitor()
    return _fim
