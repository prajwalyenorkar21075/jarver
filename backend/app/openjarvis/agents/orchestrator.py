"""Orchestrator Agent - Multi-turn agent with tool-calling loop.

Ported from OpenJARVIS (Stanford Hazy Research).
Supports two modes:
- function_calling: Uses OpenAI-format tool_calls
- structured: Uses THOUGHT/TOOL/INPUT/FINAL_ANSWER text protocol
"""

import logging
import re
from typing import Any

from app.openjarvis.agents.loop_guard import LoopGuard, LoopVerdict
from app.openjarvis.tools import ToolRegistry

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    def __init__(self, mode: str = "structured", max_turns: int = 10):
        self.mode = mode
        self.max_turns = max_turns
        self.loop_guard = LoopGuard()
        self._tools = {}
        self._token_usage = {"prompt": 0, "completion": 0, "total": 0}

    def register_tools(self, tool_names: list[str] | None = None):
        if tool_names:
            for name in tool_names:
                tool = ToolRegistry.get(name)
                if tool:
                    self._tools[name] = tool
        else:
            for name in ToolRegistry.list_names():
                self._tools[name] = ToolRegistry.get(name)

    async def run(self, query: str, llm_call=None) -> dict[str, Any]:
        if not self._tools:
            self.register_tools()

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": query},
        ]

        final_answer = None
        turn = 0

        while turn < self.max_turns:
            turn += 1
            logger.info(f"Orchestrator turn {turn}/{self.max_turns}")

            if self.mode == "structured":
                result = await self._structured_turn(messages, llm_call)
            else:
                result = await self._function_calling_turn(messages, llm_call)

            if result.get("final_answer"):
                final_answer = result["final_answer"]
                break

            if result.get("tool_calls"):
                for tc in result["tool_calls"]:
                    verdict = self.loop_guard.record_call(tc["name"], tc.get("arguments"))
                    if verdict == LoopVerdict.BLOCK:
                        logger.warning("Loop guard blocked execution")
                        final_answer = "I encountered a loop in my reasoning. Please try rephrasing your request."
                        break

                    tool = self._tools.get(tc["name"])
                    if tool:
                        try:
                            tool_result = await tool.execute(**tc.get("arguments", {}))
                            messages.append({
                                "role": "tool",
                                "content": str(tool_result),
                                "tool_name": tc["name"],
                            })
                        except Exception as e:
                            logger.error(f"Tool {tc['name']} failed: {e}")
                            messages.append({
                                "role": "tool",
                                "content": f"Error: {e}",
                                "tool_name": tc["name"],
                            })

                if final_answer:
                    break

        if not final_answer:
            final_answer = messages[-1].get("content", "I was unable to complete the request.")

        return {
            "answer": final_answer,
            "turns": turn,
            "tools_used": list(set(
                m.get("tool_name", "") for m in messages if m.get("role") == "tool"
            )),
            "token_usage": self._token_usage,
            "loop_guard_stats": self.loop_guard.stats,
        }

    async def _structured_turn(self, messages: list[dict], llm_call) -> dict[str, Any]:
        if llm_call is None:
            return {"final_answer": "No LLM configured - using tool-only mode"}

        response = await llm_call(messages)
        content = response.get("content", "")

        final_match = re.search(r"FINAL_ANSWER:\s*(.+)", content, re.DOTALL)
        if final_match:
            return {"final_answer": final_match.group(1).strip()}

        tool_calls = []
        tool_matches = re.findall(
            r"TOOL:\s*(\w+)\s*\nINPUT:\s*(.+?)(?=\n(?:THOUGHT|TOOL|FINAL_ANSWER)|$)",
            content,
            re.DOTALL,
        )
        for tool_name, input_text in tool_matches:
            try:
                import json
                arguments = json.loads(input_text.strip())
            except (json.JSONDecodeError, ValueError):
                arguments = {"input": input_text.strip()}
            tool_calls.append({"name": tool_name.strip(), "arguments": arguments})

        if not tool_calls:
            return {"final_answer": content.strip()}

        messages.append({"role": "assistant", "content": content})
        return {"tool_calls": tool_calls}

    async def _function_calling_turn(self, messages: list[dict], llm_call) -> dict[str, Any]:
        if llm_call is None:
            return {"final_answer": "No LLM configured - using tool-only mode"}

        schemas = [t.to_openai_schema() for t in self._tools.values()]
        response = await llm_call(messages, tools=schemas)

        if response.get("content") and not response.get("tool_calls"):
            return {"final_answer": response["content"]}

        tool_calls = []
        for tc in response.get("tool_calls", []):
            tool_calls.append({
                "name": tc["function"]["name"],
                "arguments": tc["function"].get("arguments", {}),
            })

        messages.append({"role": "assistant", "content": response.get("content", ""), "tool_calls": response.get("tool_calls", [])})
        return {"tool_calls": tool_calls}

    def _build_system_prompt(self) -> str:
        tool_descriptions = []
        for name, tool in self._tools.items():
            tool_descriptions.append(f"- {name}: {tool.spec.description}")

        tools_section = "\n".join(tool_descriptions) if tool_descriptions else "No tools available."

        return f"""You are JARVIS, an intelligent assistant with access to the following tools:

{tools_section}

To use a tool, write:
THOUGHT: <your reasoning>
TOOL: <tool_name>
INPUT: <json arguments>

When you have the final answer, write:
FINAL_ANSWER: <your answer>

Be concise and accurate. Think step by step."""
