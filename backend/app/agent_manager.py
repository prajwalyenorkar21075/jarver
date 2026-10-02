"""Agent Manager — manages all 30 JARVIS agents.

Each agent has: clear responsibility, input/output, tools, permissions,
memory access, error handling, retry/recovery, execution status, logging,
and communication with the central orchestrator.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable, Optional

from .core.execution import ExecutionStatus, ExecutionResult, RetryPolicy
from .core.error_recovery import get_recovery_engine
from .core.permissions import get_permission_manager, PermissionLevel
from .core.event_bus import get_event_bus, EventType

logger = logging.getLogger("jarvis.agent_manager")


class AgentState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


@dataclass
class AgentDefinition:
    id: str
    name: str
    description: str
    category: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    tools: list[str] = field(default_factory=list)
    permission_level: PermissionLevel = PermissionLevel.LOW
    memory_access: bool = False
    max_retries: int = 3
    timeout_seconds: float = 60.0
    state: AgentState = AgentState.IDLE
    execution_count: int = 0
    error_count: int = 0
    last_execution: float | None = None
    handler: Callable | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tools": self.tools,
            "permission_level": self.permission_level.value,
            "memory_access": self.memory_access,
            "state": self.state.value,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "last_execution": self.last_execution,
        }


class AgentManager:
    def __init__(self):
        self._agents: dict[str, AgentDefinition] = {}
        self._recovery = get_recovery_engine()
        self._permissions = get_permission_manager()
        self._event_bus = get_event_bus()
        self._register_all_agents()
        logger.info(f"[AGENT_MANAGER] Initialized with {len(self._agents)} agents")

    def _register_all_agents(self):
        agents = [
            AgentDefinition(id="conversation_agent", name="Conversation Agent",
                description="Handles general conversation and natural language responses",
                category="core", tools=["llm_call"], permission_level=PermissionLevel.LOW),
            AgentDefinition(id="research_agent", name="Research Agent",
                description="Performs web searches and deep research on topics",
                category="core", tools=["web_search", "http_request", "knowledge_search"],
                permission_level=PermissionLevel.LOW, memory_access=True),
            AgentDefinition(id="coding_agent", name="Coding Agent",
                description="Handles code generation, debugging, and execution",
                category="core", tools=["code_interpreter", "file_read", "file_write", "shell_exec"],
                permission_level=PermissionLevel.MEDIUM),
            AgentDefinition(id="app_controller", name="Application Controller",
                description="Opens, closes, and controls desktop applications",
                category="system", tools=["app_open", "app_close", "app_control"],
                permission_level=PermissionLevel.MEDIUM),
            AgentDefinition(id="media_controller", name="Media Controller",
                description="Controls media playback — YouTube, music, video",
                category="system", tools=["browser_navigate", "browser_click", "browser_search"],
                permission_level=PermissionLevel.MEDIUM),
            AgentDefinition(id="file_manager", name="File Manager",
                description="Manages files and folders — create, read, write, delete, organize",
                category="system", tools=["file_read", "file_write", "file_delete", "folder_create"],
                permission_level=PermissionLevel.MEDIUM),
            AgentDefinition(id="knowledge_agent", name="Knowledge Agent",
                description="Queries robotics and Indian knowledge bases",
                category="knowledge", tools=["knowledge_search", "knowledge_explain"],
                permission_level=PermissionLevel.LOW, memory_access=True),
            AgentDefinition(id="vedic_knowledge_agent", name="Vedic Knowledge Agent",
                description="Answers questions on Vedic literature, philosophy, and Indic knowledge using local corpus with web fallback",
                category="knowledge", tools=["vedic_query", "vedic_explain", "vedic_compare", "vedic_concept", "vedic_ingest"],
                permission_level=PermissionLevel.LOW, memory_access=True),
            AgentDefinition(id="formatter_agent", name="Formatter Agent",
                description="Formats responses for display and TTS output",
                category="core", tools=[], permission_level=PermissionLevel.LOW),
            AgentDefinition(id="verifier_agent", name="Verifier Agent",
                description="Verifies execution results and system state",
                category="core", tools=["status_check", "system_info"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="memory_agent", name="Memory Agent",
                description="Manages adaptive memory — stores, retrieves, learns from history",
                category="memory", tools=["memory_store", "memory_retrieve", "memory_search"],
                permission_level=PermissionLevel.LOW, memory_access=True),
            AgentDefinition(id="learning_agent", name="Learning Agent",
                description="Learns from successes and failures, adapts behavior",
                category="memory", tools=["memory_store", "memory_retrieve", "pattern_detect"],
                permission_level=PermissionLevel.LOW, memory_access=True),
            AgentDefinition(id="planner_agent", name="Planner Agent",
                description="Breaks complex tasks into executable steps",
                category="planning", tools=["think", "task_create"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="task_manager_agent", name="Task Manager Agent",
                description="Tracks task progress, manages priorities and dependencies",
                category="planning", tools=["task_create", "task_update", "task_list"],
                permission_level=PermissionLevel.LOW, memory_access=True),
            AgentDefinition(id="vision_agent", name="Vision Agent",
                description="Processes camera input for scene understanding",
                category="vision", tools=["camera_capture", "image_process"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="object_detection_agent", name="Object Detection Agent",
                description="Detects and classifies objects in camera feed",
                category="vision", tools=["camera_capture", "object_detect", "yolo_infer"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="tracking_agent", name="Tracking Agent",
                description="Tracks objects across video frames",
                category="vision", tools=["camera_capture", "object_track"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="mapping_agent", name="Mapping Agent",
                description="Builds semantic maps of the environment",
                category="robotics", tools=["sensor_read", "map_build", "slam_process"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="navigation_agent", name="Navigation Agent",
                description="Plans and executes navigation paths",
                category="robotics", tools=["path_plan", "navigate", "localize"],
                permission_level=PermissionLevel.MEDIUM),
            AgentDefinition(id="localization_agent", name="Localization Agent",
                description="Determines robot position in the environment",
                category="robotics", tools=["sensor_read", "localize", "imu_read"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="motion_planning_agent", name="Motion Planning Agent",
                description="Plans collision-free robot trajectories",
                category="robotics", tools=["trajectory_plan", "collision_check", "kinematics_solve"],
                permission_level=PermissionLevel.MEDIUM),
            AgentDefinition(id="kinematics_agent", name="Kinematics Agent",
                description="Solves forward/inverse kinematics for robot arms",
                category="robotics", tools=["fk_solve", "ik_solve", "joint_control"],
                permission_level=PermissionLevel.MEDIUM),
            AgentDefinition(id="trajectory_agent", name="Trajectory Agent",
                description="Executes and monitors robot trajectories",
                category="robotics", tools=["trajectory_execute", "trajectory_monitor"],
                permission_level=PermissionLevel.MEDIUM),
            AgentDefinition(id="error_detection_agent", name="Error Detection Agent",
                description="Monitors for errors and anomalies across all systems",
                category="recovery", tools=["system_monitor", "log_analyze", "anomaly_detect"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="recovery_agent", name="Recovery Agent",
                description="Executes recovery strategies for failed operations",
                category="recovery", tools=["retry", "fallback", "system_restart"],
                permission_level=PermissionLevel.HIGH),
            AgentDefinition(id="tool_manager_agent", name="Tool Manager Agent",
                description="Manages the dynamic tool registry — register, discover, execute tools",
                category="tools", tools=["tool_register", "tool_list", "tool_execute"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="plugin_agent", name="Plugin Agent",
                description="Manages plugin lifecycle — install, enable, disable, update",
                category="tools", tools=["plugin_install", "plugin_enable", "plugin_disable"],
                permission_level=PermissionLevel.MEDIUM),
            AgentDefinition(id="security_agent", name="Security Agent",
                description="Enforces permissions, scans for threats, manages access control",
                category="security", tools=["permission_check", "secret_scan", "pii_scan"],
                permission_level=PermissionLevel.HIGH),
            AgentDefinition(id="audit_agent", name="Audit Agent",
                description="Maintains audit logs for all significant actions",
                category="security", tools=["log_write", "log_query", "report_generate"],
                permission_level=PermissionLevel.LOW, memory_access=True),
            AgentDefinition(id="biometric_agent", name="Biometric Agent",
                description="Handles face detection and user authentication",
                category="security", tools=["face_detect", "face_recognize", "face_enroll"],
                permission_level=PermissionLevel.HIGH),
            AgentDefinition(id="monitoring_agent", name="Monitoring Agent",
                description="Collects and reports system health metrics",
                category="monitoring", tools=["system_info", "cpu_monitor", "ram_monitor", "service_check"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="diagnostics_agent", name="Diagnostics Agent",
                description="Runs diagnostic tests and reports system health",
                category="monitoring", tools=["diagnostic_run", "health_check", "test_execute"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="status_agent", name="Status Agent",
                description="Provides real-time status of all JARVIS subsystems",
                category="monitoring", tools=["status_query", "subsystem_check"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="remote_control_agent", name="Remote Control Agent",
                description="Handles remote commands with authentication and authorization",
                category="remote", tools=["remote_receive", "remote_respond", "auth_verify"],
                permission_level=PermissionLevel.HIGH),
            AgentDefinition(id="communication_agent", name="Communication Agent",
                description="Manages WebSocket and API communication channels",
                category="remote", tools=["ws_send", "ws_receive", "api_respond"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="stt_agent", name="STT Agent",
                description="Handles speech-to-text processing",
                category="voice", tools=["stt_process", "audio_capture"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="tts_agent", name="TTS Agent",
                description="Handles text-to-speech synthesis",
                category="voice", tools=["tts_synthesize", "audio_play"],
                permission_level=PermissionLevel.LOW),
            AgentDefinition(id="industrial_agent", name="Industrial Automation Agent",
                description="Reads PLC/SCADA tags, alarms and machine state (READ only by default)",
                category="industrial", tools=["industrial.read_device", "industrial.read_tag", "industrial.state", "industrial.alarms"],
                permission_level=PermissionLevel.MEDIUM),
            AgentDefinition(id="plc_agent", name="PLC Program Agent",
                description="Analyzes PLC programs, generates drafts, test cases and documentation",
                category="industrial", tools=["plc.analyze", "plc.test_cases", "plc.documentation", "plc.draft"],
                permission_level=PermissionLevel.LOW, memory_access=True),
            AgentDefinition(id="maintenance_agent", name="Predictive Maintenance Agent",
                description="Analyzes stored sensor data for anomalies, trends and equipment health",
                category="industrial", tools=["maintenance.analyze", "maintenance.health", "maintenance.series"],
                permission_level=PermissionLevel.LOW, memory_access=True),
            AgentDefinition(id="cell_inspector_agent", name="Robot Cell Inspector",
                description="Correlates robot, PLC, vision, alarm and security state into one verified report",
                category="industrial", tools=["cell.inspect", "twin.compare"],
                permission_level=PermissionLevel.LOW, memory_access=True),
        ]

        for agent_def in agents:
            self._agents[agent_def.id] = agent_def

    def register_handler(self, agent_id: str, handler: Callable):
        if agent_id in self._agents:
            self._agents[agent_id].handler = handler
            logger.info(f"[AGENT_MANAGER] Custom handler registered for {agent_id}")
        else:
            logger.warning(f"[AGENT_MANAGER] Agent {agent_id} not found")

    async def execute_agent(
        self,
        agent_id: str,
        args: dict[str, Any] | None = None,
        task_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        result = ExecutionResult(operation=f"agent:{agent_id}")
        agent = self._agents.get(agent_id)

        if not agent:
            result.fail(error=f"Agent '{agent_id}' not found")
            return result

        if agent.state == AgentState.DISABLED:
            result.fail(error=f"Agent '{agent_id}' is disabled")
            return result

        if agent.handler is None:
            result.fail(error=f"Agent '{agent_id}' has no executable handler")
            return result

        args = args or {}
        agent.state = AgentState.RUNNING
        agent.execution_count += 1
        agent.last_execution = time.time()

        await self._event_bus.emit(EventType.AGENT_STARTED, {
            "agent_id": agent_id,
            "task_id": task_id,
            "args": args,
        }, "agent_manager")

        policy = RetryPolicy(max_retries=agent.max_retries)

        async def run_agent():
            if agent.handler:
                return await agent.handler(args, context)
            raise RuntimeError(f"No handler for agent {agent_id}")

        exec_result = await self._recovery.execute_with_recovery(
            agent_id, run_agent, policy
        )

        if exec_result.status == ExecutionStatus.SUCCESS:
            result.succeed(result=exec_result.result)
            agent.state = AgentState.IDLE
        else:
            result.fail(error=exec_result.error or "Agent execution failed")
            agent.state = AgentState.ERROR
            agent.error_count += 1

        await self._event_bus.emit(
            EventType.AGENT_COMPLETED if result.status == ExecutionStatus.SUCCESS else EventType.AGENT_FAILED,
            {"agent_id": agent_id, "task_id": task_id, "status": result.status.value},
            "agent_manager",
        )

        return result

    def get_agent(self, agent_id: str) -> AgentDefinition | None:
        return self._agents.get(agent_id)

    def list_agents(self, category: str | None = None) -> list[dict[str, Any]]:
        agents = self._agents.values()
        if category:
            agents = [a for a in agents if a.category == category]
        return [a.to_dict() for a in agents]

    def get_agents_by_category(self) -> dict[str, list[dict[str, Any]]]:
        categories: dict[str, list[dict[str, Any]]] = {}
        for agent in self._agents.values():
            cat = agent.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(agent.to_dict())
        return categories

    def get_stats(self) -> dict[str, Any]:
        total = len(self._agents)
        idle = sum(1 for a in self._agents.values() if a.state == AgentState.IDLE)
        running = sum(1 for a in self._agents.values() if a.state == AgentState.RUNNING)
        error = sum(1 for a in self._agents.values() if a.state == AgentState.ERROR)
        disabled = sum(1 for a in self._agents.values() if a.state == AgentState.DISABLED)
        total_executions = sum(a.execution_count for a in self._agents.values())
        total_errors = sum(a.error_count for a in self._agents.values())
        return {
            "total_agents": total,
            "idle": idle,
            "running": running,
            "error": error,
            "disabled": disabled,
            "total_executions": total_executions,
            "total_errors": total_errors,
            "error_rate": round(total_errors / total_executions * 100, 1) if total_executions > 0 else 0.0,
        }


_agent_manager: AgentManager | None = None


def get_agent_manager() -> AgentManager:
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
        _register_vedic_knowledge_handler(_agent_manager)
        _register_app_controller_handler(_agent_manager)
        _register_capability_handlers(_agent_manager)
    return _agent_manager


def _register_capability_handlers(manager: AgentManager):
    """Wire the new domain services into the orchestrator agent pool.

    Every handler reports real-vs-simulated honestly and never fabricates data.
    """

    async def execute_industrial(args: dict, context: dict | None = None):
        from .industrial_service import get_industrial_service
        from .core.execution_policy import ActionClass, get_execution_policy
        svc = get_industrial_service()
        op = (args or {}).get("op", "read")
        device_id = (args or {}).get("device_id", "")
        tag = (args or {}).get("tag", "")
        text = (args or {}).get("text", "")
        target = device_id or tag or text
        if op == "read" and device_id and tag:
            policy = get_execution_policy().evaluate(
                "read_plc_tag", agent="industrial_agent",
                tool="industrial.read_tag", target=f"{device_id}.{tag}",
                action_class=ActionClass.READ)
            if policy.decision == "DENY":
                raise RuntimeError(policy.decision_reason)
            result = svc.read_tag(device_id, tag)
            if not result.get("success"):
                raise RuntimeError(result.get("error", "PLC tag read failed"))
            device = svc.get_device(device_id)
            result["simulated"] = bool(device and device.simulated)
            result["reply"] = (
                f"{tag} on {device_id} reads {result['reading']['value']}"
                f"{result['reading'].get('unit', '')}, sir."
                + (" (simulated device)" if result["simulated"] else ""))
            return result
        if op in ("read", "state") and device_id:
            result = svc.machine_state(device_id)
            if not result.get("success"):
                raise RuntimeError(result.get("error", "machine state unavailable"))
            device = svc.get_device(device_id)
            result["simulated"] = bool(device and device.simulated)
            result["reply"] = f"{device_id} state is {result['state']}, sir."
            return result
        # Default: list devices and their status
        devices = svc.list_devices()
        return {
            "reply": (f"{len(devices)} industrial devices registered, "
                        f"{sum(1 for d in devices if d.get('address'))} configured with addresses, sir."),
            "devices": devices, "protocols": svc.protocol_status(),
            "alarms": svc.active_alarms(), "success": True,
        }

    async def execute_plc(args: dict, context: dict | None = None):
        from .plc_analyzer import get_plc_analyzer
        analyzer = get_plc_analyzer()
        source = (args or {}).get("source", "")
        path = (args or {}).get("path", "")
        if path:
            result = analyzer.analyze_file(path)
        elif source:
            result = analyzer.analyze(source, (args or {}).get("filename", ""))
        else:
            raise RuntimeError("plc_agent needs 'source' text or a 'path' to a PLC program file")
        if not result.get("supported", True):
            raise RuntimeError(result.get("error", "PLC program not supported"))
        result["reply"] = analyzer.explain(result)
        result["success"] = True
        return result

    async def execute_maintenance(args: dict, context: dict | None = None):
        from .predictive_maintenance import get_maintenance_engine
        engine = get_maintenance_engine()
        device_id = (args or {}).get("device_id")
        result = engine.analyze(device_id)
        if not result.get("success"):
            raise RuntimeError(result.get("error", "No maintenance data available"))
        health = result.get("equipment_health", {})
        summary = "; ".join(
            f"{d}: {h.get('status')} (score {h.get('health_score')})"
            if h.get("health_score") is not None
            else f"{d}: {h.get('status')} — {h.get('message', '')[:80]}"
            for d, h in health.items()) or "no devices with data"
        result["reply"] = (
            f"Analyzed {result['signals_analyzed']} sensor signals, sir. "
            f"{len(result.get('alerts', []))} alerts. Health — {summary}.")
        return result

    async def execute_cell_inspector(args: dict, context: dict | None = None):
        from .digital_twin import get_cell_inspector
        report = await get_cell_inspector().inspect(
            cell=(args or {}).get("cell", "robot_cell_1"),
            run_vision=bool((args or {}).get("run_vision", False)))
        report["reply"] = (
            f"Cell {report['cell']}: {report['verdict']}, sir. "
            f"{report['finding_count']} findings across robot, PLC, vision, alarms and security.")
        report["success"] = True
        return report

    async def execute_security(args: dict, context: dict | None = None):
        """Defensive security status through the real cybersecurity module."""
        from .cybersecurity import get_security_orchestrator, get_alert_manager, get_security_db
        orch = get_security_orchestrator()
        alert_mgr = get_alert_manager()
        summary = alert_mgr.get_alert_summary()
        stats = get_security_db().get_security_stats()
        open_vulns = sum(1 for v in get_security_db().get_vulnerabilities(limit=1000)
                         if v.get("status") == "open") if hasattr(
            get_security_db(), "get_vulnerabilities") else 0
        text = (args or {}).get("text", "")
        if any(w in text.lower() for w in ["port scan", "penetration", "reconnaissance",
                                            "security assessment", "authorized test"]):
            return {
                "reply": ("Authorized security testing needs a defined scope first, sir. "
                            "Create a test scope in the Security panel with your target listed, "
                            "then I will run reconnaissance and checks inside that scope only."),
                "requires_scope": True, "success": True,
            }
        return {
            "reply": (f"Security posture: {summary.get('total_active', 0)} active alerts, "
                        f"orchestrator status {orch.get_orchestrator_stats() if hasattr(orch, 'get_orchestrator_stats') else 'operational'}, sir."),
            "success": True, "alert_summary": summary, "security_stats": stats,
            "open_vulnerabilities": open_vulns,
        }

    async def execute_vision(args: dict, context: dict | None = None):
        from .vision_service import get_vision_service
        service = get_vision_service()
        frame = await service.process_frame()
        data = frame.to_dict()
        stats = service.get_stats()
        data["simulated"] = stats.get("simulation_mode", True)
        detections = data.get("detections", [])
        if detections:
            names = ", ".join(f"{d['class_name']} ({d['confidence']:.0%})" for d in detections[:5])
            data["reply"] = f"Camera shows: {names}, sir." + (" (simulated feed)" if data["simulated"] else "")
        else:
            data["reply"] = "No objects detected in the current frame, sir."
        data["success"] = True
        return data

    async def execute_navigation(args: dict, context: dict | None = None):
        from .robotics_service import get_robotics_service
        service = get_robotics_service()
        status = service.get_full_status()
        state = status.get("robot_state", {})
        pose = state.get("pose", {})
        status["reply"] = (
            f"Robot is {state.get('mode', 'unknown')}, battery "
            f"{state.get('battery_level', '?')} percent, at "
            f"x {pose.get('x', 0)}, y {pose.get('y', 0)}, sir. (simulation)"
            if status.get("simulation") else
            f"Robot is {state.get('mode', 'unknown')}, battery "
            f"{state.get('battery_level', '?')} percent, sir.")
        status["simulated"] = status.get("simulation", True)
        status["success"] = True
        return status

    manager.register_handler("industrial_agent", execute_industrial)
    manager.register_handler("plc_agent", execute_plc)
    manager.register_handler("maintenance_agent", execute_maintenance)
    manager.register_handler("cell_inspector_agent", execute_cell_inspector)
    manager.register_handler("security_agent", execute_security)
    manager.register_handler("object_detection_agent", execute_vision)
    manager.register_handler("navigation_agent", execute_navigation)
    for agent_id in ("industrial_agent", "plc_agent", "maintenance_agent", "cell_inspector_agent",
                     "security_agent", "object_detection_agent", "navigation_agent"):
        agent = manager.get_agent(agent_id)
        if agent:
            agent.max_retries = 0  # these handlers read/analyze; never auto-repeat side effects


def _register_vedic_knowledge_handler(manager: AgentManager):
    try:
        from .vedic_knowledge_agent import execute_vedic_knowledge_agent
        manager.register_handler("vedic_knowledge_agent", execute_vedic_knowledge_agent)
    except ImportError as e:
        logger.warning(f"[AGENT_MANAGER] Could not register Vedic Knowledge Agent handler: {e}")


def _register_app_controller_handler(manager: AgentManager):
    """Thin adapter delegating app/system control to the proven agent_brain executor."""

    async def execute_app_controller(args: dict, context: dict | None = None):
        from .agent_brain import parse_and_execute_multitask

        text = (args or {}).get("text") or (args or {}).get("command") or ""
        if not text.strip():
            raise RuntimeError("app_controller requires a non-empty 'text' command")

        history = (context or {}).get("conversation_history") or []
        res = await parse_and_execute_multitask(text, history)

        if res.get("requires_confirmation"):
            # The confirmation gate itself was raised — return it so callers
            # can present the gate; the protected action has NOT executed yet.
            return res
        if not res.get("success"):
            raise RuntimeError(res.get("reply") or "System action failed")
        return res

    manager.register_handler("app_controller", execute_app_controller)
    # Executing twice could repeat real side effects (launch apps, prompt confirmation gates)
    agent = manager.get_agent("app_controller")
    if agent:
        agent.max_retries = 0
