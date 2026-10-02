"""Workspace Model - AGENTS.md/SOUL.md/IDENTITY.md/USER.md pattern.

Ported from OpenClaw. Markdown files define agent personality, memory, and constraints.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceFile:
    name: str
    path: Path
    content: str = ""
    last_modified: str = ""

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> str:
        if self.path.exists():
            self.content = self.path.read_text(encoding="utf-8")
            return self.content
        return ""

    def save(self, content: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(content, encoding="utf-8")
        self.content = content


class WorkspaceModel:
    def __init__(self, workspace_dir: str | Path | None = None):
        self._dir = Path(workspace_dir) if workspace_dir else Path.home() / ".jarvis" / "workspace"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._files: dict[str, WorkspaceFile] = {}
        self._load_workspace_files()

    def _load_workspace_files(self) -> None:
        definitions = {
            "AGENTS": "AGENTS.md",
            "SOUL": "SOUL.md",
            "IDENTITY": "IDENTITY.md",
            "USER": "USER.md",
            "MEMORY": "MEMORY.md",
            "HEARTBEAT": "HEARTBEAT.md",
        }
        for key, filename in definitions.items():
            self._files[key] = WorkspaceFile(
                name=filename,
                path=self._dir / filename,
            )

    def get_file(self, key: str) -> WorkspaceFile | None:
        return self._files.get(key)

    def get_content(self, key: str) -> str:
        wf = self._files.get(key)
        if wf:
            return wf.load()
        return ""

    def set_content(self, key: str, content: str) -> None:
        wf = self._files.get(key)
        if wf:
            wf.save(content)
        else:
            wf = WorkspaceFile(name=f"{key}.md", path=self._dir / f"{key}.md")
            wf.save(content)
            self._files[key] = wf

    def build_system_context(self) -> str:
        parts = []

        soul = self.get_content("SOUL")
        if soul:
            parts.append(f"## Personality & Values\n{soul}")

        identity = self.get_content("IDENTITY")
        if identity:
            parts.append(f"## Identity\n{identity}")

        user = self.get_content("USER")
        if user:
            parts.append(f"## About the User\n{user}")

        memory = self.get_content("MEMORY")
        if memory:
            parts.append(f"## Persistent Memory\n{memory}")

        agents = self.get_content("AGENTS")
        if agents:
            parts.append(f"## Behavioral Contract\n{agents}")

        return "\n\n".join(parts) if parts else "No workspace context configured."

    @property
    def workspace_dir(self) -> Path:
        return self._dir

    @property
    def files(self) -> dict[str, WorkspaceFile]:
        return dict(self._files)
