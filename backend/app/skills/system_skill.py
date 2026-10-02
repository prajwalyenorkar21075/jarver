from typing import Any, Dict
from .skill_base import BaseSkill, SkillTool

try:
    from app.system_controller import launch_app, open_url
    from app.agent_brain import get_system_telemetry
except ImportError:
    from system_controller import launch_app, open_url
    from agent_brain import get_system_telemetry


class SystemSkill(BaseSkill):
    id = "system_automation"
    display_name = "Desktop & Windows Hardware Supervisor"
    description = "Control desktop applications, browser windows, audio volume, system power, and real-time hardware telemetry."
    icon = "cpu-chip"

    def _setup_tools(self):
        self.tools.append(
            SkillTool(
                name="system_telemetry",
                description="Get live hardware CPU, RAM, Disk, Battery, and process metrics.",
                parameters={"type": "object", "properties": {}},
                handler=self.tool_telemetry,
            )
        )
        self.tools.append(
            SkillTool(
                name="launch_application",
                description="Launch or focus a Windows desktop application (e.g. 'notepad', 'calc', 'chrome', 'code').",
                parameters={
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "Name or executable of the application"},
                    },
                    "required": ["app_name"],
                },
                handler=self.tool_launch_app,
            )
        )
        self.tools.append(
            SkillTool(
                name="open_browser_url",
                description="Open a web URL in the default system browser or Stark HUD panel.",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to open"},
                    },
                    "required": ["url"],
                },
                handler=self.tool_open_url,
            )
        )

    def tool_telemetry(self) -> Dict[str, Any]:
        return get_system_telemetry()

    def tool_launch_app(self, app_name: str) -> Dict[str, Any]:
        res = launch_app(app_name)
        return {"app": app_name, "success": bool(res)}

    def tool_open_url(self, url: str) -> Dict[str, Any]:
        res = open_url(url)
        return {"url": url, "success": bool(res)}

