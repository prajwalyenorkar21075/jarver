import os
import json
import logging
import asyncio
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import httpx

EventCallback = Callable[[str, Dict[str, Any]], None]

try:
    from app.skills import skills_registry
    from app.persistent_memory import (
        create_or_get_coding_session,
        save_coding_message,
        get_coding_messages,
        list_coding_sessions,
        get_coding_session,
        WORKSPACE_ROOT,
        PROJECT_ROOT,
    )
except ImportError:
    from skills import skills_registry
    from persistent_memory import (
        create_or_get_coding_session,
        save_coding_message,
        get_coding_messages,
        list_coding_sessions,
        get_coding_session,
        WORKSPACE_ROOT,
        PROJECT_ROOT,
    )

logger = logging.getLogger("jarvis.coding")

# Output-token budget for coding turns. write_file tool calls must fit the ENTIRE
# file inside one JSON payload; 1500 tokens silently truncated most real files.
CODING_MAX_OUTPUT_TOKENS = int(os.getenv("CODING_MAX_OUTPUT_TOKENS", "16000"))
CODING_HTTP_TIMEOUT = float(os.getenv("CODING_HTTP_TIMEOUT_SECONDS", "120"))

# Quota failover cooldown to eliminate latency loops
_openai_coding_cooldown_until: float = 0.0

CODING_SYSTEM_PROMPT = """You are J.A.R.V.I.S., Tony Stark's elite Autonomous AI Coding Assistant and Systems Architect.
You possess world-class expertise in modern full-stack development, Python, TypeScript, React, TailwindCSS, Vite, Node.js, systems programming, and algorithms.

Core Directives:
1. AUTONOMOUS & ACTION-ORIENTED: Don't just talk about code—inspect files, read directories, generate diffs, write implementations, and verify them using your skills.
2. PRESERVE EXISTING CODE: Always preserve existing comments, formatting, and working features unless explicitly told to refactor. Before modifying a file, read it first using `read_file`.
3. SAFE CODE EDITING: Use `patch_file` for targeted surgical edits or `write_file` for new modules. All edits are automatically backed up and reversible via `rollback_file`.
4. VOICE-READY & CONCISE: In your final response, provide a clear, composed, articulate Stark-style summary (2-4 sentences) suitable for vocal synthesis, along with formatted code blocks or diffs for the UI.
5. TOOL USAGE: When you need information, call your tools. You can inspect workspace structure, search code with regex, execute commands, and check git status.
6. AUTONOMOUS ERROR RECOVERY: When a command fails or tests error, inspect the output, diagnose the root cause, fix the code, and re-run until the task succeeds. Never stop at the first failure.
7. VERIFY YOUR WORK: After writing code, always run it (via run_command) to confirm it works. Run tests if they exist.
"""


def _get_env_credentials():
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-6-astra")
    responses_url = os.getenv("OPENAI_RESPONSES_API_URL", "https://api.openai.com/v1/responses")
    gemini_key = os.getenv("GEMINI_API_KEY")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
    groq_key = os.getenv("GROQ_API_KEY")
    groq_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    # If not in os.environ, try reading backend .env
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k == "OPENAI_API_KEY" and not api_key:
                    api_key = v
                elif k == "OPENAI_MODEL" and not model:
                    model = v
                elif k == "GEMINI_API_KEY" and not gemini_key:
                    gemini_key = v
                elif k == "GROQ_API_KEY" and not groq_key:
                    groq_key = v

    return {
        "openai_key": api_key,
        "openai_model": model or "gpt-6-astra",
        "openai_responses_url": responses_url,
        "gemini_key": gemini_key,
        "gemini_model": gemini_model,
        "groq_key": groq_key,
        "groq_model": groq_model,
    }


class CodingEngine:
    """Orchestrates multi-turn autonomous coding sessions, tool loops, and memory."""

    def __init__(self):
        self.registry = skills_registry
        self._cancelled_sessions: set[str] = set()

    def cancel_session(self, session_id: str):
        """Mark a session as cancelled to abort ongoing turns."""
        self._cancelled_sessions.add(session_id)

    def is_cancelled(self, session_id: str) -> bool:
        return session_id in self._cancelled_sessions

    def clear_cancellation(self, session_id: str):
        self._cancelled_sessions.discard(session_id)

    def _emit(self, callback: Optional[EventCallback], event_type: str, data: Dict[str, Any]) -> None:
        if callback:
            try:
                callback(event_type, data)
            except Exception as ex:
                logger.warning(f"Event callback error for {event_type}: {ex}")

    async def execute_coding_turn(
        self,
        session_id: str,
        user_message: str,
        active_file: str = "",
        auto_run_tools: bool = True,
        max_tool_iterations: int = 15,
        event_callback: Optional[EventCallback] = None,
        autonomous: bool = True,
    ) -> Dict[str, Any]:
        """Execute a full autonomous coding turn with reasoning, tool loops, and error retry."""
        creds = _get_env_credentials()
        session = create_or_get_coding_session(session_id, active_file=active_file)

        self._emit(event_callback, "agent_start", {
            "engine": "jarvis",
            "session_id": session_id,
            "prompt": user_message[:200],
        })

        # Retrieve previous conversation messages for context
        prior_messages = get_coding_messages(session_id, limit=20)

        # Format context messages for LLM
        messages = [{"role": "system", "content": CODING_SYSTEM_PROMPT}]
        if active_file:
            messages.append({
                "role": "system",
                "content": f"The user currently has the file '{active_file}' open in their workspace editor.",
            })

        for m in prior_messages:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_message})

        executed_tools = []
        collected_diffs = []
        all_tool_results = []
        verified_writes: List[str] = []
        last_iteration_errors: List[str] = []
        final_reply = ""
        provider_used = "none"

        # Autonomous ReAct Loop with error recovery
        for iteration in range(max_tool_iterations):
            if self.is_cancelled(session_id):
                self.clear_cancellation(session_id)
                final_reply = "Operation cancelled by user, sir."
                break

            self._emit(event_callback, "iteration_start", {
                "iteration": iteration + 1,
                "max_iterations": max_tool_iterations,
            })

            # Try Provider 1: OpenAI (GPT-6 Astra via Responses API or Tools)
            llm_result = None
            if creds["openai_key"] and time.time() >= _openai_coding_cooldown_until:
                try:
                    llm_result = await self._call_openai(creds, messages)
                    provider_used = f"openai ({creds['openai_model']})"
                except Exception as ex_openai:
                    logger.warning(f"OpenAI {creds['openai_model']} notice: {ex_openai}. Cascading to Gemini/Groq...")

            # Try Provider 2: Gemini 3.1 Flash Lite
            if not llm_result and creds["gemini_key"]:
                try:
                    llm_result = await self._call_gemini(creds, messages)
                    provider_used = f"gemini ({creds['gemini_model']})"
                except Exception as ex_gemini:
                    logger.warning(f"Gemini failed: {ex_gemini}. Cascading to Groq...")

            # Try Provider 3: Groq Qwen
            if not llm_result and creds["groq_key"]:
                try:
                    llm_result = await self._call_groq(creds, messages)
                    provider_used = f"groq ({creds['groq_model']})"
                except Exception as ex_groq:
                    logger.error(f"Groq failed: {ex_groq}")

            if not llm_result:
                final_reply = "I apologize, sir. All neural coding reasoning providers are currently unreachable or out of API quota. Core local diagnostics remain active."
                break

            tool_calls = llm_result.get("tool_calls", [])
            reply_text = llm_result.get("content", "")

            # Stream reply tokens to frontend
            if reply_text:
                self._emit(event_callback, "token_delta", {"delta": reply_text})

            # If no tool calls, model provided final response
            if not tool_calls or not auto_run_tools:
                final_reply = reply_text or "Task analysis complete, sir."
                break

            # Execute tool calls
            iteration_results = []
            iteration_errors = []
            malformed_args = False
            for tc in tool_calls:
                if self.is_cancelled(session_id):
                    break
                t_name = tc.get("name")
                t_args = tc.get("arguments", {})
                if isinstance(t_args, str):
                    try:
                        t_args = json.loads(t_args)
                    except Exception:
                        # Truncated JSON (usually the output-token cap cutting a
                        # huge write_file payload). Never run the tool with {} —
                        # report honestly so the model retries with less content.
                        malformed_args = True
                        err_msg = (
                            f"Tool '{t_name}' arguments were malformed or truncated mid-stream. "
                            "The generated payload exceeded the output limit. Split the work: use "
                            "patch_file for small edits, or write a smaller complete file."
                        )
                        iteration_errors.append(err_msg)
                        self._emit(event_callback, "error", {
                            "tool": t_name,
                            "message": err_msg,
                            "severity": "error",
                        })
                        continue

                self._emit(event_callback, "tool_start", {"tool": t_name, "args": t_args})
                logger.info(f"CodingEngine executing tool: {t_name} with args {list(t_args.keys())}")
                tool_res = self.registry.execute_tool(t_name, t_args)

                executed_tools.append({
                    "id": tc.get("id", f"call_{len(executed_tools)}"),
                    "name": t_name,
                    "arguments": t_args,
                })
                iteration_results.append({
                    "tool": t_name,
                    "result": tool_res,
                })
                all_tool_results.append(tool_res)

                self._emit(event_callback, "tool_result", {"tool": t_name, "result": tool_res})

                # Emit terminal output for run_command
                if t_name == "run_command":
                    result_data = tool_res.get("result", tool_res)
                    if isinstance(result_data, dict):
                        self._emit(event_callback, "terminal_output", {
                            "cmd": result_data.get("command", ""),
                            "stdout": result_data.get("stdout", ""),
                            "stderr": result_data.get("stderr", result_data.get("error", "")),
                            "exit_code": result_data.get("exit_code", -1),
                        })
                        if result_data.get("exit_code", 0) != 0:
                            iteration_errors.append(
                                f"Command '{result_data.get('command', '')}' failed "
                                f"(exit {result_data.get('exit_code')}): "
                                f"{result_data.get('stderr', result_data.get('error', ''))}"
                            )

                # Check for tool-level errors
                if not tool_res.get("success", True):
                    err_msg = tool_res.get("error", str(tool_res.get("result", "Unknown error")))
                    iteration_errors.append(f"Tool '{t_name}' failed: {err_msg}")
                    self._emit(event_callback, "error", {
                        "tool": t_name,
                        "message": err_msg,
                        "severity": "error",
                    })

                # Check if tool produced a diff
                if tool_res.get("success") and isinstance(tool_res.get("result"), dict):
                    inner = tool_res["result"]
                    if t_name in ("write_file", "patch_file") and inner.get("verified"):
                        verified_writes.append(inner.get("path", t_name))
                    diff = inner.get("diff")
                    if diff:
                        diff_entry = {
                            "path": tool_res["result"].get("path", ""),
                            "diff": diff,
                        }
                        collected_diffs.append(diff_entry)
                        self._emit(event_callback, "file_changed", diff_entry)

            # Autonomous error recovery: feed errors back to LLM for retry
            last_iteration_errors = iteration_errors
            if iteration_errors and autonomous and iteration < max_tool_iterations - 1:
                self._emit(event_callback, "retry", {
                    "attempt": iteration + 1,
                    "errors": iteration_errors,
                })
                messages.append({
                    "role": "assistant",
                    "content": reply_text or "Encountered errors during execution.",
                })
                tool_response_text = "\n".join(
                    f"Tool '{res['tool']}' output: {json.dumps(res['result'])}"
                    for res in iteration_results
                )
                error_context = (
                    f"Tool Execution Results:\n{tool_response_text}\n\n"
                    "The following errors occurred. Diagnose, fix the code, and retry:\n"
                    + "\n".join(f"- {e}" for e in iteration_errors)
                )
                messages.append({"role": "user", "content": error_context})
                continue

            # Append assistant message with tool calls and tool responses back into context.
            # Provider history flattening only keeps `content`, so embed a compact tool
            # ledger there — otherwise the model "forgets" it already wrote the file and
            # regenerates (and truncates) it every iteration.
            tool_ledger = "; ".join(
                f"{res['tool']} -> "
                + ("OK" if res["result"].get("success") else f"FAILED: {str(res['result'].get('error', ''))[:160]}")
                for res in iteration_results
            )
            messages.append({
                "role": "assistant",
                "content": ((reply_text or "") + f"\n[TOOLS EXECUTED THIS TURN: {tool_ledger}]").strip(),
                "tool_calls": [
                    {
                        "id": f"call_{i}",
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc.get("arguments", {}))},
                    }
                    for i, tc in enumerate(tool_calls)
                ],
            })

            tool_response_text = "\n".join(
                f"Tool '{res['tool']}' output: {json.dumps(res['result'])}" for res in iteration_results
            )
            messages.append({"role": "user", "content": f"Tool Execution Results:\n{tool_response_text}"})

        # Persist exchange to SQLite database
        save_coding_message(
            session_id=session_id,
            role="user",
            content=user_message,
        )
        save_coding_message(
            session_id=session_id,
            role="assistant",
            content=final_reply,
            tool_calls=executed_tools,
            tool_results=all_tool_results,
            thoughts="",
            diffs=collected_diffs,
        )

        status = "ok"
        if provider_used == "none":
            status = "error"
        elif last_iteration_errors and not verified_writes and not collected_diffs:
            status = "error"
        elif last_iteration_errors:
            status = "partial"

        self._emit(event_callback, "agent_complete", {
            "engine": "jarvis",
            "session_id": session_id,
            "tool_count": len(executed_tools),
            "diff_count": len(collected_diffs),
            "verified_writes": verified_writes,
            "status": status,
        })

        return {
            "session_id": session_id,
            "reply": final_reply,
            "provider": provider_used,
            "tool_calls": executed_tools,
            "tool_results": all_tool_results,
            "diffs": collected_diffs,
            "verified_writes": verified_writes,
            "errors": last_iteration_errors,
            "status": status,
            "engine": "jarvis",
        }

    async def execute_autonomous_task(
        self,
        session_id: str,
        user_message: str,
        active_file: str = "",
        event_callback: Optional[EventCallback] = None,
        prefer_opencode: bool = True,
    ) -> Dict[str, Any]:
        """Route to OpenCode when available, otherwise use built-in engine."""
        use_opencode = prefer_opencode and os.getenv("JARVIS_USE_OPENCODE", "auto") != "false"

        if use_opencode:
            try:
                from app.opencode_bridge import is_opencode_available, get_opencode_bridge
            except ImportError:
                from opencode_bridge import is_opencode_available, get_opencode_bridge

            if is_opencode_available():
                self._emit(event_callback, "status", {"message": "routing_to_opencode"})
                bridge = get_opencode_bridge(str(WORKSPACE_ROOT))
                result = await bridge.execute_task(
                    prompt=user_message,
                    event_callback=event_callback,
                    max_retries=3,
                )
                if result.get("status") == "ok":
                    save_coding_message(session_id=session_id, role="user", content=user_message)
                    save_coding_message(
                        session_id=session_id,
                        role="assistant",
                        content=result.get("reply", ""),
                        tool_calls=result.get("tool_calls", []),
                        tool_results=result.get("tool_results", []),
                        diffs=result.get("diffs", []),
                    )
                    result["session_id"] = session_id
                    return result
                self._emit(event_callback, "status", {
                    "message": "opencode_failed_fallback_to_jarvis",
                })

        return await self.execute_coding_turn(
            session_id=session_id,
            user_message=user_message,
            active_file=active_file,
            auto_run_tools=True,
            max_tool_iterations=15,
            event_callback=event_callback,
            autonomous=True,
        )

    async def _call_openai(self, creds: dict, messages: list[dict]) -> dict:
        """Call OpenAI Responses API or chat completions with tools."""
        global _openai_coding_cooldown_until
        tools = self.registry.get_openai_tools()
        headers = {
            "Authorization": f"Bearer {creds['openai_key']}",
            "Content-Type": "application/json",
        }

        # Try Responses API first
        responses_url = creds.get("openai_responses_url", "https://api.openai.com/v1/responses")
        input_items = []
        for m in messages[-10:]:
            r = m.get("role", "user")
            input_items.append({"role": "user" if r == "user" else "assistant", "content": m.get("content", "")})

        payload = {
            "model": creds["openai_model"],
            "instructions": CODING_SYSTEM_PROMPT,
            "input": input_items,
            "tools": tools[:15],
            "max_output_tokens": CODING_MAX_OUTPUT_TOKENS,
        }

        async with httpx.AsyncClient(timeout=CODING_HTTP_TIMEOUT) as client:
            try:
                resp = await client.post(responses_url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return self._parse_openai_response(data)
                elif resp.status_code == 429:
                    _openai_coding_cooldown_until = time.time() + 180.0
                    raise ValueError("OpenAI quota exhausted (HTTP 429)")
                resp.raise_for_status()
            except ValueError:
                raise
            except Exception:
                if time.time() < _openai_coding_cooldown_until:
                    raise
                # Fallback to standard OpenAI /v1/chat/completions
                chat_url = "https://api.openai.com/v1/chat/completions"
                chat_payload = {
                    "model": creds["openai_model"],
                    "messages": messages[-12:],
                    "tools": tools[:15],
                    "temperature": 0.3,
                }
                chat_resp = await client.post(chat_url, headers=headers, json=chat_payload)
                if chat_resp.status_code == 429:
                    _openai_coding_cooldown_until = time.time() + 180.0
                    raise ValueError("OpenAI quota exhausted (HTTP 429)")
                chat_resp.raise_for_status()
                data = chat_resp.json()
                msg = data["choices"][0]["message"]
                tool_calls = []
                if "tool_calls" in msg and msg["tool_calls"]:
                    for tc in msg["tool_calls"]:
                        fn = tc.get("function", {})
                        tool_calls.append({
                            "id": tc.get("id"),
                            "name": fn.get("name"),
                            "arguments": fn.get("arguments"),
                        })
                return {"content": msg.get("content", ""), "tool_calls": tool_calls}

    def _parse_openai_response(self, data: dict) -> dict:
        content = ""
        tool_calls = []
        if "output" in data and isinstance(data["output"], list):
            for item in data["output"]:
                if isinstance(item, dict):
                    if item.get("type") == "message" and "content" in item:
                        for c in item["content"]:
                            if isinstance(c, dict) and c.get("text"):
                                content += c["text"]
                    elif item.get("type") == "function_call":
                        tool_calls.append({
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "arguments": item.get("arguments"),
                        })
                    elif item.get("text"):
                        content += item["text"]
        elif "output_text" in data:
            content = data["output_text"]
        elif "choices" in data and len(data["choices"]) > 0:
            c = data["choices"][0].get("message", {})
            content = c.get("content", "")
            if c.get("tool_calls"):
                for tc in c["tool_calls"]:
                    tool_calls.append({
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    })
        return {"content": content.strip(), "tool_calls": tool_calls}

    async def _call_gemini(self, creds: dict, messages: list[dict]) -> dict:
        """Call Gemini generateContent with tools."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{creds['gemini_model']}:generateContent?key={creds['gemini_key']}"

        # Build Gemini function declarations
        tools_decl = []
        for t in self.registry.get_active_tools():
            tools_decl.append({
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            })

        contents = []
        for m in messages[-10:]:
            role = "user" if m.get("role") in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})

        payload = {
            "system_instruction": {"parts": [{"text": CODING_SYSTEM_PROMPT}]},
            "contents": contents,
            "tools": [{"function_declarations": tools_decl[:15]}] if tools_decl else [],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": CODING_MAX_OUTPUT_TOKENS},
        }

        async with httpx.AsyncClient(timeout=CODING_HTTP_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            candidate = data["candidates"][0]
            parts = candidate["content"]["parts"]
            content = ""
            tool_calls = []
            for p in parts:
                if "text" in p:
                    content += p["text"]
                if "functionCall" in p:
                    fc = p["functionCall"]
                    if not fc.get("name"):
                        continue  # truncated function call — skip instead of KeyError
                    tool_calls.append({
                        "name": fc["name"],
                        "arguments": fc.get("args", {}),
                    })

            return {"content": content.strip(), "tool_calls": tool_calls}

    async def _call_groq(self, creds: dict, messages: list[dict]) -> dict:
        """Call Groq Qwen chat completions."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {creds['groq_key']}",
            "Content-Type": "application/json",
        }
        tools = self.registry.get_openai_tools()

        payload = {
            "model": creds["groq_model"],
            "messages": messages[-10:],
            "tools": tools[:15],
            "temperature": 0.2,
            "max_tokens": CODING_MAX_OUTPUT_TOKENS,
        }

        async with httpx.AsyncClient(timeout=CODING_HTTP_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            msg = data["choices"][0]["message"]
            tool_calls = []
            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    tool_calls.append({
                        "id": tc.get("id"),
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    })
            return {"content": msg.get("content", ""), "tool_calls": tool_calls}


coding_engine = CodingEngine()
