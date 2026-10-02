try:
    from .skill_base import BaseSkill, SkillTool, SkillRegistry, skills_registry
    from .coding_skill import CodingSkill
    from .terminal_skill import TerminalSkill
    from .git_skill import GitSkill
    from .web_research_skill import WebResearchSkill
    from .system_skill import SystemSkill
    from .file_upload_skill import FileUploadSkill
except ImportError:
    from app.skills.skill_base import BaseSkill, SkillTool, SkillRegistry, skills_registry
    from app.skills.coding_skill import CodingSkill
    from app.skills.terminal_skill import TerminalSkill
    from app.skills.git_skill import GitSkill
    from app.skills.web_research_skill import WebResearchSkill
    from app.skills.system_skill import SystemSkill
    from app.skills.file_upload_skill import FileUploadSkill

# Automatically register built-in default skills
skills_registry.register(CodingSkill())
skills_registry.register(TerminalSkill())
skills_registry.register(GitSkill())
skills_registry.register(WebResearchSkill())
skills_registry.register(SystemSkill())
skills_registry.register(FileUploadSkill())

__all__ = [
    "BaseSkill",
    "SkillTool",
    "SkillRegistry",
    "skills_registry",
    "CodingSkill",
    "TerminalSkill",
    "GitSkill",
    "WebResearchSkill",
    "SystemSkill",
    "FileUploadSkill",
]
