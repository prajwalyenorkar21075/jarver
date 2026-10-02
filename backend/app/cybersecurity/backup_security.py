"""
Backup & Recovery Security for JARVIS cybersecurity module.

Verifies backup integrity and security:
- Backup file existence and accessibility checks
- Backup integrity verification via hashing
- Backup freshness monitoring
- Recovery procedure validation
"""

import hashlib
import logging
import time
import json
from typing import Optional
from pathlib import Path

from .security_db import get_security_db

logger = logging.getLogger(__name__)


class BackupSecurityVerifier:
    """Verifies backup integrity and security."""

    def __init__(self):
        self.db = get_security_db()
        self.logger = logging.getLogger(__name__)
        self._backup_registry: dict[str, dict] = {}

    def compute_backup_hash(self, file_path: str) -> Optional[str]:
        """Compute SHA-256 hash of a backup file."""
        try:
            path = Path(file_path)
            if not path.exists():
                return None

            sha256 = hashlib.sha256()
            with open(path, 'rb') as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    sha256.update(chunk)
            return sha256.hexdigest()

        except Exception as e:
            self.logger.error(f"Error computing backup hash: {e}")
            return None

    def register_backup(self, backup_path: str, backup_type: str = "full",
                          description: str = "") -> dict:
        """Register a backup for monitoring."""
        path = Path(backup_path)

        if not path.exists():
            return {"error": f"Backup not found: {backup_path}"}

        file_hash = self.compute_backup_hash(backup_path)
        file_stat = path.stat()

        self._backup_registry[backup_path] = {
            "path": backup_path,
            "type": backup_type,
            "description": description,
            "hash": file_hash,
            "size": file_stat.st_size,
            "last_modified": file_stat.st_mtime,
            "registered_at": time.time(),
            "verified_at": None,
        }

        return {
            "backup_path": backup_path,
            "hash": file_hash,
            "size": file_stat.st_size,
            "status": "registered",
        }

    def verify_backup_integrity(self, backup_path: str) -> dict:
        """Verify backup file integrity against registered hash."""
        if backup_path not in self._backup_registry:
            return {
                "backup_path": backup_path,
                "status": "not_registered",
                "severity": "medium",
                "description": "Backup is not registered for integrity monitoring",
            }

        registered = self._backup_registry[backup_path]
        path = Path(backup_path)

        if not path.exists():
            return {
                "backup_path": backup_path,
                "status": "missing",
                "severity": "critical",
                "description": "Backup file is missing!",
            }

        current_hash = self.compute_backup_hash(backup_path)

        if current_hash == registered["hash"]:
            registered["verified_at"] = time.time()
            return {
                "backup_path": backup_path,
                "status": "verified",
                "severity": "info",
                "hash": current_hash,
                "description": "Backup integrity verified",
            }
        else:
            return {
                "backup_path": backup_path,
                "status": "integrity_violation",
                "severity": "critical",
                "expected_hash": registered["hash"],
                "current_hash": current_hash,
                "description": "Backup file has been modified since registration!",
            }

    def check_backup_freshness(self, backup_path: str,
                                  max_age_hours: int = 24) -> dict:
        """Check if backup is fresh enough."""
        path = Path(backup_path)

        if not path.exists():
            return {
                "backup_path": backup_path,
                "status": "missing",
                "severity": "critical",
                "description": "Backup file not found",
            }

        age_seconds = time.time() - path.stat().st_mtime
        age_hours = age_seconds / 3600

        if age_hours > max_age_hours:
            return {
                "backup_path": backup_path,
                "status": "stale",
                "severity": "high",
                "age_hours": round(age_hours, 2),
                "max_age_hours": max_age_hours,
                "description": f"Backup is {age_hours:.1f} hours old (max: {max_age_hours}h)",
            }

        return {
            "backup_path": backup_path,
            "status": "fresh",
            "severity": "info",
            "age_hours": round(age_hours, 2),
            "description": f"Backup is {age_hours:.1f} hours old",
        }

    def verify_all_backups(self, max_age_hours: int = 24) -> dict:
        """Verify all registered backups."""
        self.logger.info("[BACKUP_SEC] Verifying all registered backups")

        results = []
        for backup_path in self._backup_registry:
            integrity = self.verify_backup_integrity(backup_path)
            freshness = self.check_backup_freshness(backup_path, max_age_hours)

            results.append({
                "backup_path": backup_path,
                "integrity": integrity,
                "freshness": freshness,
                "overall_status": "ok" if (
                    integrity["status"] == "verified" and
                    freshness["status"] == "fresh"
                ) else "attention_needed",
            })

        ok_count = sum(1 for r in results if r["overall_status"] == "ok")

        return {
            "total_backups": len(results),
            "healthy": ok_count,
            "needs_attention": len(results) - ok_count,
            "results": results,
            "verification_time": time.time(),
        }

    def get_backup_registry(self) -> dict:
        """Get all registered backups."""
        return {
            "registered_backups": len(self._backup_registry),
            "backups": dict(self._backup_registry),
        }


_backup_verifier: Optional[BackupSecurityVerifier] = None


def get_backup_verifier() -> BackupSecurityVerifier:
    """Get singleton instance of BackupSecurityVerifier."""
    global _backup_verifier
    if _backup_verifier is None:
        _backup_verifier = BackupSecurityVerifier()
    return _backup_verifier
