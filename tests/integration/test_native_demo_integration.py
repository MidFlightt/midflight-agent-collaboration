"""Native engine traversal, viewer arrows and safe upgrade of the real peer demo."""

from types import SimpleNamespace

import pytest

from demo_fixture import NOW
from midflight.adapters.clock import FixedClock
from midflight.adapters.falkor_store import FalkorStore
from midflight.api.app import build_services
from midflight.domain.models import Contract, FieldType
from midflight.services.plans import PlanDraft
from midflight.theater.live_graph import snapshot
from midflight.theater.scenario import change, seed
from midflight.theater.worktree_lab import seed_lab


def test_native_engine_selects_recipients_and_viewer_uses_real_edges(falkor_store, monkeypatch):
    services = build_services(falkor_store, FixedClock(NOW))
    seed(services, "demo")
    query = falkor_store._query
    calls = []

    def native(text, params=None):
        assert "RETURN a.key,type(r)" not in text, "Python BFS adjacency query was used"
        calls.append(text)
        return query(text, params)

    monkeypatch.setattr(falkor_store, "_query", native)
    monkeypatch.setattr(
        "midflight.services.plans.affected_tasks",
        lambda *args: pytest.fail("Python reachability fallback"),
    )
    change(services, "demo")
    assert any("shortestPath" in text for text in calls)
    directives = falkor_store.list_directives("demo")
    assert {d.recipient_id for d in directives} == {"pricing", "checkout", "reporting"}
    reporting = next(d for d in directives if d.task_id == "reporting")
    assert "potential downstream impact" in reporting.requested_adjustment
    live = SimpleNamespace(
        version=2,
        panes={},
        theater=SimpleNamespace(project="demo", server=SimpleNamespace(services=services)),
    )
    state = snapshot(live)
    assert len(state["native_dependencies"]) == 2
    assert any(p["task_id"] == "reporting" for p in state["dependency_evidence"])
    # JSON remains intact; only native edges are removed. Queries must reflect it.
    falkor_store._query("MATCH ()-[r:CONSUMED_BY]->() DELETE r")
    assert falkor_store.dependency_links("demo", 2) == []
    assert services.plans.current("demo").contract("price").consumer_tasks == ["checkout"]
    assert falkor_store.dependency_impact("demo", 2, 2, ["price"]).affected_tasks == {
        "pricing": ["price"]
    }


def test_startup_backfills_old_plans_without_changing_payloads(falkor_store):
    services = build_services(falkor_store, FixedClock(NOW))
    seed(services, "demo")
    old = falkor_store.get_plan("demo", 1)
    revision = falkor_store.get_project("demo").coord_rev
    falkor_store._query("MATCH (p:MFPlan) REMOVE p.graph_key")
    fresh = FalkorStore(falkor_store.graph)
    assert fresh.get_plan("demo", 1) == old
    assert fresh.get_project("demo").coord_rev == revision
    assert len(fresh.dependency_links("demo", 1)) == 2
    again = FalkorStore(falkor_store.graph)
    assert again.get_project("demo").coord_rev == revision


def test_native_paths_survive_database_restart(falkor_store, falkor_server):
    services = build_services(falkor_store, FixedClock(NOW))
    seed(services, "demo")
    before = falkor_store.dependency_impact("demo", 1, 1, ["price"])
    falkor_server.kill_and_restart()
    fresh = FalkorStore.connect(port=falkor_server.port, graph_name=falkor_store.graph.name)
    try:
        assert fresh.dependency_impact("demo", 1, 1, ["price"]) == before
        assert len(fresh.dependency_links("demo", 1)) == 2
    finally:
        fresh.close()


def test_worktree_lab_can_grow_graph_from_no_contracts(falkor_store):
    services = build_services(falkor_store, FixedClock(NOW))
    seed_lab(services, "lab")
    assert falkor_store.dependency_links("lab", 1) == []
    old = services.plans.current("lab")
    contract = Contract(
        id="task-list",
        version=2,
        provider_task="api",
        consumer_tasks=["web", "cli"],
        fields={"title": FieldType.STRING},
    )
    actor = falkor_store.get_participant("api")
    draft = services.plans.propose(
        actor, PlanDraft(requirements=old.requirements, tasks=old.tasks, contracts=[contract])
    )
    services.plans.approve(actor, draft.version, "Declare API consumers")
    assert {d.task_id for d in falkor_store.list_directives("lab")} == {"api", "web", "cli"}
    assert {link["consumer"] for link in falkor_store.dependency_links("lab", 2)} == {"web", "cli"}
