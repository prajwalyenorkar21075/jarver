"""Workflow Graph - DAG with adjacency lists, cycle detection, topological sort."""

import logging
from collections import deque

from app.openjarvis.workflow.types import WorkflowNode, WorkflowEdge

logger = logging.getLogger(__name__)


class WorkflowGraph:
    def __init__(self):
        self._nodes: dict[str, WorkflowNode] = {}
        self._edges: list[WorkflowEdge] = []
        self._forward: dict[str, list[str]] = {}
        self._reverse: dict[str, list[str]] = {}

    def add_node(self, node: WorkflowNode) -> None:
        self._nodes[node.id] = node
        if node.id not in self._forward:
            self._forward[node.id] = []
        if node.id not in self._reverse:
            self._reverse[node.id] = []

    def add_edge(self, edge: WorkflowEdge) -> None:
        if edge.source not in self._nodes or edge.target not in self._nodes:
            raise ValueError(f"Edge references unknown node: {edge.source} -> {edge.target}")
        self._edges.append(edge)
        self._forward[edge.source].append(edge.target)
        self._reverse[edge.target].append(edge.source)

    def validate(self) -> bool:
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for neighbor in self._forward.get(node_id, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node_id)
            return False

        for node_id in self._nodes:
            if node_id not in visited:
                if dfs(node_id):
                    raise ValueError("Workflow graph contains a cycle")

        in_degree = {nid: 0 for nid in self._nodes}
        for edge in self._edges:
            in_degree[edge.target] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        count = 0
        while queue:
            node = queue.popleft()
            count += 1
            for neighbor in self._forward.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if count != len(self._nodes):
            raise ValueError("Workflow graph is not a valid DAG")

        return True

    def topological_sort(self) -> list[str]:
        self.validate()

        in_degree = {nid: 0 for nid in self._nodes}
        for edge in self._edges:
            in_degree[edge.target] += 1

        queue = deque(sorted([nid for nid, deg in in_degree.items() if deg == 0]))
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in sorted(self._forward.get(node, [])):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def execution_stages(self) -> list[list[str]]:
        self.validate()

        in_degree = {nid: 0 for nid in self._nodes}
        for edge in self._edges:
            in_degree[edge.target] += 1

        stages = []
        remaining = dict(in_degree)

        while any(remaining.values()) or any(v == 0 for v in remaining.values()):
            stage = sorted([nid for nid, deg in remaining.items() if deg == 0])
            if not stage:
                break
            stages.append(stage)
            for node in stage:
                del remaining[node]
                for neighbor in self._forward.get(node, []):
                    if neighbor in remaining:
                        remaining[neighbor] -= 1

        return stages

    def predecessors(self, node_id: str) -> list[str]:
        return self._reverse.get(node_id, [])

    def successors(self, node_id: str) -> list[str]:
        return self._forward.get(node_id, [])

    @property
    def nodes(self) -> dict[str, WorkflowNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[WorkflowEdge]:
        return list(self._edges)
