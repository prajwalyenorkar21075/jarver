"""File access policy — blocks sensitive file reads."""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_SENSITIVE_PATTERNS = [
    ".env", ".env.local", ".env.production",
    "id_rsa", "id_ed25519", "id_ecdsa",
    ".pem", ".key", ".p12", ".pfx",
    "credentials", "secrets",
    ".aws/credentials",
    "shadow", "passwd",
    "known_hosts", "authorized_keys",
    ".git/config",
    "wallet.dat",
]

_SENSITIVE_EXTENSIONS = {
    ".pem", ".key", ".p12", ".pfx", ".jks",
    ".keystore", ".keychain", ".kdbx",
}


class FilePolicy:
    """Determines whether a file path is safe to read/write."""

    def __init__(self, extra_blocked: list[str] | None = None):
        self._blocked = list(_SENSITIVE_PATTERNS)
        if extra_blocked:
            self._blocked.extend(extra_blocked)

    def is_sensitive(self, path: str | Path) -> bool:
        path_str = str(path).lower().replace("\\", "/")
        filename = os.path.basename(path_str)

        for pattern in self._blocked:
            if pattern in path_str:
                return True

        _, ext = os.path.splitext(filename)
        if ext.lower() in _SENSITIVE_EXTENSIONS:
            return True

        return False

    def check_read(self, path: str | Path) -> tuple[bool, str]:
        if self.is_sensitive(path):
            return False, f"Access denied: sensitive file '{os.path.basename(str(path))}'"
        return True, "OK"

    def check_write(self, path: str | Path) -> tuple[bool, str]:
        if self.is_sensitive(path):
            return False, f"Write denied: would overwrite sensitive file '{os.path.basename(str(path))}'"
        return True, "OK"


file_policy = FilePolicy()
