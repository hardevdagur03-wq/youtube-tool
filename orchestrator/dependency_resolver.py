"""Dependency Resolver — determines stage execution order based on dependencies.

No existing code is modified.
"""

from __future__ import annotations

from orchestrator.execution_graph import ExecutionGraph


STAGE_DEPENDENCIES = {
    "metadata": [],
    "transcript": ["metadata"],
    "analysis": ["transcript"],
    "seo": ["analysis"],
    "knowledge_graph": ["analysis"],
    "seo_intelligence": ["knowledge_graph"],
    "outline_generator": ["seo_intelligence"],
    "outline": ["outline_generator"],
    "sections": ["outline"],
    "merge": ["sections"],
    "review": ["merge"],
    "export": ["review"],
}


class DependencyResolver:
    """Resolves stage execution order from dependency definitions."""

    def __init__(self, dependencies: dict[str, list[str]] | None = None) -> None:
        self._deps = dependencies or STAGE_DEPENDENCIES

    def build_graph(self, stages: list[str] | None = None) -> ExecutionGraph:
        graph = ExecutionGraph()
        target_stages = stages or list(self._deps.keys())
        included = set(target_stages)

        def _include_deps(name: str) -> None:
            for dep in self._deps.get(name, []):
                if dep not in included:
                    included.add(dep)
                    _include_deps(dep)

        for s in target_stages:
            _include_deps(s)

        for name in self._deps:
            if name in included:
                deps = [d for d in self._deps[name] if d in included]
                graph.add_node(name, deps)

        return graph

    def execution_order(self, stages: list[str] | None = None) -> list[str]:
        graph = self.build_graph(stages)
        errors = graph.validate()
        if errors:
            raise ValueError(f"Graph validation failed: {errors}")
        return graph.topological_sort()

    def parallel_levels(self, stages: list[str] | None = None) -> list[list[str]]:
        graph = self.build_graph(stages)
        return graph.levels()

    def can_run_in_parallel(self, stage_a: str, stage_b: str) -> bool:
        graph = self.build_graph()
        a_deps = graph.get_upstream(stage_a)
        b_deps = graph.get_upstream(stage_b)
        a_dependents = set(graph.get_downstream(stage_a))
        b_dependents = set(graph.get_downstream(stage_b))
        return (
            stage_a not in b_deps
            and stage_b not in a_deps
            and stage_a not in b_dependents
            and stage_b not in a_dependents
        )

    @property
    def stages(self) -> list[str]:
        return list(self._deps.keys())
