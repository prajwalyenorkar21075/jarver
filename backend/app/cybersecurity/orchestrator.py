"""
Security Orchestrator - Central coordinator for JARVIS cybersecurity operations.

Routes tasks to appropriate security components, prevents duplicate operations,
maintains audit logs, and coordinates all defensive security functions.
"""

import logging
import time
import hashlib
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from .security_db import get_security_db

logger = logging.getLogger(__name__)


class SecurityOperation(Enum):
    """Security operation types."""
    THREAT_SCAN = "threat_scan"
    ENDPOINT_CHECK = "endpoint_check"
    NETWORK_MONITOR = "network_monitor"
    VULN_SCAN = "vuln_scan"
    WEB_SECURITY_TEST = "web_security_test"
    CODE_ANALYSIS = "code_analysis"
    DEPENDENCY_SCAN = "dependency_scan"
    FILE_INTEGRITY_CHECK = "file_integrity_check"
    MALWARE_ANALYSIS = "malware_analysis"
    LOG_ANALYSIS = "log_analysis"
    SECRET_SCAN = "secret_scan"
    DATABASE_AUDIT = "database_audit"
    INCIDENT_RESPONSE = "incident_response"
    BACKUP_VERIFY = "backup_verify"
    PRIVACY_CHECK = "privacy_check"
    SECURITY_REPORT = "security_report"


class OperationStatus(Enum):
    """Operation status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SecurityOperationRecord:
    """Record of a security operation."""
    operation_id: str
    operation_type: SecurityOperation
    timestamp: float
    target: str
    status: OperationStatus
    request: dict
    result: Optional[dict] = None
    error: Optional[str] = None
    duration: float = 0.0
    actor: str = "system"


class SecurityOrchestrator:
    """
    Central coordinator for all cybersecurity operations.
    
    Prevents duplicate operations, routes tasks to appropriate components,
    maintains audit logs, and enforces security policies.
    """

    def __init__(self):
        self.db = get_security_db()
        self._active_operations: dict[str, SecurityOperationRecord] = {}
        self._operation_history: list[SecurityOperationRecord] = []
        self._operation_locks: dict[str, float] = {}  # target -> timestamp
        self._rate_limits: dict[str, list[float]] = {}  # operation_type -> [timestamps]
        
        # Rate limiting configuration (operations per minute)
        self.rate_limit_config = {
            SecurityOperation.THREAT_SCAN: 10,
            SecurityOperation.VULN_SCAN: 5,
            SecurityOperation.CODE_ANALYSIS: 10,
            SecurityOperation.DEPENDENCY_SCAN: 10,
            SecurityOperation.SECRET_SCAN: 20,
        }
        
        # Duplicate prevention window (seconds)
        self.duplicate_window = 300  # 5 minutes
        
        logger.info("[SEC_ORCH] Security orchestrator initialized")

    def _generate_operation_id(self) -> str:
        """Generate unique operation ID."""
        return f"op_{int(time.time() * 1000)}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"

    def _check_duplicate(self, operation_type: SecurityOperation, target: str) -> bool:
        """
        Check if this is a duplicate operation.
        
        Returns True if duplicate detected, False otherwise.
        """
        current_time = time.time()
        lock_key = f"{operation_type.value}:{target}"
        
        # Check if operation is currently running
        if lock_key in self._operation_locks:
            lock_time = self._operation_locks[lock_key]
            if current_time - lock_time < self.duplicate_window:
                logger.warning(f"[SEC_ORCH] Duplicate operation blocked: {lock_key}")
                return True
        
        return False

    def _check_rate_limit(self, operation_type: SecurityOperation) -> bool:
        """
        Check if operation exceeds rate limit.
        
        Returns True if within limit, False if exceeded.
        """
        current_time = time.time()
        limit = self.rate_limit_config.get(operation_type, 20)
        
        if operation_type not in self._rate_limits:
            self._rate_limits[operation_type] = []
        
        # Remove old timestamps (older than 1 minute)
        self._rate_limits[operation_type] = [
            t for t in self._rate_limits[operation_type]
            if current_time - t < 60
        ]
        
        # Check if limit exceeded
        if len(self._rate_limits[operation_type]) >= limit:
            logger.warning(f"[SEC_ORCH] Rate limit exceeded for {operation_type.value}")
            return False
        
        # Record this operation
        self._rate_limits[operation_type].append(current_time)
        return True

    def _log_audit(self, operation_id: str, action: str, actor: str,
                   target: str, result: str, details: Optional[dict] = None):
        """Log operation to audit trail."""
        try:
            self.db.insert_audit_log(
                action=action,
                actor=actor,
                target=target,
                result=result,
                details=details or {},
            )
        except Exception as e:
            logger.error(f"[SEC_ORCH] Failed to log audit: {e}")

    def execute_operation(
        self,
        operation_type: SecurityOperation,
        target: str,
        request: dict,
        actor: str = "system",
        handler: Optional[callable] = None,
    ) -> dict:
        """
        Execute a security operation with duplicate prevention and rate limiting.
        
        Args:
            operation_type: Type of security operation
            target: Target system/path/resource
            request: Operation parameters
            actor: Who initiated the operation
            handler: Function to execute the operation
            
        Returns:
            Operation result dict with operation_id, status, and results
        """
        operation_id = self._generate_operation_id()
        start_time = time.time()
        
        # Check for duplicate
        if self._check_duplicate(operation_type, target):
            return {
                "success": False,
                "error": "Duplicate operation detected. Please wait before retrying.",
                "operation_id": operation_id,
            }
        
        # Check rate limit
        if not self._check_rate_limit(operation_type):
            return {
                "success": False,
                "error": "Rate limit exceeded. Please try again later.",
                "operation_id": operation_id,
            }
        
        # Create operation record
        record = SecurityOperationRecord(
            operation_id=operation_id,
            operation_type=operation_type,
            timestamp=start_time,
            target=target,
            status=OperationStatus.RUNNING,
            request=request,
            actor=actor,
        )
        
        # Lock this operation
        lock_key = f"{operation_type.value}:{target}"
        self._operation_locks[lock_key] = start_time
        self._active_operations[operation_id] = record
        
        logger.info(f"[SEC_ORCH] Starting operation {operation_id}: {operation_type.value} on {target}")
        
        # Log audit
        self._log_audit(
            operation_id=operation_id,
            action=f"start_{operation_type.value}",
            actor=actor,
            target=target,
            result="started",
            details={"request": request},
        )
        
        try:
            # Execute the operation
            if handler:
                result = handler(**request)
            else:
                result = {"message": "No handler provided"}
            
            # Update record
            record.status = OperationStatus.COMPLETED
            record.result = result
            record.duration = time.time() - start_time
            
            # Log success
            self._log_audit(
                operation_id=operation_id,
                action=f"complete_{operation_type.value}",
                actor=actor,
                target=target,
                result="success",
                details={"duration": record.duration},
            )
            
            logger.info(f"[SEC_ORCH] Operation {operation_id} completed in {record.duration:.2f}s")
            
            return {
                "success": True,
                "operation_id": operation_id,
                "result": result,
                "duration": record.duration,
            }
            
        except Exception as e:
            # Update record with error
            record.status = OperationStatus.FAILED
            record.error = str(e)
            record.duration = time.time() - start_time
            
            # Log failure
            self._log_audit(
                operation_id=operation_id,
                action=f"fail_{operation_type.value}",
                actor=actor,
                target=target,
                result="failed",
                details={"error": str(e)},
            )
            
            logger.error(f"[SEC_ORCH] Operation {operation_id} failed: {e}")
            
            return {
                "success": False,
                "operation_id": operation_id,
                "error": str(e),
                "duration": record.duration,
            }
            
        finally:
            # Move to history and clean up
            self._operation_history.append(record)
            if operation_id in self._active_operations:
                del self._active_operations[operation_id]
            
            # Keep only last 1000 operations in history
            if len(self._operation_history) > 1000:
                self._operation_history = self._operation_history[-1000:]

    def get_operation_status(self, operation_id: str) -> Optional[dict]:
        """Get status of an operation."""
        # Check active operations
        if operation_id in self._active_operations:
            record = self._active_operations[operation_id]
            return {
                "operation_id": record.operation_id,
                "operation_type": record.operation_type.value,
                "status": record.status.value,
                "timestamp": record.timestamp,
                "target": record.target,
                "actor": record.actor,
            }
        
        # Check history
        for record in reversed(self._operation_history):
            if record.operation_id == operation_id:
                return {
                    "operation_id": record.operation_id,
                    "operation_type": record.operation_type.value,
                    "status": record.status.value,
                    "timestamp": record.timestamp,
                    "target": record.target,
                    "actor": record.actor,
                    "duration": record.duration,
                    "result": record.result,
                    "error": record.error,
                }
        
        return None

    def get_active_operations(self) -> list[dict]:
        """Get list of currently active operations."""
        return [
            {
                "operation_id": record.operation_id,
                "operation_type": record.operation_type.value,
                "status": record.status.value,
                "timestamp": record.timestamp,
                "target": record.target,
                "actor": record.actor,
            }
            for record in self._active_operations.values()
        ]

    def get_operation_history(self, limit: int = 50) -> list[dict]:
        """Get recent operation history."""
        return [
            {
                "operation_id": record.operation_id,
                "operation_type": record.operation_type.value,
                "status": record.status.value,
                "timestamp": record.timestamp,
                "target": record.target,
                "actor": record.actor,
                "duration": record.duration,
            }
            for record in self._operation_history[-limit:]
        ][::-1]  # Reverse to show most recent first

    def get_orchestrator_stats(self) -> dict:
        """Get orchestrator statistics."""
        return {
            "active_operations": len(self._active_operations),
            "total_operations": len(self._operation_history),
            "operation_types": {
                op_type.value: sum(1 for r in self._operation_history if r.operation_type == op_type)
                for op_type in SecurityOperation
            },
            "rate_limits": {
                op_type.value: len(timestamps)
                for op_type, timestamps in self._rate_limits.items()
            },
        }

    def clear_operation_lock(self, operation_type: SecurityOperation, target: str):
        """Manually clear an operation lock (for recovery)."""
        lock_key = f"{operation_type.value}:{target}"
        if lock_key in self._operation_locks:
            del self._operation_locks[lock_key]
            logger.info(f"[SEC_ORCH] Cleared lock for {lock_key}")


# Singleton instance
_security_orchestrator: Optional[SecurityOrchestrator] = None


def get_security_orchestrator() -> SecurityOrchestrator:
    """Get or create the security orchestrator singleton."""
    global _security_orchestrator
    if _security_orchestrator is None:
        _security_orchestrator = SecurityOrchestrator()
    return _security_orchestrator
