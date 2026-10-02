"""Central JARVIS Orchestrator — ties together all subsystems.

Flow: User Input → Intent → Task Plan → Agent Selection → Tool Selection →
      Permission Check → Execution → Verification → Error Recovery →
      Memory Update → Response → TTS
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .core.execution import ExecutionStatus, ExecutionResult, RetryPolicy
from .core.error_recovery import get_recovery_engine
from .core.permissions import get_permission_manager, PermissionAction, PermissionLevel
from .core.event_bus import get_event_bus, EventType, Event

logger = logging.getLogger("jarvis.orchestrator")


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskState(str, Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    WAITING_PERMISSION = "WAITING_PERMISSION"


@dataclass
class TaskStep:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    agent: str = ""
    tool: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Any = None
    error: str | None = None
    verified: bool = False
    critical: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "agent": self.agent,
            "tool": self.tool,
            "args": self.args,
            "status": self.status.value,
            "result": str(self.result)[:200] if self.result else None,
            "error": self.error,
            "verified": self.verified,
            "critical": self.critical,
        }


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_input: str = ""
    intent: str = ""
    state: TaskState = TaskState.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    steps: list[TaskStep] = field(default_factory=list)
    result: Any = None
    response: str = ""
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    max_retries: int = 3
    timeout_seconds: float = 300.0
    permission_check_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_input": self.user_input,
            "intent": self.intent,
            "state": self.state.value,
            "priority": self.priority.value,
            "steps": [s.to_dict() for s in self.steps],
            "result": str(self.result)[:500] if self.result else None,
            "response": self.response,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class JarvisOrchestrator:
    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._task_history: list[Task] = []
        self._max_history = 100
        self._recovery = get_recovery_engine()
        self._permissions = get_permission_manager()
        self._event_bus = get_event_bus()
        self._agent_manager = None
        self._running = False
        logger.info("[ORCHESTRATOR] Central orchestrator initialized")

    def set_agent_manager(self, agent_manager):
        self._agent_manager = agent_manager

    async def can_handle(self, user_input: str) -> bool:
        """True only when a plan exists whose steps map to executable agent handlers."""
        try:
            intent = await self._classify_intent(user_input)
            steps = await self._create_plan(user_input, intent, None)
            return bool(steps)
        except Exception:
            return False

    async def process_input(self, user_input: str, context: dict[str, Any] | None = None) -> ExecutionResult:
        result = ExecutionResult(operation="process_input")
        result.status = ExecutionStatus.RUNNING

        task = Task(user_input=user_input, context=context or {})
        self._tasks[task.id] = task

        await self._event_bus.emit(EventType.USER_INPUT, {"input": user_input, "task_id": task.id}, "orchestrator")

        try:
            task.state = TaskState.PLANNING
            await self._plan_task(task, context)

            if not task.steps:
                task.state = TaskState.FAILED
                task.error = (
                    f"No executable capability is currently available for intent '{task.intent}'. "
                    "The required tool or agent handler is not implemented on this system."
                )
                result.fail(error=task.error)
                self._archive_task(task)
                await self._event_bus.emit(EventType.TASK_FAILED, {"task_id": task.id, "error": task.error}, "orchestrator")
                return result

            task.state = TaskState.EXECUTING
            await self._execute_task(task)

            if task.state == TaskState.WAITING_PERMISSION:
                result.fail(error=f"Task {task.id} is waiting for user permission confirmation")
                self._archive_task(task)
                return result

            task.state = TaskState.VERIFYING
            verified = await self._verify_task(task)

            if verified:
                task.state = TaskState.COMPLETED
                task.completed_at = time.time()
                result.succeed(result=task.to_dict())
                result.metadata["step_results"] = [s.result for s in task.steps if s.result is not None]
                await self._event_bus.emit(EventType.TASK_COMPLETED, {"task_id": task.id}, "orchestrator")
            else:
                task.state = TaskState.RECOVERING
                recovered = await self._recover_task(task)
                if recovered:
                    task.state = TaskState.COMPLETED
                    task.completed_at = time.time()
                    result.succeed(result=task.to_dict())
                    result.metadata["step_results"] = [s.result for s in task.steps if s.result is not None]
                else:
                    task.state = TaskState.FAILED
                    task.error = "Task verification failed and recovery was not possible"
                    result.fail(error=task.error)
                    await self._event_bus.emit(EventType.TASK_FAILED, {"task_id": task.id, "error": task.error}, "orchestrator")

        except Exception as e:
            task.state = TaskState.FAILED
            task.error = str(e)
            task.completed_at = time.time()
            result.fail(error=str(e))
            logger.error(f"[ORCHESTRATOR] Task {task.id} failed: {e}", exc_info=True)
            await self._event_bus.emit(EventType.TASK_FAILED, {"task_id": task.id, "error": str(e)}, "orchestrator")

        self._archive_task(task)
        return result

    async def _plan_task(self, task: Task, context: dict[str, Any] | None = None):
        logger.info(f"[ORCHESTRATOR] Planning task {task.id}: {task.user_input[:80]}")

        intent = await self._classify_intent(task.user_input)
        task.intent = intent

        steps = await self._create_plan(task.user_input, intent, context)
        task.steps = steps

        logger.info(f"[ORCHESTRATOR] Plan: {len(steps)} steps, intent={intent}")

    async def _classify_intent(self, user_input: str) -> str:
        mapped = "general_conversation"
        try:
            from app.intent_classification import classify_intent
            result = classify_intent(user_input)
            mapped = self._map_intent_enum_to_string(result.intent)
        except Exception:
            mapped = self._simple_intent_classification(user_input)

        # The keyword classifier is more specific than the ML classifier for
        # low-confidence/unknown results (e.g. Vedic terms, "open notepad").
        if mapped in ("general_conversation", "knowledge"):
            fallback = self._simple_intent_classification(user_input)
            if fallback != "general_conversation":
                return fallback
        return mapped

    def _map_intent_enum_to_string(self, intent) -> str:
        """Map Intent enum values to orchestrator plan template keys."""
        intent_str = intent.value if hasattr(intent, 'value') else str(intent)
        mapping = {
            "system_control": "app_control",
            "app_launch": "app_control",
            "app_close": "app_control",
            "web_search": "search",
            "information_query": "knowledge",
            "navigation": "robotics",
            "file_operation": "file_operation",
            "file_create": "file_operation",
            "file_delete": "file_operation",
            "file_read": "file_operation",
            "file_write": "file_operation",
            "code_generation": "coding",
            "code_editing": "coding",
            "code_explanation": "coding",
            "media_control": "media_control",
            "robotics": "robotics",
            "monitoring": "monitoring",
            "knowledge": "knowledge",
            "vedic_knowledge": "vedic_knowledge",
            "conversation": "general_conversation",
            "unknown": "general_conversation",
            "ethical_hacking": "ethical_hacking",
            "cybersecurity": "cybersecurity",
            "industrial": "industrial",
            "plc": "plc",
            "maintenance": "maintenance",
            "cell_inspection": "cell_inspection",
            "vision": "vision_task",
            "cad_modeling": "cad",
        }
        # New domain intents from intent_classification.py map directly.
        if intent_str in ("industrial", "plc", "maintenance", "cell_inspection", "vision",
                          "ethical_hacking", "cybersecurity", "cad_modeling"):
            direct = {"industrial": "industrial", "plc": "plc", "maintenance": "maintenance",
                      "cell_inspection": "cell_inspection", "vision": "vision_task",
                      "ethical_hacking": "ethical_hacking", "cybersecurity": "cybersecurity",
                      "cad_modeling": "cad"}
            return direct[intent_str]
        return mapping.get(intent_str, "general_conversation")

    def _simple_intent_classification(self, text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ["open", "launch", "start"]):
            return "app_control"
        if any(w in text_lower for w in ["search", "find", "look up"]):
            return "search"
        if any(w in text_lower for w in ["play", "youtube", "music", "song"]):
            return "media_control"
        if any(w in text_lower for w in ["file", "folder", "directory", "create", "delete"]):
            return "file_operation"
        if any(w in text_lower for w in ["inspect the robot cell", "robot cell", "cell inspection",
                                          "inspect the cell"]):
            return "cell_inspection"
        if any(w in text_lower for w in ["robot", "move", "navigate", "go to"]):
            return "robotics"
        if any(w in text_lower for w in ["plc", "ladder", "structured text", "hmi", "scada",
                                          "modbus", "opc ua", "opcua", "mqtt", "conveyor",
                                          "industrial", "machine state", "tag"]):
            return "industrial"
        if any(w in text_lower for w in ["predictive maintenance", "equipment health",
                                          "vibration", "anomaly", "sensor trend"]):
            return "maintenance"
        if any(w in text_lower for w in ["scan for vulnerabilities", "vulnerability scan",
                                          "threat scan", "security scan", "security status",
                                          "check security", "malware", "phishing"]):
            return "cybersecurity"
        if any(w in text_lower for w in ["port scan", "penetration test", "authorized test",
                                          "security assessment", "reconnaissance"]):
            return "ethical_hacking"
        if any(w in text_lower for w in ["camera", "detect object", "what do you see",
                                          "inspect the object", "vision", "yolo"]):
            return "vision_task"
        if any(w in text_lower for w in ["status", "check", "monitor", "diagnose"]):
            return "monitoring"
        if any(w in text_lower for w in ["atman", "brahman", "dharma", "karma", "moksha", "yoga", "jnana", "bhakti",
                                          "upanishad", "vedas", "gita", "bhagavad", "ramayana", "mahabharata", "purana",
                                          "vedanga", "shiksha", "kalpa", "vyakarana", "nirukta", "chandas", "jyotisha",
                                          "आत्मा", "ब्रह्म", "धर्म", "कर्म", "मोक्ष", "योग", "ज्ञान", "भक्ति",
                                          "उपनिषद", "गीता", "रामायण", "महाभारत", "पुराण", "वेद"]):
            return "vedic_knowledge"
        if any(w in text_lower for w in ["explain", "learn", "what is", "how to"]):
            return "knowledge"
        if any(w in text_lower for w in ["code", "program", "debug", "fix"]):
            return "coding"
        return "general_conversation"

    async def _create_plan(self, user_input: str, intent: str, context: dict[str, Any] | None) -> list[TaskStep]:
        plan_templates = {
            "app_control": [
                TaskStep(name="execute_action", agent="app_controller"),
            ],
            "search": [
                TaskStep(name="execute_search", agent="research_agent"),
            ],
            "media_control": [
                TaskStep(name="play_media", agent="app_controller"),
            ],
            "file_operation": [
                TaskStep(name="execute_file_op", agent="app_controller"),
            ],
            "robotics": [
                TaskStep(name="check_robot_status", agent="navigation_agent"),
            ],
            "monitoring": [
                TaskStep(name="gather_status", agent="monitoring_agent"),
            ],
            "knowledge": [
                TaskStep(name="query_knowledge", agent="knowledge_agent"),
            ],
            "vedic_knowledge": [
                TaskStep(name="query_vedic_knowledge", agent="vedic_knowledge_agent"),
            ],
            "coding": [
                TaskStep(name="execute_code", agent="coding_agent"),
            ],
            "industrial": [
                TaskStep(name="read_industrial_state", agent="industrial_agent"),
            ],
            "plc": [
                TaskStep(name="analyze_plc", agent="plc_agent"),
            ],
            "maintenance": [
                TaskStep(name="analyze_maintenance", agent="maintenance_agent"),
            ],
            "cell_inspection": [
                TaskStep(name="inspect_robot_cell", agent="cell_inspector_agent"),
            ],
            "cybersecurity": [
                TaskStep(name="security_status", agent="security_agent"),
            ],
            "ethical_hacking": [
                TaskStep(name="security_assessment", agent="security_agent"),
            ],
            "vision_task": [
                TaskStep(name="process_frame", agent="object_detection_agent"),
            ],
            "cad": [
                TaskStep(name="generate_response", agent="conversation_agent"),
            ],
            "general_conversation": [
                TaskStep(name="generate_response", agent="conversation_agent"),
            ],
        }

        steps = plan_templates.get(intent, [TaskStep(name="process", agent="conversation_agent")])
        for i, step in enumerate(steps):
            step.name = f"step_{i + 1}_{step.name}"
            # Pass the user's command to adapter-style agents
            step.args.setdefault("text", user_input)
            step.args.setdefault("query", user_input)

        # Only keep steps whose agents actually have executable handlers.
        if self._agent_manager:
            steps = [
                s for s in steps
                if (a := self._agent_manager.get_agent(s.agent)) and a.handler is not None
            ]
        return steps

    async def _execute_task(self, task: Task):
        logger.info(f"[ORCHESTRATOR] Executing task {task.id} ({len(task.steps)} steps)")

        for step in task.steps:
            if step.status == ExecutionStatus.SUCCESS:
                continue

            perm_check = self._permissions.check_permission(
                operation=step.name,
                agent=step.agent,
                tool=step.tool,
            )

            if perm_check.action == PermissionAction.REQUIRE_CONFIRMATION:
                task.state = TaskState.WAITING_PERMISSION
                task.permission_check_id = perm_check.id
                await self._event_bus.emit(EventType.PERMISSION_REQUESTED, {
                    "task_id": task.id,
                    "check_id": perm_check.id,
                    "operation": step.name,
                    "level": perm_check.level.value,
                }, "orchestrator")
                return

            if perm_check.action == PermissionAction.REQUIRE_AUTH:
                task.state = TaskState.WAITING_PERMISSION
                task.permission_check_id = perm_check.id
                await self._event_bus.emit(EventType.PERMISSION_REQUESTED, {
                    "task_id": task.id,
                    "check_id": perm_check.id,
                    "operation": step.name,
                    "level": perm_check.level.value,
                    "auth_required": True,
                }, "orchestrator")
                return

            step.status = ExecutionStatus.RUNNING
            await self._event_bus.emit(EventType.AGENT_STARTED, {
                "task_id": task.id,
                "step_id": step.id,
                "agent": step.agent,
            }, "orchestrator")

            try:
                if self._agent_manager:
                    step_result = await self._agent_manager.execute_agent(
                        step.agent, step.args, task_id=task.id, context=task.context
                    )
                    step.result = step_result.result
                    step.status = step_result.status
                    if step_result.error:
                        step.error = step_result.error
                else:
                    step.status = ExecutionStatus.FAILED
                    step.error = f"No agent manager available to execute step '{step.name}' (agent={step.agent})"
                    logger.error(f"[ORCHESTRATOR] {step.error}")

                if step.status == ExecutionStatus.SUCCESS:
                    step.verified = True
                    await self._event_bus.emit(EventType.AGENT_COMPLETED, {
                        "task_id": task.id,
                        "step_id": step.id,
                        "agent": step.agent,
                    }, "orchestrator")
                else:
                    await self._event_bus.emit(EventType.AGENT_FAILED, {
                        "task_id": task.id,
                        "step_id": step.id,
                        "agent": step.agent,
                        "error": step.error,
                    }, "orchestrator")
                    if step.critical:
                        return

            except Exception as e:
                step.status = ExecutionStatus.FAILED
                step.error = str(e)
                logger.error(f"[ORCHESTRATOR] Step {step.name} failed: {e}")
                await self._event_bus.emit(EventType.ERROR_DETECTED, {
                    "task_id": task.id,
                    "step_id": step.id,
                    "error": str(e),
                }, "orchestrator")
                if step.critical:
                    return

    async def _verify_task(self, task: Task) -> bool:
        for step in task.steps:
            if step.critical and step.status != ExecutionStatus.SUCCESS:
                return False
        return True

    async def _recover_task(self, task: Task) -> bool:
        logger.info(f"[ORCHESTRATOR] Attempting recovery for task {task.id}")

        for step in task.steps:
            if step.status == ExecutionStatus.FAILED and step.critical:
                error = step.error or "Unknown error"
                policy = RetryPolicy(max_retries=2)

                async def retry_step():
                    if self._agent_manager:
                        return await self._agent_manager.execute_agent(
                            step.agent, step.args, task_id=task.id, context=task.context
                        )
                    return ExecutionResult(
                        operation=f"retry_{step.name}",
                        status=ExecutionStatus.FAILED,
                        error="No agent manager available; retry cannot execute the step",
                    )

                recovery_result = await self._recovery.execute_with_recovery(
                    f"recover_{step.name}",
                    retry_step,
                    policy,
                )

                if recovery_result.status == ExecutionStatus.SUCCESS:
                    step.status = ExecutionStatus.SUCCESS
                    step.result = recovery_result.result
                    step.verified = True
                    step.recovery_applied = True if hasattr(step, 'recovery_applied') else True
                    await self._event_bus.emit(EventType.RECOVERY_APPLIED, {
                        "task_id": task.id,
                        "step_id": step.id,
                    }, "orchestrator")
                else:
                    await self._event_bus.emit(EventType.RECOVERY_FAILED, {
                        "task_id": task.id,
                        "step_id": step.id,
                    }, "orchestrator")
                    return False

        # A task is only recovered when every critical step truly succeeded
        for step in task.steps:
            if step.critical and step.status != ExecutionStatus.SUCCESS:
                return False

        return True

    def _archive_task(self, task: Task):
        self._task_history.append(task)
        if len(self._task_history) > self._max_history:
            self._task_history = self._task_history[-self._max_history:]
        if task.id in self._tasks:
            del self._tasks[task.id]

    def confirm_permission(self, check_id: str, confirmed_by: str = "user") -> bool:
        return self._permissions.confirm_permission(check_id, confirmed_by)

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        task = self._tasks.get(task_id)
        if task:
            return task.to_dict()
        for t in reversed(self._task_history):
            if t.id == task_id:
                return t.to_dict()
        return None

    def get_active_tasks(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._tasks.values()]

    def get_task_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._task_history[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        total = len(self._task_history) + len(self._tasks)
        completed = sum(1 for t in self._task_history if t.state == TaskState.COMPLETED)
        failed = sum(1 for t in self._task_history if t.state == TaskState.FAILED)
        return {
            "active_tasks": len(self._tasks),
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "success_rate": round(completed / total * 100, 1) if total > 0 else 0.0,
            "recovery_stats": self._recovery.get_recovery_stats(),
            "permission_stats": self._permissions.get_stats(),
            "event_stats": self._event_bus.get_stats(),
        }


_orchestrator: JarvisOrchestrator | None = None


def get_orchestrator() -> JarvisOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = JarvisOrchestrator()
    return _orchestrator
