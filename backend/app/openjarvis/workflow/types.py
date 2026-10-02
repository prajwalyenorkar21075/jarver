"""Workflow type definitions."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(Enum):
    AGENT = "agent"
    TOOL = "tool"
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"
    TRANSFORM = "transform"


@dataclass
class WorkflowNode:
    id: str
    node_type: NodeType
    agent: str | None = None
    tools: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    condition_expr: str | None = None
    max_iterations: int = 10
    transform_expr: str | None = None


@dataclass
class WorkflowEdge:
    source: str
    target: str
    condition: str | None = None


@dataclass
class WorkflowStepResult:
    node_id: str
    output: Any = None
    success: bool = True
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    success: bool
    steps: list[WorkflowStepResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    final_output: Any = None
    error: str | None = None
