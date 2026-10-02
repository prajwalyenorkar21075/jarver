"""Skill Loader - Load skill manifests from TOML files."""

import logging
from pathlib import Path
from typing import Any

from app.openjarvis.skills.types import SkillManifest, SkillStep

logger = logging.getLogger(__name__)


def load_skill(path: str | Path) -> SkillManifest | None:
    path = Path(path)
    if not path.exists():
        logger.warning(f"Skill file not found: {path}")
        return None

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            logger.error("No TOML library available (need Python 3.11+ or tomli package)")
            return None

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        logger.error(f"Failed to parse skill TOML {path}: {e}")
        return None

    skill_data = data.get("skill", data)

    steps = []
    for step_data in skill_data.get("steps", []):
        steps.append(SkillStep(
            tool_name=step_data.get("tool_name", ""),
            arguments_template=step_data.get("arguments_template", {}),
            output_key=step_data.get("output_key", ""),
            skill_name=step_data.get("skill_name"),
        ))

    return SkillManifest(
        name=skill_data.get("name", path.stem),
        description=skill_data.get("description", ""),
        version=skill_data.get("version", "1.0.0"),
        author=skill_data.get("author", ""),
        steps=steps,
        required_capabilities=skill_data.get("required_capabilities", []),
        tags=skill_data.get("tags", []),
        depends=skill_data.get("depends", []),
        user_invocable=skill_data.get("user_invocable", True),
        disable_model_invocation=skill_data.get("disable_model_invocation", False),
        metadata=skill_data.get("metadata", {}),
        signature=skill_data.get("signature"),
    )


def discover_skills(directory: str | Path) -> list[SkillManifest]:
    directory = Path(directory)
    if not directory.exists():
        return []

    skills = []

    for toml_file in directory.rglob("*.toml"):
        skill = load_skill(toml_file)
        if skill:
            skills.append(skill)

    for skill_dir in directory.iterdir():
        if skill_dir.is_dir():
            skill_toml = skill_dir / "skill.toml"
            if skill_toml.exists():
                skill = load_skill(skill_toml)
                if skill and not any(s.name == skill.name for s in skills):
                    skills.append(skill)

    return skills
