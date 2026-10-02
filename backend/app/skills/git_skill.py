import subprocess
from pathlib import Path
from typing import Any, Dict

from .skill_base import BaseSkill, SkillTool

try:
    from app.persistent_memory import WORKSPACE_ROOT
except ImportError:
    from persistent_memory import WORKSPACE_ROOT


def _run_git(args: list[str]) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return -1, "", "git executable not found"
    except Exception as e:
        return -1, "", str(e)


class GitSkill(BaseSkill):
    id = "git_manager"
    display_name = "Git Version Control Manager"
    description = "Inspect git repository status, diffs, branches, and commit logs."
    icon = "code-bracket-square"

    def _setup_tools(self):
        self.tools.append(
            SkillTool(
                name="git_status",
                description="Get current git branch, tracked/untracked changes, and staging state.",
                parameters={"type": "object", "properties": {}},
                handler=self.tool_git_status,
            )
        )
        self.tools.append(
            SkillTool(
                name="git_diff",
                description="View unified git diff of all unstaged/staged changes, or for a specific file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Optional specific file to diff"},
                        "cached": {"type": "boolean", "description": "Whether to view staged changes", "default": False},
                    },
                },
                handler=self.tool_git_diff,
            )
        )
        self.tools.append(
            SkillTool(
                name="git_log",
                description="View recent git commit history.",
                parameters={
                    "type": "object",
                    "properties": {
                        "max_count": {"type": "integer", "description": "Number of commits to return (default: 10)", "default": 10},
                    },
                },
                handler=self.tool_git_log,
            )
        )

    def tool_git_status(self) -> Dict[str, Any]:
        code, out, err = _run_git(["status", "--porcelain", "-b"])
        if code != 0:
            return {"is_git_repo": False, "notice": "Directory is not a git repository or git is uninitialized."}
        lines = out.splitlines()
        branch_line = lines[0] if lines else "## unknown"
        changes = lines[1:] if len(lines) > 1 else []
        return {
            "is_git_repo": True,
            "branch": branch_line.replace("## ", ""),
            "changes_count": len(changes),
            "changes": changes,
        }

    def tool_git_diff(self, path: str = "", cached: bool = False) -> Dict[str, Any]:
        args = ["diff"]
        if cached:
            args.append("--cached")
        if path:
            args.append(path)
        code, out, err = _run_git(args)
        if code != 0:
            return {"error": err or "Failed to compute git diff"}
        return {"diff": out[:5000] if out else "No changes detected."}

    def tool_git_log(self, max_count: int = 10) -> Dict[str, Any]:
        code, out, err = _run_git(["log", f"-n{max_count}", "--oneline", "--decorate"])
        if code != 0:
            return {"error": err or "Failed to get git log"}
        return {"commits": out.splitlines()}
