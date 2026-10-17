"""GH-04: immutable plan projections and bounded, version-scoped graph traversal."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

from midflight.domain.graph import (
    DependencyImpact,
    GraphChanged,
    GraphItem,
    GraphNotReady,
    ImpactPath,
    IncompleteImpact,
)
from midflight.domain.models import Plan


def encoded(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def projection(plan: Plan) -> dict[str, Any]:
    content = plan.model_dump(mode="json", include={"tasks", "contracts", "requirements"})
    digest = hashlib.sha256(encoded(content).encode()).hexdigest()
    scope = encoded([plan.project_id, plan.version, digest])
    nodes = {}
    for kind, values in [
        ("task", plan.tasks),
        ("contract", plan.contracts),
        ("requirement", plan.requirements),
    ]:
        for value in values:
            identity = (kind, value.id)
            if identity in nodes:
                raise ValueError(f"duplicate graph {kind}: {value.id}")
            nodes[identity] = {
                "key": encoded([scope, kind, value.id]),
                "scope": scope,
                "kind": kind,
                "item_id": value.id,
                "payload": value.model_dump_json(),
            }
    edges: dict[str, set[tuple[str, str]]] = {
        r: set() for r in ("PROVIDES", "CONSUMED_BY", "IMPLEMENTED_BY")
    }

    def edge(relation, source, target):
        if source not in nodes or target not in nodes:
            raise ValueError(f"unknown graph reference: {source} -> {target}")
        edges[relation].add((nodes[source]["key"], nodes[target]["key"]))

    for task in plan.tasks:
        for requirement in task.requirement_ids:
            edge("IMPLEMENTED_BY", ("requirement", requirement), ("task", task.id))
        for contract in task.provides:
            edge("PROVIDES", ("task", task.id), ("contract", contract))
        for contract in task.consumes:
            edge("CONSUMED_BY", ("contract", contract), ("task", task.id))
    for contract in plan.contracts:
        edge("PROVIDES", ("task", contract.provider_task), ("contract", contract.id))
        for consumer in contract.consumer_tasks:
            edge("CONSUMED_BY", ("contract", contract.id), ("task", consumer))
    return {
        "key": scope,
        "nodes": list(nodes.values()),
        **{
            relation: [{"source": source, "target": target} for source, target in sorted(links)]
            for relation, links in edges.items()
        },
    }


def projection_clauses(index: int) -> list[str]:
    """Clauses embedded INSIDE Store.commit's guarded atomic mutation block."""
    parameter = f"$graph{index}"
    clauses = [
        f"MERGE (g{index}:MFPlanGraph {{key:{parameter}.key}})",
        f"SET n{index}.graph_key = {parameter}.key",
        f"MERGE (n{index})-[:HAS_GRAPH]->(g{index})",
        f"FOREACH (item IN {parameter}.nodes | "
        f"MERGE (part:MFContext {{key:item.key}}) SET part += item "
        f"MERGE (g{index})-[:HAS_ITEM]->(part))",
    ]
    for relation in ("PROVIDES", "CONSUMED_BY", "IMPLEMENTED_BY"):
        clauses.append(
            f"FOREACH (link IN {parameter}.{relation} | "
            "MERGE (source:MFContext {key:link.source}) "
            "MERGE (targetPart:MFContext {key:link.target}) "
            f"MERGE (source)-[:{relation}]->(targetPart))"
        )
    return clauses


class DependencyQueries:
    def __init__(self, query: Callable[..., list]) -> None:
        self.query = query

    def impact(
        self,
        project_id: str,
        old_version: int,
        new_version: int,
        changed: list[str],
        *,
        max_depth: int = 32,
        max_nodes: int = 1000,
        max_edges: int = 5000,
    ) -> DependencyImpact:
        if min(max_depth, max_nodes, max_edges) < 1:
            raise ValueError("impact limits must be positive")
        if len(changed) > max_nodes:
            raise IncompleteImpact("too many changed items")
        scopes = {}
        for version in dict.fromkeys([old_version, new_version]):
            rows = self.query(
                "MATCH (p:MFPlan {key:$key}) "
                "MATCH (g:MFPlanGraph) WHERE g.key=p.graph_key RETURN g.key",
                {"key": encoded(["Plan", project_id, version])},
            )
            if len(rows) != 1:
                raise GraphNotReady(f"plan {project_id} v{version} has no graph projection")
            scopes[version] = rows[0][0]
        current = self.query(
            "MATCH (n:MFContext) WHERE n.scope=$scope AND n.kind='task' "
            "RETURN n.item_id LIMIT $limit",
            {"scope": scopes[new_version], "limit": max_nodes + 1},
        )
        if len(current) > max_nodes:
            raise IncompleteImpact("task limit reached")
        recipients = {row[0] for row in current}
        paths = []
        seen_changes = set()
        for version, scope in scopes.items():
            # Budget the entire selected context before asking the engine to
            # traverse it. Do not authorize a partial reachability result.
            counts = self.query(
                "MATCH (n:MFContext) WHERE n.scope=$scope RETURN count(n)",
                {"scope": scope},
            )
            if counts[0][0] > max_nodes:
                raise IncompleteImpact("node limit reached")
            counts = self.query(
                "MATCH (a:MFContext)-[r]->(b:MFContext) "
                "WHERE a.scope=$scope AND b.scope=$scope "
                "AND type(r) IN ['PROVIDES','CONSUMED_BY','IMPLEMENTED_BY'] "
                "RETURN count(r)",
                {"scope": scope},
            )
            if counts[0][0] > max_edges:
                raise IncompleteImpact("edge limit reached")
            seeds = self.query(
                "MATCH (n:MFContext) WHERE n.scope=$scope AND n.item_id IN $changed "
                "RETURN n.key,n.kind,n.item_id ORDER BY n.key LIMIT $limit",
                {"scope": scope, "changed": sorted(set(changed)), "limit": max_nodes + 1},
            )
            for key, kind, item_id in seeds:
                seen_changes.add(item_id)
                start = GraphItem(kind, item_id)
                if kind == "task" and item_id in recipients:
                    paths.append(ImpactPath(version, item_id, item_id, (start,), ()))
                # A changed contract also affects its provider, but must not
                # propagate backwards into the provider's other output contracts.
                if kind == "contract":
                    providers = self.query(
                        "MATCH (t:MFContext)-[:PROVIDES]->(c:MFContext {key:$key}) "
                        "WHERE t.scope=$scope RETURN t.item_id",
                        {"key": key, "scope": scope},
                    )
                    for (provider,) in providers:
                        if provider in recipients:
                            paths.append(
                                ImpactPath(
                                    version,
                                    item_id,
                                    provider,
                                    (start, GraphItem("task", provider)),
                                    ("PROVIDES_REVERSE",),
                                )
                            )
                # Reachability AND paths are computed inside FalkorDB. Python
                # only checks limits and turns returned values into domain types.
                rows = self.query(
                    NATIVE_IMPACT_QUERY,
                    {"key": key, "scope": scope, "recipients": sorted(recipients)},
                )
                for task, kinds, identifiers, relations in rows:
                    if len(relations) > max_depth:
                        raise IncompleteImpact("depth limit reached")
                    paths.append(
                        ImpactPath(
                            version,
                            item_id,
                            task,
                            tuple(GraphItem(k, i) for k, i in zip(kinds, identifiers, strict=True)),
                            tuple(relations),
                        )
                    )
        if set(changed) - seen_changes:
            raise ValueError("changed ids are absent from both plan versions")
        for version, scope in scopes.items():
            rows = self.query(
                "MATCH (p:MFPlan {key:$key}) RETURN p.graph_key",
                {"key": encoded(["Plan", project_id, version])},
            )
            if rows != [[scope]]:
                raise GraphChanged("plan graph changed during analysis; retry with fresh plans")
        # Cycles can reach a provider through a forward path as well. Keep the
        # shortest explanation for each changed item/task/version.
        unique = {}
        for path in paths:
            key = (path.plan_version, path.changed_id, path.task_id)
            if key not in unique or len(path.relationships) < len(unique[key].relationships):
                unique[key] = path
        return DependencyImpact(tuple(unique.values()), tuple(scopes.values()))


NATIVE_IMPACT_QUERY = """
MATCH (start:MFContext {key:$key}), (target:MFContext)
WHERE target.scope=$scope AND target.kind='task' AND target.item_id IN $recipients
  AND target.key <> start.key
WITH target, shortestPath(
  (start)-[:PROVIDES|CONSUMED_BY|IMPLEMENTED_BY*]->(target)
) AS route
WHERE route IS NOT NULL
RETURN target.item_id, [n IN nodes(route) | n.kind],
       [n IN nodes(route) | n.item_id], [r IN relationships(route) | type(r)]
ORDER BY target.item_id
"""
