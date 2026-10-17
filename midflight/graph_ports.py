"""Optional graph-plan capabilities, separate from the existing Store contract."""

from typing import Protocol, runtime_checkable

from midflight.domain.graph import DependencyImpact
from midflight.domain.models import Plan
from midflight.ports import Commit, CommitResult


@runtime_checkable
class GraphPlanStore(Protocol):
    def plan_graph_key(self, plan: Plan) -> str: ...

    def dependency_impact(
        self, project_id: str, old_version: int, new_version: int, changed: list[str]
    ) -> DependencyImpact: ...

    def commit_graph_approval(
        self, commit: Commit, expected_graphs: dict[int, str]
    ) -> CommitResult:
        """Reject unless every analyzed snapshot is still current in the atomic write."""
        ...
