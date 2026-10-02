"""
Authentication & Access Control for JARVIS cybersecurity module.

Provides secure authentication and authorization for JARVIS admin functions:
- Password policy enforcement
- Session management
- Role-based access control
- Account lockout protection
- Multi-factor authentication support
"""

import hashlib
import hmac
import logging
import os
import re
import secrets
import time
from typing import Optional
from dataclasses import dataclass, field

from .security_db import get_security_db

logger = logging.getLogger(__name__)


@dataclass
class PasswordPolicy:
    """Password policy configuration."""
    min_length: int = 12
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    max_age_days: int = 90
    history_count: int = 5
    lockout_threshold: int = 5
    lockout_duration_minutes: int = 30


@dataclass
class UserSession:
    """Represents an active user session."""
    session_id: str
    username: str
    role: str
    created_at: float
    last_activity: float
    expires_at: float
    ip_address: str = ""
    user_agent: str = ""
    is_active: bool = True


class AuthenticationManager:
    """Manages authentication and access control."""

    def __init__(self):
        self.db = get_security_db()
        self.logger = logging.getLogger(__name__)
        self.sessions: dict[str, UserSession] = {}
        self.failed_attempts: dict[str, list] = {}
        self.password_policy = PasswordPolicy()
        self.session_timeout = 3600
        self._users: dict[str, dict] = {}

    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash password with salt using SHA-256."""
        if salt is None:
            salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations=100000
        )
        return hashed.hex(), salt

    def validate_password_policy(self, password: str) -> dict:
        """Validate password against security policy."""
        issues = []
        policy = self.password_policy

        if len(password) < policy.min_length:
            issues.append(f"Password must be at least {policy.min_length} characters")

        if policy.require_uppercase and not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")

        if policy.require_lowercase and not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")

        if policy.require_digit and not re.search(r'\d', password):
            issues.append("Password must contain at least one digit")

        if policy.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password must contain at least one special character")

        common_passwords = [
            "password", "123456", "qwerty", "admin", "letmein",
            "welcome", "monkey", "dragon", "master", "login"
        ]
        if password.lower() in common_passwords:
            issues.append("Password is too common")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "strength": self._calculate_password_strength(password),
        }

    def _calculate_password_strength(self, password: str) -> str:
        """Calculate password strength score."""
        score = 0

        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1

        if re.search(r'[A-Z]', password):
            score += 1
        if re.search(r'[a-z]', password):
            score += 1
        if re.search(r'\d', password):
            score += 1
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 2

        if len(set(password)) > len(password) * 0.7:
            score += 1

        if score >= 7:
            return "strong"
        elif score >= 4:
            return "medium"
        else:
            return "weak"

    def register_user(self, username: str, password: str, role: str = "user") -> dict:
        """Register a new user."""
        if username in self._users:
            return {"success": False, "error": "Username already exists"}

        policy_check = self.validate_password_policy(password)
        if not policy_check["valid"]:
            return {
                "success": False,
                "error": "Password does not meet policy requirements",
                "issues": policy_check["issues"],
            }

        hashed, salt = self.hash_password(password)
        self._users[username] = {
            "username": username,
            "password_hash": hashed,
            "salt": salt,
            "role": role,
            "created_at": time.time(),
            "last_login": None,
            "failed_attempts": 0,
            "locked": False,
            "locked_until": 0,
        }

        self.db.insert_audit_log(
            action="user_registered",
            actor=username,
            target="system",
            result="success",
            details={"role": role}
        )

        return {"success": True, "username": username, "role": role}

    def authenticate(self, username: str, password: str,
                      ip_address: str = "", user_agent: str = "") -> dict:
        """Authenticate a user."""
        if username not in self._users:
            self.db.insert_audit_log(
                action="login_failed",
                actor=username,
                target="system",
                result="failure",
                details={"reason": "user_not_found", "ip": ip_address}
            )
            return {"success": False, "error": "Invalid credentials"}

        user = self._users[username]

        if user.get("locked") and user.get("locked_until", 0) > time.time():
            return {"success": False, "error": "Account is locked. Try again later."}

        if user.get("locked"):
            user["locked"] = False
            user["failed_attempts"] = 0

        hashed, _ = self.hash_password(password, user["salt"])
        if not hmac.compare_digest(hashed, user["password_hash"]):
            user["failed_attempts"] = user.get("failed_attempts", 0) + 1

            if user["failed_attempts"] >= self.password_policy.lockout_threshold:
                user["locked"] = True
                user["locked_until"] = time.time() + (self.password_policy.lockout_duration_minutes * 60)
                self.logger.warning(f"[AUTH] Account locked due to failed attempts: {username}")

            self.db.insert_audit_log(
                action="login_failed",
                actor=username,
                target="system",
                result="failure",
                details={"reason": "invalid_password", "ip": ip_address}
            )

            return {"success": False, "error": "Invalid credentials"}

        session_id = secrets.token_urlsafe(32)
        now = time.time()

        session = UserSession(
            session_id=session_id,
            username=username,
            role=user["role"],
            created_at=now,
            last_activity=now,
            expires_at=now + self.session_timeout,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.sessions[session_id] = session

        user["last_login"] = now
        user["failed_attempts"] = 0

        self.db.insert_audit_log(
            action="login_success",
            actor=username,
            target="system",
            result="success",
            details={"ip": ip_address, "session_id": session_id[:8]}
        )

        return {
            "success": True,
            "session_id": session_id,
            "username": username,
            "role": user["role"],
            "expires_in": self.session_timeout,
        }

    def validate_session(self, session_id: str) -> dict:
        """Validate an active session."""
        if session_id not in self.sessions:
            return {"valid": False, "error": "Session not found"}

        session = self.sessions[session_id]

        if not session.is_active:
            return {"valid": False, "error": "Session expired"}

        if time.time() > session.expires_at:
            session.is_active = False
            return {"valid": False, "error": "Session expired"}

        session.last_activity = time.time()

        return {
            "valid": True,
            "username": session.username,
            "role": session.role,
        }

    def revoke_session(self, session_id: str) -> dict:
        """Revoke a user session."""
        if session_id in self.sessions:
            self.sessions[session_id].is_active = False
            del self.sessions[session_id]

            self.db.insert_audit_log(
                action="session_revoked",
                actor="system",
                target=session_id[:8],
                result="success",
            )

            return {"success": True}

        return {"success": False, "error": "Session not found"}

    def check_permission(self, session_id: str, required_role: str) -> bool:
        """Check if session has required role/permission."""
        validation = self.validate_session(session_id)
        if not validation.get("valid"):
            return False

        role_hierarchy = {"admin": 3, "operator": 2, "user": 1, "viewer": 0}
        user_level = role_hierarchy.get(validation["role"], 0)
        required_level = role_hierarchy.get(required_role, 0)

        return user_level >= required_level

    def get_active_sessions(self) -> list[dict]:
        """Get all active sessions."""
        active = []
        now = time.time()

        for session_id, session in self.sessions.items():
            if session.is_active and now < session.expires_at:
                active.append({
                    "session_id": session_id[:8] + "...",
                    "username": session.username,
                    "role": session.role,
                    "created_at": session.created_at,
                    "last_activity": session.last_activity,
                    "ip_address": session.ip_address,
                })

        return active

    def get_auth_stats(self) -> dict:
        """Get authentication statistics."""
        total_users = len(self._users)
        locked_users = sum(1 for u in self._users.values() if u.get("locked"))
        active_sessions = len([s for s in self.sessions.values() if s.is_active])

        return {
            "total_users": total_users,
            "locked_accounts": locked_users,
            "active_sessions": active_sessions,
            "session_timeout": self.session_timeout,
        }


_auth_manager: Optional[AuthenticationManager] = None


def get_auth_manager() -> AuthenticationManager:
    """Get singleton instance of AuthenticationManager."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthenticationManager()
    return _auth_manager
