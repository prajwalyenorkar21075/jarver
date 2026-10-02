"""Skill Executor - Runs skill steps sequentially with context resolution."""

import logging
import re
from typing import Any

from app.openjarvis.skills.types import SkillManifest
from app.openjarvis.tools import ToolRegistry

logger = logging.getLogger(__name__)


class SkillExecutor:
    def __init__(self):
        self._skill_resolver = None

    def set_skill_resolver(self, resolver):
        self._skill_resolver = resolver

    async def execute(self, skill: SkillManifest, initial_context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = dict(initial_context or {})
        results = {}

        for i, step in enumerate(skill.steps):
            if step.skill_name and self._skill_resolver:
                sub_skill = self._skill_resolver(step.skill_name)
                if sub_skill:
                    sub_result = await self.execute(sub_skill, context)
                    if step.output_key:
                        context[step.output_key] = sub_result
                    results[f"step_{i}_{step.skill_name}"] = sub_result
                    continue

            tool = ToolRegistry.get(step.tool_name)
            if not tool:
                logger.warning(f"Tool not found for skill step: {step.tool_name}")
                results[f"step_{i}_{step.tool_name}"] = {"error": f"Tool not found: {step.tool_name}"}
                continue

            resolved_args = self._resolve_template(step.arguments_template, context)

            try:
                result = await tool.execute(**resolved_args)
                results[f"step_{i}_{step.tool_name}"] = result
                if step.output_key:
                    context[step.output_key] = result
            except Exception as e:
                logger.error(f"Skill step {step.tool_name} failed: {e}")
                results[f"step_{i}_{step.tool_name}"] = {"error": str(e)}

        return {
            "skill": skill.name,
            "steps_executed": len(skill.steps),
            "results": results,
            "context": context,
        }

    def _resolve_template(self, template: Any, context: dict[str, Any]) -> Any:
        if isinstance(template, str):
            def replacer(match):
                key = match.group(1)
                return str(context.get(key, match.group(0)))
            return re.sub(r"\{(\w+)\}", replacer, template)
        elif isinstance(template, dict):
            return {k: self._resolve_template(v, context) for k, v in template.items()}
        elif isinstance(template, list):
            return [self._resolve_template(item, context) for item in template]
        return template
