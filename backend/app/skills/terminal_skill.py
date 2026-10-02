import subprocess
import shlex
import sys
from pathlib import Path
from typing import Any, Dict

from .skill_base import BaseSkill, SkillTool

try:
    from app.persistent_memory import WORKSPACE_ROOT
except ImportError:
    from persistent_memory import WORKSPACE_ROOT


class TerminalSkill(BaseSkill):
    id = "terminal_controller"
    display_name = "Secure Terminal & Process Commander"
    description = "Execute shell commands, run tests, install packages, and manage processes inside the workspace."
    icon = "command-line"

    def _setup_tools(self):
        self.tools.append(
            SkillTool(
                name="run_command",
                description="Run a shell or PowerShell command inside the project workspace directory and capture its stdout, stderr, and exit code.",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The exact shell command line string to run"},
                        "cwd": {"type": "string", "description": "Working directory relative to project root (default: '.')", "default": "."},
                        "timeout_seconds": {"type": "integer", "description": "Max execution time in seconds (default: 30)", "default": 30},
                    },
                    "required": ["command"],
                },
                handler=self.tool_run_command,
            )
        )

    def get_system_prompt_addon(self) -> str:
        return (
            "You have access to the project terminal via `run_command`:\n"
            "- Operating System: Windows.\n"
            "- Never run destructive system commands (e.g. format, rm -rf /).\n"
            "- Always verify output and exit codes."
        )

    def tool_run_command(self, command: str, cwd: str = ".", timeout_seconds: int = 30) -> Dict[str, Any]:
        work_dir = (WORKSPACE_ROOT / cwd).resolve()
        if not work_dir.exists():
            return {"error": f"Working directory '{cwd}' does not exist"}

        # Block destructive commands
        dangerous = ["format ", "del /f /s /q c:", "rmdir /s /q c:", "mkfs", ":(){ :|:& };:"]
        lower_cmd = command.lower()
        if any(d in lower_cmd for d in dangerous):
            return {"error": "Execution blocked: command deemed potentially destructive"}

        try:
            # On Windows, execute via cmd.exe or powershell
            is_win = sys.platform == "win32"
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=max(1, min(120, timeout_seconds)),
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            return {
                "command": command,
                "exit_code": proc.returncode,
                "stdout": stdout[:4000] + ("\n... [truncated]" if len(stdout) > 4000 else ""),
                "stderr": stderr[:4000] + ("\n... [truncated]" if len(stderr) > 4000 else ""),
                "success": proc.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {"command": command, "error": f"Command timed out after {timeout_seconds} seconds", "exit_code": -1}
        except Exception as e:
            return {"command": command, "error": str(e), "exit_code": -1}
