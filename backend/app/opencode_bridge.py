"""OpenCode bridge — connects JARVIS to the opencode-ai coding agent binary.

When opencode is installed (`npm i -g opencode-ai`), JARVIS delegates autonomous
coding tasks to opencode's agentic loop with safe file/bash permissions.
Falls back to the built-in CodingEngine when opencode is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger("jarvis.opencode")

_LISTENING_RE = re.compile(r"listening on\s+(https?://\S+)", re.IGNORECASE)

# Tool names opencode uses for file mutations — used to detect real edits.
EDIT_TOOLS = {"write", "edit", "patch", "apply_patch", "str_replace", "multiedit", "create", "notebookedit"}

EventCallback = Callable[[str, Dict[str, Any]], None]


def is_opencode_available() -> bool:
    return shutil.which("opencode") is not None


def _extract_text(parts: List[dict]) -> str:
    return "".join(
        p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"
    ).strip()


class OpenCodeBridge:
    """Manages a headless opencode server and drives coding sessions."""

    def __init__(self, workspace: str = ""):
        self._workspace = workspace or os.getcwd()
        self._proc: Optional[subprocess.Popen] = None
        self._base: str = ""
        self._config_dir: Optional[str] = None
        self._opencode_bin = shutil.which("opencode") or "opencode"

    def _build_config(self) -> dict:
        """Permission policy: allow edits + bash for autonomous coding."""
        cfg: dict = {
            "$schema": "https://opencode.ai/config.json",
            "permission": {"edit": "allow", "bash": "allow", "webfetch": "allow"},
        }
        api_key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        if api_key:
            options: dict = {"apiKey": api_key}
            # Route opencode through the same custom OpenAI-compatible endpoint
            # the rest of JARVIS uses, otherwise exotic model IDs 404 upstream.
            responses_url = os.getenv("OPENAI_RESPONSES_API_URL", "")
            if responses_url and "api.openai.com" not in responses_url:
                from urllib.parse import urlparse
                parsed = urlparse(responses_url)
                path = parsed.path
                for suffix in ("/responses", "/chat/completions", "/completions"):
                    if path.endswith(suffix):
                        path = path[: -len(suffix)]
                        break
                if path.endswith("/v1"):
                    path = path[:-3]
                options["baseURL"] = f"{parsed.scheme}://{parsed.netloc}{path.rstrip('/')}/v1"
            cfg["provider"] = {
                "openai": {
                    "npm": "@ai-sdk/openai",
                    "name": "OpenAI",
                    "options": options,
                    "models": {model: {"name": model}},
                }
            }
        return cfg

    def _ensure_server(self) -> str:
        if self._base and self._proc and self._proc.poll() is None:
            return self._base

        if not is_opencode_available():
            raise RuntimeError(
                "opencode binary not found. Install with: npm i -g opencode-ai"
            )

        self._config_dir = tempfile.mkdtemp(prefix="jarvis-opencode-")
        config_path = Path(self._config_dir) / "opencode.json"
        config_path.write_text(json.dumps(self._build_config(), indent=2), encoding="utf-8")

        env = dict(os.environ)
        env["OPENCODE_CONFIG"] = str(config_path)

        self._proc = subprocess.Popen(
            [self._opencode_bin, "serve", "--port", "0", "--hostname", "127.0.0.1"],
            cwd=self._workspace,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        deadline = time.monotonic() + 60
        base = ""
        assert self._proc.stdout is not None
        while time.monotonic() < deadline:
            line = self._proc.stdout.readline()
            if not line:
                if self._proc.poll() is not None:
                    raise RuntimeError("opencode server exited during startup")
                continue
            m = _LISTENING_RE.search(line)
            if m:
                base = m.group(1).rstrip("/")
                break

        if not base:
            self.close()
            raise RuntimeError("opencode server did not report a listening URL")

        self._base = base
        logger.info(f"OpenCode server started at {base}")
        return base

    def close(self) -> None:
        if self._base:
            try:
                with httpx.Client(base_url=self._base, timeout=10) as c:
                    c.post("/global/dispose")
            except Exception:
                pass
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
        self._base = ""
        if self._config_dir:
            shutil.rmtree(self._config_dir, ignore_errors=True)
            self._config_dir = None

    async def execute_task(
        self,
        prompt: str,
        event_callback: Optional[EventCallback] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Run an autonomous coding task via opencode with error-retry loop."""
        def emit(event_type: str, data: Dict[str, Any]) -> None:
            if event_callback:
                event_callback(event_type, data)

        emit("agent_start", {"engine": "opencode", "prompt": prompt[:200]})

        try:
            self._ensure_server()
        except RuntimeError as exc:
            return {"status": "error", "reply": str(exc), "engine": "opencode"}

        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        model_spec = {"providerID": "openai", "modelID": model}

        all_tool_results: List[Dict[str, Any]] = []
        collected_diffs: List[Dict[str, str]] = []
        executed_tools: List[Dict[str, Any]] = []
        final_reply = ""
        retry_count = 0

        current_prompt = prompt

        while retry_count <= max_retries:
            if retry_count > 0:
                emit("retry", {"attempt": retry_count, "max_retries": max_retries})

            try:
                async with httpx.AsyncClient(base_url=self._base, timeout=600) as client:
                    ses = await client.post("/session", json={"title": current_prompt[:80]})
                    ses.raise_for_status()
                    session_id = ses.json()["id"]

                    emit("status", {"message": "processing", "session_id": session_id})

                    body = {
                        "agent": "build",
                        "model": model_spec,
                        "parts": [{"type": "text", "text": current_prompt}],
                    }

                    resp = await client.post(f"/session/{session_id}/message", json=body)
                    resp.raise_for_status()
                    data = resp.json()

                    turn_parts = list(data.get("parts", []))
                    try:
                        msgs_resp = await client.get(f"/session/{session_id}/message")
                        msgs = msgs_resp.json()
                        if isinstance(msgs, list):
                            turn_parts = [
                                part
                                for mm in msgs
                                if isinstance(mm, dict)
                                for part in mm.get("parts", [])
                            ]
                    except Exception:
                        pass

                    for part in turn_parts:
                        if not isinstance(part, dict):
                            continue
                        ptype = part.get("type", "")

                        if ptype == "tool":
                            tool_name = part.get("tool", part.get("name", "unknown"))
                            state = part.get("state", {}) if isinstance(part.get("state"), dict) else {}
                            status = state.get("status", "")
                            output = state.get("output") or state.get("title", "")

                            emit("tool_start", {"tool": tool_name, "args": state.get("input", {})})

                            tool_result = {
                                "tool": tool_name,
                                "success": status == "completed",
                                "output": str(output),
                            }
                            all_tool_results.append(tool_result)
                            executed_tools.append({"name": tool_name, "arguments": state.get("input", {})})

                            emit("tool_result", {"tool": tool_name, "result": tool_result})

                            if tool_name in ("bash", "run_command", "shell"):
                                metadata = state.get("metadata") if isinstance(state.get("metadata"), dict) else {}
                                emit("terminal_output", {
                                    "cmd": state.get("input", {}).get("command", tool_name),
                                    "stdout": str(output),
                                    "stderr": state.get("error", ""),
                                    "exit_code": metadata.get("exit", metadata.get("exit_code", 0 if status == "completed" else -1)),
                                })

                            # Record real file mutations as diffs so the result is
                            # backed by evidence instead of a bare "completed" flag.
                            if str(tool_name).lower() in EDIT_TOOLS and status == "completed":
                                tool_input = state.get("input") if isinstance(state.get("input"), dict) else {}
                                diff_entry = {
                                    "path": str(tool_input.get("filePath") or tool_input.get("path") or tool_input.get("filename") or ""),
                                    "diff": str(output)[:4000],
                                }
                                collected_diffs.append(diff_entry)
                                emit("file_changed", diff_entry)

                            if status == "error":
                                emit("error", {
                                    "tool": tool_name,
                                    "message": str(output),
                                    "severity": "error",
                                })

                        elif ptype == "patch":
                            for f in part.get("files", []) or []:
                                collected_diffs.append({"path": str(f), "diff": ""})

                        elif ptype == "text" and part.get("text"):
                            emit("token_delta", {"delta": part["text"]})

                    final_reply = _extract_text(data.get("parts", []))

            except Exception as exc:
                logger.error(f"OpenCode task failed: {exc}", exc_info=True)
                emit("error", {"message": str(exc), "severity": "critical"})
                if retry_count < max_retries:
                    retry_count += 1
                    current_prompt = (
                        f"The previous attempt failed with error: {exc}\n"
                        f"Original task: {prompt}\n"
                        f"Please fix the issue and retry."
                    )
                    continue
                return {
                    "status": "error",
                    "reply": f"OpenCode agent failed after {max_retries} retries: {exc}",
                    "engine": "opencode",
                    "tool_calls": executed_tools,
                    "tool_results": all_tool_results,
                }

            has_errors = any(not tr.get("success", True) for tr in all_tool_results)
            if has_errors and retry_count < max_retries:
                error_msgs = [
                    tr.get("output", "") for tr in all_tool_results if not tr.get("success", True)
                ]
                retry_count += 1
                current_prompt = (
                    f"Errors occurred during execution:\n"
                    + "\n".join(error_msgs)
                    + f"\n\nOriginal task: {prompt}\nFix these errors and complete the task."
                )
                emit("status", {"message": "retrying_after_errors", "attempt": retry_count})
                continue

            break

        if not all_tool_results and not collected_diffs and not final_reply:
            # Turn produced zero tool activity, zero file changes and zero text —
            # usually a rejected model/provider call inside opencode. Never report
            # that as success; fall through to the built-in engine.
            emit("agent_complete", {"engine": "opencode", "retries": retry_count, "status": "error"})
            return {
                "status": "error",
                "reply": "OpenCode completed the turn without executing any tools, making any file change, or returning text (model/provider likely rejected the request).",
                "engine": "opencode",
                "provider": f"opencode (build/{model})",
                "tool_calls": executed_tools,
                "tool_results": all_tool_results,
                "diffs": collected_diffs,
                "errors": ["opencode turn produced no actions"],
                "retries": retry_count,
            }

        final_errors = [tr for tr in all_tool_results if not tr.get("success", True)]
        if final_errors:            # Retries exhausted with failures still present — report honestly so
            # the caller can fall back instead of showing a fake success.
            emit("agent_complete", {"engine": "opencode", "retries": retry_count, "status": "error"})
            return {
                "status": "error",
                "reply": final_reply
                or "OpenCode reported tool failures that were not resolved; no verified changes were made.",
                "engine": "opencode",
                "provider": f"opencode (build/{model})",
                "tool_calls": executed_tools,
                "tool_results": all_tool_results,
                "diffs": collected_diffs,
                "errors": [str(tr.get("output", ""))[:300] for tr in final_errors],
                "retries": retry_count,
            }

        emit("agent_complete", {
            "engine": "opencode",
            "retries": retry_count,
            "diff_count": len(collected_diffs),
            "status": "ok",
        })

        return {
            "status": "ok",
            "reply": final_reply or "Task completed via OpenCode, sir.",
            "engine": "opencode",
            "provider": f"opencode (build/{model})",
            "tool_calls": executed_tools,
            "tool_results": all_tool_results,
            "diffs": collected_diffs,
            "retries": retry_count,
        }


_opencode_bridge: Optional[OpenCodeBridge] = None


def get_opencode_bridge(workspace: str = "") -> OpenCodeBridge:
    global _opencode_bridge
    if _opencode_bridge is None or (workspace and _opencode_bridge._workspace != workspace):
        if _opencode_bridge is not None:
            _opencode_bridge.close()
        _opencode_bridge = OpenCodeBridge(workspace=workspace)
    return _opencode_bridge
