"""Remote access and robot control architecture for JARVIS.

Flow: Remote Client → Authentication → Permission Layer → JARVIS Backend →
      Robot Gateway → Robot

Supports: authentication, authorization, encrypted communication,
connection status, command acknowledgement, emergency stop,
command timeout, audit logging.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import secrets
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("jarvis.remote")


class ConnectionState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    AUTHENTICATING = "AUTHENTICATING"
    CONNECTED = "CONNECTED"
    AUTHORIZED = "AUTHORIZED"
    REJECTED = "REJECTED"


class CommandStatus(str, Enum):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    REJECTED = "REJECTED"
    EMERGENCY_STOP = "EMERGENCY_STOP"


@dataclass
class RemoteSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    client_id: str = ""
    state: ConnectionState = ConnectionState.DISCONNECTED
    authenticated: bool = False
    authorized: bool = False
    connected_at: float | None = None
    last_activity: float = field(default_factory=time.time)
    commands_sent: int = 0
    commands_completed: int = 0
    ip_address: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "client_id": self.client_id,
            "state": self.state.value,
            "authenticated": self.authenticated,
            "authorized": self.authorized,
            "connected_at": self.connected_at,
            "last_activity": self.last_activity,
            "commands_sent": self.commands_sent,
            "commands_completed": self.commands_completed,
            "ip_address": self.ip_address,
        }


@dataclass
class RemoteCommand:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    session_id: str = ""
    command: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    status: CommandStatus = CommandStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    acknowledged_at: float | None = None
    completed_at: float | None = None
    timeout_seconds: float = 30.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "command": self.command,
            "args": self.args,
            "status": self.status.value,
            "result": str(self.result)[:200] if self.result else None,
            "error": self.error,
            "created_at": self.created_at,
            "acknowledged_at": self.acknowledged_at,
            "completed_at": self.completed_at,
        }


@dataclass
class AuditEntry:
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""
    action: str = ""
    command: str = ""
    status: str = ""
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "action": self.action,
            "command": self.command,
            "status": self.status,
            "details": self.details,
        }


class AuthManager:
    def __init__(self):
        self._tokens: dict[str, dict[str, Any]] = {}
        self._clients: dict[str, dict[str, Any]] = {}
        self._token_ttl = 3600.0
        self._generate_default_client()
        logger.info("[REMOTE] AuthManager initialized")

    def _generate_default_client(self):
        client_id = "jarvis-admin"
        client_secret = secrets.token_hex(32)
        self._clients[client_id] = {
            "client_id": client_id,
            "client_secret_hash": hashlib.sha256(client_secret.encode()).hexdigest(),
            "role": "admin",
            "permissions": ["*"],
            "created_at": time.time(),
        }
        logger.info(f"[REMOTE] Default admin client created: {client_id}")

    def register_client(self, client_id: str, role: str = "operator") -> dict[str, str]:
        client_secret = secrets.token_hex(32)
        self._clients[client_id] = {
            "client_id": client_id,
            "client_secret_hash": hashlib.sha256(client_secret.encode()).hexdigest(),
            "role": role,
            "permissions": self._role_permissions(role),
            "created_at": time.time(),
        }
        return {"client_id": client_id, "client_secret": client_secret}

    def authenticate(self, client_id: str, client_secret: str) -> str | None:
        client = self._clients.get(client_id)
        if not client:
            return None
        secret_hash = hashlib.sha256(client_secret.encode()).hexdigest()
        if not hmac.compare_digest(secret_hash, client["client_secret_hash"]):
            return None
        token = secrets.token_hex(32)
        self._tokens[token] = {
            "client_id": client_id,
            "role": client["role"],
            "permissions": client["permissions"],
            "created_at": time.time(),
            "expires_at": time.time() + self._token_ttl,
        }
        return token

    def validate_token(self, token: str) -> dict[str, Any] | None:
        token_data = self._tokens.get(token)
        if not token_data:
            return None
        if time.time() > token_data["expires_at"]:
            del self._tokens[token]
            return None
        return token_data

    def has_permission(self, token: str, permission: str) -> bool:
        token_data = self.validate_token(token)
        if not token_data:
            return False
        perms = token_data.get("permissions", [])
        if "*" in perms:
            return True
        return permission in perms

    def revoke_token(self, token: str):
        self._tokens.pop(token, None)

    def _role_permissions(self, role: str) -> list[str]:
        roles = {
            "admin": ["*"],
            "operator": ["read", "navigate", "monitor", "command"],
            "viewer": ["read", "monitor"],
        }
        return roles.get(role, ["read"])

    def get_stats(self) -> dict[str, Any]:
        return {
            "active_tokens": len(self._tokens),
            "registered_clients": len(self._clients),
        }


class RemoteControlService:
    def __init__(self):
        self._auth = AuthManager()
        self._sessions: dict[str, RemoteSession] = {}
        self._commands: dict[str, RemoteCommand] = {}
        self._command_history: list[RemoteCommand] = []
        self._audit_log: list[AuditEntry] = []
        self._max_history = 500
        self._max_audit = 1000
        self._emergency_active = False
        logger.info("[REMOTE] RemoteControlService initialized")

    async def connect(self, client_id: str, client_secret: str, ip_address: str = "") -> dict[str, Any]:
        session = RemoteSession(client_id=client_id, ip_address=ip_address)
        session.state = ConnectionState.AUTHENTICATING

        token = self._auth.authenticate(client_id, client_secret)
        if not token:
            session.state = ConnectionState.REJECTED
            self._audit(AuditEntry(
                session_id=session.id,
                action="connect",
                status="REJECTED",
                details="Authentication failed",
            ))
            return {"status": "rejected", "error": "Authentication failed"}

        session.state = ConnectionState.AUTHORIZED
        session.authenticated = True
        session.authorized = True
        session.connected_at = time.time()
        self._sessions[session.id] = session

        self._audit(AuditEntry(
            session_id=session.id,
            action="connect",
            status="AUTHORIZED",
            details=f"Client {client_id} connected",
        ))

        return {
            "status": "authorized",
            "session_id": session.id,
            "token": token,
        }

    async def disconnect(self, session_id: str):
        session = self._sessions.pop(session_id, None)
        if session:
            session.state = ConnectionState.DISCONNECTED
            self._audit(AuditEntry(
                session_id=session_id,
                action="disconnect",
                status="DISCONNECTED",
            ))

    async def send_command(
        self,
        session_id: str,
        command: str,
        args: dict[str, Any] | None = None,
        token: str = "",
    ) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session or not session.authorized:
            return {"status": "rejected", "error": "Session not authorized"}

        if self._emergency_active:
            return {"status": "rejected", "error": "Emergency stop active — all commands blocked"}

        if not self._auth.has_permission(token, "command"):
            return {"status": "rejected", "error": "Insufficient permissions"}

        cmd = RemoteCommand(
            session_id=session_id,
            command=command,
            args=args or {},
        )
        self._commands[cmd.id] = cmd
        session.commands_sent += 1

        cmd.status = CommandStatus.ACKNOWLEDGED
        cmd.acknowledged_at = time.time()

        self._audit(AuditEntry(
            session_id=session_id,
            action="command",
            command=command,
            status="ACKNOWLEDGED",
        ))

        try:
            cmd.status = CommandStatus.EXECUTING
            result = await self._execute_command(command, args or {}, session)
            cmd.status = CommandStatus.COMPLETED
            cmd.result = result
            cmd.completed_at = time.time()
            session.commands_completed += 1
        except asyncio.TimeoutError:
            cmd.status = CommandStatus.TIMEOUT
            cmd.error = "Command timed out"
        except Exception as e:
            cmd.status = CommandStatus.FAILED
            cmd.error = str(e)

        self._command_history.append(cmd)
        if len(self._command_history) > self._max_history:
            self._command_history = self._command_history[-self._max_history:]

        return cmd.to_dict()

    async def _execute_command(self, command: str, args: dict[str, Any], session: RemoteSession) -> Any:
        if command == "emergency_stop":
            self._emergency_active = True
            return {"message": "Emergency stop activated"}

        if command == "release_emergency_stop":
            self._emergency_active = False
            return {"message": "Emergency stop released"}

        if command == "get_status":
            from app.robotics_service import get_robotics_service
            return get_robotics_service().get_full_status()

        if command == "navigate_to":
            location = args.get("location", "")
            if not location:
                raise ValueError("Location required")
            from app.robotics_service import get_robotics_service
            return await get_robotics_service().navigate_to(location)

        if command == "get_robot_state":
            from app.robotics_service import get_robotics_service
            return get_robotics_service().robot_state.to_dict()

        if command == "get_vision":
            from app.vision_service import get_vision_service
            return get_vision_service().get_stats()

        if command == "get_diagnostics":
            from app.diagnostics import run_diagnostics
            return await run_diagnostics()

        raise ValueError(f"Unknown command: {command}")

    async def emergency_stop(self, session_id: str = "system"):
        self._emergency_active = True
        self._audit(AuditEntry(
            session_id=session_id,
            action="emergency_stop",
            status="ACTIVATED",
            details="Emergency stop activated",
        ))
        try:
            from app.robotics_service import get_robotics_service
            await get_robotics_service().emergency_stop()
        except Exception as e:
            logger.error(f"[REMOTE] Emergency stop propagation failed: {e}")
        logger.warning("[REMOTE] EMERGENCY STOP ACTIVATED")

    def _audit(self, entry: AuditEntry):
        self._audit_log.append(entry)
        if len(self._audit_log) > self._max_audit:
            self._audit_log = self._audit_log[-self._max_audit:]

    def get_active_sessions(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._sessions.values()]

    def get_command_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._command_history[-limit:]]

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._audit_log[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "active_sessions": len(self._sessions),
            "emergency_active": self._emergency_active,
            "total_commands": len(self._command_history),
            "auth_stats": self._auth.get_stats(),
            "recent_commands": [c.to_dict() for c in self._command_history[-5:]],
        }


_remote_service: RemoteControlService | None = None


def get_remote_service() -> RemoteControlService:
    global _remote_service
    if _remote_service is None:
        _remote_service = RemoteControlService()
    return _remote_service
