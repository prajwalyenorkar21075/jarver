"""Skill Manager - Discovery, resolution, catalog generation, and execution."""

import logging
from pathlib import Path
from typing import Any

from app.openjarvis.skills.types import SkillManifest
from app.openjarvis.skills.loader import load_skill, discover_skills
from app.openjarvis.skills.executor import SkillExecutor

logger = logging.getLogger(__name__)


class SkillManager:
    def __init__(self, skill_dirs: list[str | Path] | None = None):
        self._skills: dict[str, SkillManifest] = {}
        self._executor = SkillExecutor()
        self._skill_dirs = skill_dirs or []

    def discover(self) -> int:
        count = 0
        for skill_dir in self._skill_dirs:
            skills = discover_skills(skill_dir)
            for skill in skills:
                if skill.name not in self._skills:
                    self._skills[skill.name] = skill
                    count += 1
                    logger.info(f"Discovered skill: {skill.name} v{skill.version}")
        return count

    def register(self, skill: SkillManifest) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> SkillManifest | None:
        return self._skills.get(name)

    def list_skills(self) -> list[SkillManifest]:
        return list(self._skills.values())

    def get_catalog_xml(self) -> str:
        lines = ["<available_skills>"]
        for skill in self._skills.values():
            if not skill.user_invocable:
                continue
            lines.append(f'  <skill name="{skill.name}" version="{skill.version}">')
            lines.append(f"    <description>{skill.description}</description>")
            if skill.tags:
                lines.append(f'    <tags>{", ".join(skill.tags)}</tags>')
            lines.append(f"    <steps>{len(skill.steps)}</steps>")
            lines.append("  </skill>")
        lines.append("</available_skills>")
        return "\n".join(lines)

    async def execute(self, skill_name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        skill = self._skills.get(skill_name)
        if not skill:
            return {"error": f"Skill not found: {skill_name}"}

        return await self._executor.execute(skill, context)

    def validate_dependencies(self) -> list[str]:
        errors = []
        for skill in self._skills.values():
            for dep in skill.depends:
                if dep not in self._skills:
                    errors.append(f"Skill '{skill.name}' depends on missing skill '{dep}'")

        visited = set()
        rec_stack = set()

        def has_cycle(name: str) -> bool:
            visited.add(name)
            rec_stack.add(name)
            skill = self._skills.get(name)
            if skill:
                for dep in skill.depends:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            rec_stack.discard(name)
            return False

        for name in self._skills:
            if name not in visited:
                if has_cycle(name):
                    errors.append(f"Dependency cycle detected involving '{name}'")

        return errors
