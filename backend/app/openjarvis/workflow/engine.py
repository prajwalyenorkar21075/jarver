"""Workflow Engine - Executes a WorkflowGraph against registered tools and agents."""

import ast
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.openjarvis.workflow.types import (
    NodeType, WorkflowNode, WorkflowStepResult, WorkflowResult,
)
from app.openjarvis.workflow.graph import WorkflowGraph
from app.openjarvis.tools import ToolRegistry

logger = logging.getLogger(__name__)


class WorkflowEngine:
    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers
        self._context: dict[str, Any] = {}

    async def execute(self, graph: WorkflowGraph, initial_input: Any = None) -> WorkflowResult:
        start_time = time.time()
        steps: list[WorkflowStepResult] = []
        self._context = {"input": initial_input}

        try:
            order = graph.topological_sort()
        except ValueError as e:
            return WorkflowResult(success=False, error=str(e), total_duration_ms=self._elapsed(start_time))

        for node_id in order:
            node = graph.nodes[node_id]
            step_start = time.time()

            try:
                if node.node_type == NodeType.TOOL:
                    output = await self._run_tool_node(node)
                elif node.node_type == NodeType.AGENT:
                    output = await self._run_agent_node(node)
                elif node.node_type == NodeType.CONDITION:
                    output = self._run_condition_node(node)
                elif node.node_type == NodeType.TRANSFORM:
                    output = self._run_transform_node(node)
                elif node.node_type == NodeType.LOOP:
                    output = await self._run_loop_node(node, graph)
                elif node.node_type == NodeType.PARALLEL:
                    output = await self._run_parallel_node(node, graph)
                else:
                    output = None

                step = WorkflowStepResult(
                    node_id=node_id,
                    output=output,
                    success=True,
                    duration_ms=self._elapsed(step_start),
                )
            except Exception as e:
                logger.error(f"Workflow node {node_id} failed: {e}")
                step = WorkflowStepResult(
                    node_id=node_id,
                    success=False,
                    error=str(e),
                    duration_ms=self._elapsed(step_start),
                )
                steps.append(step)
                return WorkflowResult(
                    success=False,
                    steps=steps,
                    total_duration_ms=self._elapsed(start_time),
                    error=f"Node {node_id} failed: {e}",
                )

            steps.append(step)
            self._context[f"node:{node_id}"] = output

        final_output = self._context.get(f"node:{order[-1]}") if order else None

        return WorkflowResult(
            success=True,
            steps=steps,
            total_duration_ms=self._elapsed(start_time),
            final_output=final_output,
        )

    async def _run_tool_node(self, node: WorkflowNode) -> Any:
        tool_name = node.tools[0] if node.tools else node.id
        tool = ToolRegistry.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        args = node.config.get("arguments", {})
        resolved_args = self._resolve_placeholders(args)
        return await tool.execute(**resolved_args)

    async def _run_agent_node(self, node: WorkflowNode) -> Any:
        return {"agent": node.agent, "input": self._context.get("input"), "config": node.config}

    def _run_condition_node(self, node: WorkflowNode) -> Any:
        expr = node.condition_expr or "True"
        safe_ast = ast.parse(expr, mode="eval")
        allowed_names = {k: v for k, v in self._context.items() if isinstance(v, (bool, int, float, str))}
        result = eval(compile(safe_ast, "<condition>", "eval"), {"__builtins__": {}}, allowed_names)
        return bool(result)

    def _run_transform_node(self, node: WorkflowNode) -> Any:
        transform = node.transform_expr or "input"
        input_val = self._context.get("input", "")

        if transform == "concatenate":
            parts = []
            for key in sorted(self._context.keys()):
                if key.startswith("node:") and isinstance(self._context[key], str):
                    parts.append(self._context[key])
            return "\n".join(parts)
        elif transform == "first_line":
            return str(input_val).split("\n")[0] if input_val else ""
        else:
            return input_val

    async def _run_loop_node(self, node: WorkflowNode, graph: WorkflowGraph) -> Any:
        max_iter = node.max_iterations
        condition = node.condition_expr or "False"

        for i in range(max_iter):
            self._context["loop_iteration"] = i
            result = await self._run_agent_node(node)

            safe_ast = ast.parse(condition, mode="eval")
            allowed = {k: v for k, v in self._context.items() if isinstance(v, (bool, int, float, str))}
            allowed["iteration"] = i
            allowed["result"] = result
            should_break = eval(compile(safe_ast, "<loop_condition>", "eval"), {"__builtins__": {}}, allowed)

            if should_break:
                return result

        return result

    async def _run_parallel_node(self, node: WorkflowNode, graph: WorkflowGraph) -> Any:
        successors = graph.successors(node.id)
        results = {}

        async def run_one(nid: str):
            n = graph.nodes[nid]
            if n.node_type == NodeType.TOOL:
                return await self._run_tool_node(n)
            return await self._run_agent_node(n)

        import asyncio
        tasks = {nid: asyncio.create_task(run_one(nid)) for nid in successors}
        for nid, task in tasks.items():
            results[nid] = await task

        return results

    def _resolve_placeholders(self, obj: Any) -> Any:
        if isinstance(obj, str) and obj.startswith("{") and obj.endswith("}"):
            key = obj[1:-1]
            return self._context.get(key, obj)
        elif isinstance(obj, dict):
            return {k: self._resolve_placeholders(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_placeholders(item) for item in obj]
        return obj

    def _elapsed(self, start: float) -> float:
        return (time.time() - start) * 1000
