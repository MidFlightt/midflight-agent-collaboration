from datetime import timedelta
from threading import Event

import pytest

from demo_fixture import NOW, PROJECT, seed, submission
from midflight.adapters.clock import FixedClock
from midflight.adapters.memory_store import MemoryStore
from midflight.adapters.worker import RecoverableWorker
from midflight.api.app import build_services
from midflight.config import Settings
from midflight.domain.models import JobKind, JobState
from midflight.ports import Commit


class QueueStore(MemoryStore):
    def list_unfinished_jobs(self):
        return [
            j for j in self.list_jobs(PROJECT) if j.state in (JobState.QUEUED, JobState.RUNNING)
        ]


def setup():
    store = QueueStore()
    seed(store)
    worker = RecoverableWorker(store, FixedClock(NOW), retry_delay=0)
    services = build_services(store, FixedClock(NOW), runner=worker)
    worker.register(JobKind.CLAIM_REVIEW, services.claims.run_review)
    result = services.claims.submit(store.get_participant("p-t1"), submission("T1"))
    return store, worker, result


def test_saved_job_runs_without_submit_notification():
    store, _, result = setup()
    fresh = RecoverableWorker(store, FixedClock(NOW), retry_delay=0)
    services = build_services(store, FixedClock(NOW), runner=fresh)
    fresh.register(JobKind.CLAIM_REVIEW, services.claims.run_review)
    assert fresh.run_once() == 1
    assert store.get_job(result.job_id).state is JobState.SUCCEEDED
    assert fresh.run_once() == 0


def test_running_job_is_recovered_after_restart():
    store, worker, result = setup()
    job = store.get_job(result.job_id)
    store.commit(
        Commit(
            PROJECT,
            "crash",
            puts=[job.model_copy(update={"state": JobState.RUNNING, "attempts": 1})],
        )
    )
    worker.run_once()
    assert store.get_job(job.id).state is JobState.SUCCEEDED
    assert store.get_job(job.id).attempts == 2


def test_failures_are_bounded_and_durable():
    store, worker, result = setup()

    def fail(job):
        raise RuntimeError("secret must not be persisted")

    worker.register(JobKind.CLAIM_REVIEW, fail)
    for _ in range(3):
        worker.run_once()
    job = store.get_job(result.job_id)
    assert job.state is JobState.FAILED
    assert job.attempts == 3
    assert "secret" not in job.error
    assert worker.run_once() == 0
    assert any(e.action == "job.worker_failed" for e in store.list_audit(PROJECT))


def test_backoff_survives_worker_restart():
    store, worker, result = setup()
    worker.retry_delay = 10
    worker.register(JobKind.CLAIM_REVIEW, lambda job: (_ for _ in ()).throw(ValueError()))
    worker.run_once()
    fresh = RecoverableWorker(store, FixedClock(NOW + timedelta(seconds=9)), retry_delay=10)
    assert fresh.run_once() == 0
    assert store.get_job(result.job_id).attempts == 1


def test_lost_success_reply_does_not_reopen_finished_job():
    store, worker, result = setup()
    original = worker._handlers[JobKind.CLAIM_REVIEW]

    def lost(job):
        original(job)
        raise ConnectionError("lost reply")

    worker.register(JobKind.CLAIM_REVIEW, lost)
    worker.run_once()
    assert store.get_job(result.job_id).state is JobState.SUCCEEDED


def test_background_lifecycle():
    store, worker, result = setup()
    done = Event()
    original = worker._handlers[JobKind.CLAIM_REVIEW]

    def handle(job):
        original(job)
        done.set()

    worker.register(JobKind.CLAIM_REVIEW, handle)
    worker.start()
    try:
        assert done.wait(3)
    finally:
        worker.stop()
    assert not worker.running


def test_backend_selection_is_explicit_and_rejects_invalid_settings():
    assert Settings(table_name="legacy", store_backend="falkordb").backend == "falkordb"
    assert Settings(table_name="legacy").backend == "dynamodb"
    assert Settings().backend == "memory"
    with pytest.raises(ValueError):
        Settings(store_backend="typo")
    with pytest.raises(ValueError):
        Settings(store_backend="dynamodb")
    with pytest.raises(ValueError):
        Settings(worker_max_attempts=0)


def test_failed_poll_does_not_kill_background_worker(monkeypatch):
    store, worker, result = setup()
    original = store.list_unfinished_jobs
    recovered = Event()
    calls = 0

    def scan():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionError("offline")
        recovered.set()
        return original()

    monkeypatch.setattr(store, "list_unfinished_jobs", scan)
    worker.poll_interval = 0.01
    worker.start()
    try:
        assert recovered.wait(3)
    finally:
        worker.stop()
    assert store.get_job(result.job_id).state is JobState.SUCCEEDED


def test_environment_settings_and_connection_arguments(monkeypatch):
    from midflight.adapters.falkor_store import FalkorStore
    from midflight.wiring import store_for

    settings = Settings.from_env(
        {
            "MIDFLIGHT_STORE": "falkordb",
            "MIDFLIGHT_TABLE": "unused",
            "MIDFLIGHT_FALKOR_PORT": "6380",
            "MIDFLIGHT_FALKOR_GRAPH": "test",
            "MIDFLIGHT_FALKOR_PASSWORD": "test-secret",
            "MIDFLIGHT_FALKOR_SSL": "1",
        }
    )
    captured = {}

    def connect(**kwargs):
        captured.update(kwargs)
        return "store"

    monkeypatch.setattr(FalkorStore, "connect", connect)
    assert store_for(settings) == "store"
    assert captured["port"] == 6380 and captured["ssl"] is True
    assert captured["graph_name"] == "test"
    assert "test-secret" not in repr(settings)


def test_exhausted_running_job_fails_without_another_dispatch():
    store, worker, result = setup()
    job = store.get_job(result.job_id)
    store.commit(
        Commit(
            PROJECT,
            "crash-at-limit",
            puts=[job.model_copy(update={"state": JobState.RUNNING, "attempts": 3})],
        )
    )
    worker.register(JobKind.CLAIM_REVIEW, lambda job: pytest.fail("must not dispatch"))
    worker.run_once()
    assert store.get_job(job.id).state is JobState.FAILED
    assert store.get_job(job.id).attempts == 3


def test_handler_declared_failure_requires_explicit_retry():
    store, worker, result = setup()

    def fail_terminal(job):
        store.commit(
            Commit(
                PROJECT,
                "terminal",
                puts=[
                    job.model_copy(update={"state": JobState.FAILED, "error": "review incomplete"})
                ],
            )
        )

    worker.register(JobKind.CLAIM_REVIEW, fail_terminal)
    worker.run_once()
    assert worker.run_once() == 0
    assert store.get_job(result.job_id).error == "review incomplete"


class BusyQueueStore(QueueStore):
    """Before each of the first `busy` review saves, another change lands."""

    busy = 0

    def commit(self, commit):
        if commit.idempotency_key.startswith("review:") and self.busy > 0:
            self.busy -= 1
            super().commit(Commit(PROJECT, f"busy-{self.busy}", bump_coord_rev=True))
        return super().commit(commit)


def test_a_review_that_keeps_losing_is_requeued_and_succeeds_later():
    from midflight.services.claims import MAX_REVIEW_RUNS

    store = BusyQueueStore()
    seed(store)
    worker = RecoverableWorker(store, FixedClock(NOW), retry_delay=0)
    services = build_services(store, FixedClock(NOW), runner=worker)
    services.claims._sleep = lambda _seconds: None
    worker.register(JobKind.CLAIM_REVIEW, services.claims.run_review)
    result = services.claims.submit(store.get_participant("p-t1"), submission("T1"))
    store.busy = MAX_REVIEW_RUNS  # the whole first attempt loses

    worker.run_once()
    assert store.get_job(result.job_id).state is JobState.QUEUED
    assert "ReviewBusy" in store.get_job(result.job_id).error
    worker.run_once()

    assert store.get_job(result.job_id).state is JobState.SUCCEEDED
    assert store.get_claim(result.claim_id).state.value == "approved"
