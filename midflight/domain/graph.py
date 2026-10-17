"""Versioned dependency evidence; pure value types, no database access."""

from dataclasses import dataclass


class GraphNotReady(RuntimeError):
    """A requested plan or its graph projection is missing."""


class GraphChanged(RuntimeError):
    """A draft changed during analysis; reread plans and recompute impact."""


class IncompleteImpact(RuntimeError):
    """A traversal budget was reached; its partial result must not authorize a change."""


@dataclass(frozen=True)
class GraphItem:
    kind: str
    item_id: str


@dataclass(frozen=True)
class ImpactPath:
    plan_version: int
    changed_id: str
    task_id: str
    nodes: tuple[GraphItem, ...]
    relationships: tuple[str, ...]


@dataclass(frozen=True)
class DependencyImpact:
    paths: tuple[ImpactPath, ...]
    snapshots: tuple[str, ...]

    @property
    def affected_tasks(self) -> dict[str, list[str]]:
        affected: dict[str, set[str]] = {}
        for path in self.paths:
            affected.setdefault(path.task_id, set()).add(path.changed_id)
        return {task: sorted(changes) for task, changes in sorted(affected.items())}
