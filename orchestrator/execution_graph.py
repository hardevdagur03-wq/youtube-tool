"""Execution Graph — DAG of stages with dependency resolution.

Determines execution order based on stage dependencies.
No existing code is modified.
"""

from __future__ import annotations

from collections import deque
from typing import Any


class GraphNode:
    """A single node in the execution DAG."""

    def __init__(self, name: str, dependencies: list[str] | None = None) -> None:
        self.name = name
        self.dependencies = dependencies or []


class ExecutionGraph:
    """Directed acyclic graph of pipeline stages."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}

    def add_node(self, name: str, dependencies: list[str] | None = None) -> None:
        self._nodes[name] = GraphNode(name, dependencies or [])

    def get_node(self, name: str) -> GraphNode | None:
        return self._nodes.get(name)

    @property
    def nodes(self) -> dict[str, GraphNode]:
        return dict(self._nodes)

    @property
    def stage_names(self) -> list[str]:
        return list(self._nodes.keys())

    def topological_sort(self) -> list[str]:
        """Return stages in execution order (dependencies first)."""
        visited: set[str] = set()
        result: list[str] = []

        def _visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            node = self._nodes.get(name)
            if node:
                for dep in node.dependencies:
                    _visit(dep)
                result.append(name)

        for name in self._nodes:
            _visit(name)
        return result

    def get_ready_stages(self, completed: set[str], failed: set[str]) -> list[str]:
        """Return stages whose dependencies are all satisfied."""
        ready = []
        for name, node in self._nodes.items():
            if name in completed or name in failed:
                continue
            if all(dep in completed for dep in node.dependencies):
                ready.append(name)
        return ready

    def get_dependents(self, stage_name: str) -> list[str]:
        """Return all stages that depend on the given stage."""
        return [
            name for name, node in self._nodes.items()
            if stage_name in node.dependencies
        ]

    def get_upstream(self, stage_name: str) -> list[str]:
        """Return all stages that the given stage depends on."""
        node = self._nodes.get(stage_name)
        if node is None:
            return []
        return list(node.dependencies)

    def get_downstream(self, stage_name: str) -> list[str]:
        """Return all stages that transitively depend on the given stage."""
        downstream: set[str] = set()
        queue = deque([stage_name])
        while queue:
            current = queue.popleft()
            for dep in self.get_dependents(current):
                if dep not in downstream:
                    downstream.add(dep)
                    queue.append(dep)
        return list(downstream)

    def validate(self) -> list[str]:
        """Validate the graph. Returns list of errors."""
        errors = []
        for name, node in self._nodes.items():
            for dep in node.dependencies:
                if dep not in self._nodes:
                    errors.append(f"Stage '{name}' depends on unknown stage '{dep}'")
        try:
            self.topological_sort()
        except RecursionError:
            errors.append("Cycle detected in execution graph")
        return errors

    def levels(self) -> list[list[str]]:
        """Return stages grouped by parallel execution level."""
        result: list[list[str]] = []
        remaining = set(self._nodes.keys())
        completed: set[str] = set()

        while remaining:
            level = [
                name for name in remaining
                if all(dep in completed for dep in self._nodes[name].dependencies)
            ]
            if not level:
                break
            result.append(level)
            remaining -= set(level)
            completed |= set(level)

        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            name: {"dependencies": list(node.dependencies)}
            for name, node in self._nodes.items()
        }
