"""Safe file read/write tools with policy enforcement."""

import os
import logging
from pathlib import Path
from . import BaseTool, ToolSpec, ToolRegistry
from ..security.file_policy import file_policy

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 1_000_000


@ToolRegistry.register("file_read")
class FileReadTool(BaseTool):
    """Read file contents with security policy enforcement."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="file_read",
            description="Read the contents of a file. Blocked for sensitive files (.env, keys, credentials). Max 1MB.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "max_lines": {"type": "integer", "description": "Max lines to read"},
                },
                "required": ["path"]
            },
            category="filesystem",
        )

    async def execute(self, path: str = "", max_lines: int = None, **kwargs) -> dict:
        allowed, reason = file_policy.check_read(path)
        if not allowed:
            return {"error": reason}

        try:
            p = Path(path).resolve()
            if not p.exists():
                return {"error": f"File not found: {path}"}
            if not p.is_file():
                return {"error": f"Not a file: {path}"}
            if p.stat().st_size > MAX_FILE_SIZE:
                return {"error": f"File too large ({p.stat().st_size} bytes, max {MAX_FILE_SIZE})"}

            content = p.read_text(encoding="utf-8", errors="replace")
            if max_lines:
                lines = content.splitlines()[:max_lines]
                content = "\n".join(lines)

            return {
                "content": content,
                "path": str(p),
                "size": p.stat().st_size,
                "lines": content.count("\n") + 1,
            }
        except Exception as e:
            return {"error": str(e)}


@ToolRegistry.register("file_write")
class FileWriteTool(BaseTool):
    """Write content to a file with security policy enforcement."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="file_write",
            description="Write content to a file. Blocked for sensitive files. Creates parent directories if needed.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Content to write"},
                    "append": {"type": "boolean", "description": "Append instead of overwrite", "default": False},
                },
                "required": ["path", "content"]
            },
            category="filesystem",
        )

    async def execute(self, path: str = "", content: str = "", append: bool = False, **kwargs) -> dict:
        allowed, reason = file_policy.check_write(path)
        if not allowed:
            return {"error": reason}

        try:
            p = Path(path).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)

            mode = "a" if append else "w"
            with open(p, mode, encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "path": str(p),
                "bytes_written": len(content.encode("utf-8")),
                "mode": "append" if append else "write",
            }
        except Exception as e:
            return {"error": str(e)}
