from threading import Event

from fastapi.testclient import TestClient

from demo_fixture import NOW, PROJECT, seed, submission
from midflight.adapters.clock import FixedClock
from midflight.adapters.falkor_store import FalkorStore
from midflight.adapters.worker import RecoverableWorker
from midflight.api.app import build_services
from midflight.config import Settings
from midflight.domain.models import JobKind, JobState
from midflight.main import create_server
from midflight.ports import Commit


def test_recover_claim_after_database_restart(falkor_store, falkor_server):
    seed(falkor_store)
    clock = FixedClock(NOW)
    worker = RecoverableWorker(falkor_store, clock, retry_delay=0)
    services = build_services(falkor_store, clock, runner=worker)
    result = services.claims.submit(falkor_store.get_participant("p-t1"), submission("T1"))
    job = falkor_store.get_job(result.job_id)
    falkor_store.commit(
        Commit(
            PROJECT,
            "interrupted-dispatch",
            puts=[job.model_copy(update={"state": JobState.RUNNING, "attempts": 1})],
        )
    )
    falkor_server.kill_and_restart()
    fresh = FalkorStore.connect(port=falkor_server.port, graph_name=falkor_store.graph.name)
    try:
        recovered = RecoverableWorker(fresh, clock, retry_delay=0)
        services = build_services(fresh, clock, runner=recovered)
        recovered.register(JobKind.CLAIM_REVIEW, services.claims.run_review)
        assert recovered.run_once() == 1
        assert fresh.get_job(job.id).state is JobState.SUCCEEDED
        assert fresh.get_job(job.id).attempts == 2
        assert recovered.run_once() == 0
    finally:
        fresh.close()


def test_configured_server_owns_worker_and_closes_store(falkor_store, falkor_server, monkeypatch):
    seed(falkor_store)
    queued = RecoverableWorker(falkor_store, FixedClock(NOW))
    services = build_services(falkor_store, FixedClock(NOW), runner=queued)
    result = services.claims.submit(falkor_store.get_participant("p-t1"), submission("T1"))
    # A stale AWS table variable must not select StreamRunner when FalkorDB is explicit.
    server = create_server(
        Settings(
            dev_login=True,
            store_backend="falkordb",
            table_name="old",
            falkor_port=falkor_server.port,
            falkor_graph=falkor_store.graph.name,
            worker_poll_interval=0.01,
        )
    )
    done, closed = Event(), Event()
    # Registered handler is captured during construction: observe persisted result instead.
    original = server.services.store.commit

    def observe(write):
        outcome = original(write)
        if any(getattr(p, "state", None) is JobState.SUCCEEDED for p in write.puts):
            done.set()
        return outcome

    monkeypatch.setattr(server.services.store, "commit", observe)
    close = server.services.store.close

    def closing():
        close()
        closed.set()

    monkeypatch.setattr(server.services.store, "close", closing)
    with TestClient(server.app):
        assert done.wait(5)
        assert server.services.store.get_job(result.job_id).state is JobState.SUCCEEDED
    assert closed.is_set()


def test_review_rechecks_revision_when_context_changes(falkor_store):
    seed(falkor_store)
    clock = FixedClock(NOW)
    worker = RecoverableWorker(falkor_store, clock, retry_delay=0)

    class ChangingReviewer:
        calls = 0

        def review_claim(self, request):
            self.calls += 1
            if self.calls == 1:
                falkor_store.commit(Commit(PROJECT, "concurrent-change", bump_coord_rev=True))
            return {"findings": []}

    reviewer = ChangingReviewer()
    services = build_services(falkor_store, clock, reviewer=reviewer, runner=worker)
    worker.register(JobKind.CLAIM_REVIEW, services.claims.run_review)
    result = services.claims.submit(falkor_store.get_participant("p-t1"), submission("T1"))
    worker.run_once()
    # The rerun reads the new revision but reuses the reviewer's answer: the change
    # touched nothing the reviewer was asked about.
    assert reviewer.calls == 1
    assert falkor_store.get_job(result.job_id).state is JobState.SUCCEEDED
    events = [e for e in falkor_store.list_audit(PROJECT) if e.action == "claim.reviewed"]
    assert len(events) == 1
    assert events[0].versions["coord_rev"] == 2
