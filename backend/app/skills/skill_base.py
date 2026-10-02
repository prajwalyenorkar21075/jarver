import json
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("jarvis.skills")


class SkillTool:
    """Represents an executable function callable by AI models."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Any],
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def to_openai_tool(self) -> Dict[str, Any]:
        """Convert to OpenAI standard tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def execute(self, **kwargs) -> Any:
        return self.handler(**kwargs)


class BaseSkill:
    """Base class for modular JARVIS plugins/skills."""

    id: str = "base"
    display_name: str = "Base Skill"
    description: str = "Base skill plugin"
    icon: str = "sparkles"
    version: str = "1.0.0"

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.tools: List[SkillTool] = []
        self._setup_tools()

    def _setup_tools(self):
        """Override in subclasses to register SkillTool objects."""
        pass

    def get_tools(self) -> List[SkillTool]:
        return self.tools if self.enabled else []

    def get_system_prompt_addon(self) -> str:
        """Extra context injected into AI reasoning prompt when skill is enabled."""
        return ""


class SkillRegistry:
    """Central registry and dispatcher for all JARVIS skills and plugins."""

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill):
        self._skills[skill.id] = skill
        logger.info(f"Registered skill '{skill.id}' ({skill.display_name}) with {len(skill.tools)} tools")

    def get_skill(self, skill_id: str) -> Optional[BaseSkill]:
        return self._skills.get(skill_id)

    def list_skills(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": s.id,
                "display_name": s.display_name,
                "description": s.description,
                "icon": s.icon,
                "version": s.version,
                "enabled": s.enabled,
                "tools_count": len(s.tools),
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    }
                    for t in s.tools
                ],
            }
            for s in self._skills.values()
        ]

    def set_skill_enabled(self, skill_id: str, enabled: bool) -> bool:
        if skill_id in self._skills:
            self._skills[skill_id].enabled = enabled
            return True
        return False

    def get_active_tools(self) -> List[SkillTool]:
        active = []
        for s in self._skills.values():
            if s.enabled:
                active.extend(s.get_tools())
        return active

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        return [t.to_openai_tool() for t in self.get_active_tools()]

    def get_combined_system_prompt(self) -> str:
        prompts = []
        for s in self._skills.values():
            if s.enabled:
                addon = s.get_system_prompt_addon()
                if addon:
                    prompts.append(addon.strip())
        return "\n\n".join(prompts)

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatch a tool call to its handler."""
        for skill in self._skills.values():
            if not skill.enabled:
                continue
            for tool in skill.tools:
                if tool.name == tool_name:
                    try:
                        # Pass context if handler accepts it
                        res = tool.execute(**arguments)
                        # Handlers signal failure by returning {"error": ...} or
                        # {"success": False} without raising — treat those as failures.
                        if isinstance(res, dict) and ("error" in res or res.get("success") is False):
                            return {
                                "success": False,
                                "tool": tool_name,
                                "skill": skill.id,
                                "error": str(res.get("error", res.get("message", "Tool reported failure"))),
                                "result": res,
                            }
                        return {
                            "success": True,
                            "tool": tool_name,
                            "skill": skill.id,
                            "result": res,
                        }
                    except Exception as exc:
                        logger.error(f"Error executing tool {tool_name}: {exc}", exc_info=True)
                        return {
                            "success": False,
                            "tool": tool_name,
                            "skill": skill.id,
                            "error": str(exc),
                        }

        return {
            "success": False,
            "tool": tool_name,
            "error": f"Tool '{tool_name}' not found or its skill is currently disabled.",
        }


# Global singleton registry
skills_registry = SkillRegistry()
