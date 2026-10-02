"""Workflow Builder - Fluent API for constructing workflow graphs."""

from app.openjarvis.workflow.types import NodeType, WorkflowNode, WorkflowEdge
from app.openjarvis.workflow.graph import WorkflowGraph


class WorkflowBuilder:
    def __init__(self, name: str = "workflow"):
        self._name = name
        self._graph = WorkflowGraph()

    def add_agent(self, node_id: str, agent: str, **config) -> "WorkflowBuilder":
        node = WorkflowNode(id=node_id, node_type=NodeType.AGENT, agent=agent, config=config)
        self._graph.add_node(node)
        return self

    def add_tool(self, node_id: str, tool_name: str, arguments: dict | None = None) -> "WorkflowBuilder":
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.TOOL,
            tools=[tool_name],
            config={"arguments": arguments or {}},
        )
        self._graph.add_node(node)
        return self

    def add_condition(self, node_id: str, expression: str) -> "WorkflowBuilder":
        node = WorkflowNode(id=node_id, node_type=NodeType.CONDITION, condition_expr=expression)
        self._graph.add_node(node)
        return self

    def add_loop(self, node_id: str, agent: str, condition: str, max_iterations: int = 10) -> "WorkflowBuilder":
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.LOOP,
            agent=agent,
            condition_expr=condition,
            max_iterations=max_iterations,
        )
        self._graph.add_node(node)
        return self

    def add_transform(self, node_id: str, expression: str) -> "WorkflowBuilder":
        node = WorkflowNode(id=node_id, node_type=NodeType.TRANSFORM, transform_expr=expression)
        self._graph.add_node(node)
        return self

    def connect(self, source: str, target: str, condition: str | None = None) -> "WorkflowBuilder":
        edge = WorkflowEdge(source=source, target=target, condition=condition)
        self._graph.add_edge(edge)
        return self

    def sequential(self, *node_ids: str) -> "WorkflowBuilder":
        for i in range(len(node_ids) - 1):
            self.connect(node_ids[i], node_ids[i + 1])
        return self

    def build(self) -> WorkflowGraph:
        self._graph.validate()
        return self._graph
