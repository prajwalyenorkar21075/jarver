"""Base tool class and tool registry for OpenJARVIS tools."""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict
    category: str = "general"
    metadata: dict = field(default_factory=dict)


class BaseTool:
    """Base class for all JARVIS tools."""

    @property
    def spec(self) -> ToolSpec:
        raise NotImplementedError

    async def execute(self, **kwargs) -> Any:
        raise NotImplementedError

    def to_openai_schema(self) -> dict:
        s = self.spec
        return {
            "type": "function",
            "function": {
                "name": s.name,
                "description": s.description,
                "parameters": s.parameters,
            }
        }


class ToolRegistry:
    """Global tool registry."""

    _tools: dict[str, BaseTool] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(tool_cls):
            instance = tool_cls()
            cls._tools[name] = instance
            logger.debug(f"[TOOLS] Registered: {name}")
            return tool_cls
        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        return cls._tools.get(name)

    @classmethod
    def all_tools(cls) -> dict[str, BaseTool]:
        return dict(cls._tools)

    @classmethod
    def list_names(cls) -> list[str]:
        return list(cls._tools.keys())

    @classmethod
    def get_openai_schemas(cls, tool_names: list[str] | None = None) -> list[dict]:
        if tool_names is None:
            tool_names = list(cls._tools.keys())
        schemas = []
        for name in tool_names:
            tool = cls._tools.get(name)
            if tool:
                schemas.append(tool.to_openai_schema())
        return schemas


def _auto_register_tools():
    """Import tool modules to trigger @ToolRegistry.register decorators."""
    import importlib
    tool_modules = [
        "app.openjarvis.tools.calculator",
        "app.openjarvis.tools.think",
        "app.openjarvis.tools.code_interpreter",
        "app.openjarvis.tools.http_request",
        "app.openjarvis.tools.file_ops",
    ]
    for mod in tool_modules:
        try:
            importlib.import_module(mod)
        except Exception as e:
            logger.warning(f"Failed to import tool module {mod}: {e}")


_auto_register_tools()
