"""Skill type definitions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillStep:
    tool_name: str
    arguments_template: dict[str, Any] = field(default_factory=dict)
    output_key: str = ""
    skill_name: str | None = None


@dataclass
class SkillManifest:
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    steps: list[SkillStep] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    depends: list[str] = field(default_factory=list)
    user_invocable: bool = True
    disable_model_invocation: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    signature: str | None = None
