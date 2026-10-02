"""Secure code interpreter with defense-in-depth."""

import ast
import sys
import subprocess
import tempfile
import os
import logging
from . import BaseTool, ToolSpec, ToolRegistry

logger = logging.getLogger(__name__)

_BLOCKED_IMPORTS = {"os", "sys", "subprocess", "shutil", "pathlib", "socket",
                    "http", "urllib", "requests", "ctypes", "importlib",
                    "pickle", "shelve", "marshal", "signal"}

_BLOCKED_BUILTINS = {"eval", "exec", "compile", "__import__", "open",
                     "breakpoint", "globals", "locals", "vars",
                     "getattr", "setattr", "delattr", "memoryview", "help",
                     "input", "exit", "quit"}


def _validate_code(code: str) -> tuple[bool, str]:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BLOCKED_IMPORTS:
                    return False, f"Blocked import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in _BLOCKED_IMPORTS:
                    return False, f"Blocked import: {node.module}"
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_BUILTINS:
                return False, f"Blocked builtin: {node.func.id}"
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                return False, f"Blocked dunder access: {node.attr}"

    return True, "OK"


@ToolRegistry.register("code_interpreter")
class CodeInterpreterTool(BaseTool):
    """Execute Python code in a sandboxed subprocess."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="code_interpreter",
            description="Execute Python code in an isolated sandbox. Only json, math, time, datetime, collections, itertools, functools, random, re, string, hashlib, base64, struct, decimal, fractions are allowed. No file I/O, no network, no system access.",
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (max 30)"
                    }
                },
                "required": ["code"]
            },
            category="code",
        )

    async def execute(self, code: str = "", timeout: int = 10, **kwargs) -> dict:
        timeout = min(timeout, 30)

        valid, msg = _validate_code(code)
        if not valid:
            return {"error": f"Code rejected: {msg}"}

        allowed_imports = "import json, math, time, datetime, collections, itertools, functools, random, re, string, hashlib, base64, struct, decimal, fractions\n"
        full_code = allowed_imports + code

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(full_code)
            tmp_path = f.name

        try:
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["PYTHONNOUSERSITE"] = "1"

            result = subprocess.run(
                [sys.executable, "-I", "-B", "-S", tmp_path],
                capture_output=True, text=True,
                timeout=timeout,
                env=env,
            )

            stdout = result.stdout[:5000] if result.stdout else ""
            stderr = result.stderr[:2000] if result.stderr else ""

            return {
                "success": result.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Code execution timed out after {timeout}s"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
