"""Thinking/reasoning scratchpad tool."""

import logging
from . import BaseTool, ToolSpec, ToolRegistry

logger = logging.getLogger(__name__)


@ToolRegistry.register("think")
class ThinkTool(BaseTool):
    """Reasoning scratchpad — lets the AI think step-by-step."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="think",
            description="Use this tool to think through a problem step-by-step. Your reasoning will NOT be shown to the user. Use it for planning, analysis, and breaking down complex problems.",
            parameters={
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "Your step-by-step reasoning"
                    }
                },
                "required": ["thought"]
            },
            category="reasoning",
        )

    async def execute(self, thought: str = "", **kwargs) -> dict:
        logger.debug(f"[THINK] {thought[:200]}")
        return {"status": "noted", "length": len(thought)}
