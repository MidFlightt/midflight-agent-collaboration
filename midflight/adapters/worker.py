"""GH-03: one recoverable worker per service, using the database as its queue.

At-least-once execution: handlers own their atomic result commits and must tolerate
replay. A wake-up is only an optimization; saved jobs are scanned on every poll.
Run exactly one service process against a graph (no distributed lease is provided).
"""

from __future__ import annotations

import logging
from threading import Event, Lock, Thread
from typing import Protocol

from midflight.adapters.runners import _Dispatch
from midflight.domain.models import Job, JobState
from midflight.ports import Clock, Commit, Store
from midflight.services.audit import audit_event

log = logging.getLogger(__name__)
_TERMINAL = (JobState.SUCCEEDED, JobState.FAILED)


class RecoverableStore(Store, Protocol):
    def list_unfinished_jobs(self) -> list[Job]: ...


class RecoverableWorker(_Dispatch):
    # A handler may raise to have its job run again after the retry delay; the claim
    # review does this when other changes keep landing first (services.claims).
    retries_later = True

    def __init__(
        self,
        store: RecoverableStore,
        clock: Clock,
        *,
        max_attempts: int = 3,
        poll_interval: float = 1,
        retry_delay: float = 2,
    ) -> None:
        super().__init__()
        if max_attempts < 1 or poll_interval <= 0 or retry_delay < 0:
            raise ValueError("invalid worker retry/poll settings")
        self.store, self.clock = store, clock
        self.max_attempts, self.poll_interval, self.retry_delay = (
            max_attempts,
            poll_interval,
            retry_delay,
        )
        self._wake, self._stop = Event(), Event()
        self._dispatch_lock = Lock()
        self._thread: Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def submit(self, job: Job) -> None:
        # The service already committed the job alongside its claim/plan change.
        self._wake.set()

    def start(self) -> None:
        if self.running:
            raise RuntimeError("worker is already running")
        self._stop.clear()
        self._thread = Thread(target=self._loop, name="midflight-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 30) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout)
            if self._thread.is_alive():
                raise RuntimeError(
                    "worker did not finish before shutdown timeout; job remains durable"
                )

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._wake.clear()
            try:
                self.run_once()
            except Exception as exc:
                # Do not log response payloads or credentials from an external error.
                log.error("Worker poll failed (%s); will retry", type(exc).__name__)
            self._wake.wait(self.poll_interval)

    def run_once(self) -> int:
        """Process at most 100 due jobs. Storage failures propagate to the poll loop."""
        with self._dispatch_lock:
            count = 0
            jobs = sorted(self.store.list_unfinished_jobs(), key=lambda j: (j.created_at, j.id))
            for candidate in jobs:
                if self._stop.is_set() or count >= 100:
                    break
                job = self.store.get_job(candidate.id)
                if job is None or job.state in _TERMINAL:
                    continue
                delay = min(60, self.retry_delay * 2 ** min(job.attempts - 1, 10))
                if job.attempts and (self.clock.now() - job.updated_at).total_seconds() < delay:
                    continue
                if job.attempts >= self.max_attempts:
                    self._failed(job, "worker retry limit reached", terminal=True)
                    count += 1
                    continue
                started = job.model_copy(
                    update={
                        "state": JobState.RUNNING,
                        "attempts": job.attempts + 1,
                        "updated_at": self.clock.now(),
                        "error": None,
                    }
                )
                self.store.commit(
                    Commit(
                        job.project_id, f"worker-start:{job.id}:{started.attempts}", puts=[started]
                    )
                )
                count += 1
                try:
                    # Existing handlers increment attempts themselves on success.
                    # Pass the pre-dispatch count; the durable RUNNING record has
                    # already reserved this attempt even if the process crashes.
                    self._run(job)
                    saved = self.store.get_job(job.id)
                    if saved is None or saved.state not in _TERMINAL:
                        raise RuntimeError("handler returned without a terminal job result")
                except Exception as exc:
                    saved = self.store.get_job(job.id)
                    if saved is not None and saved.state not in _TERMINAL:
                        self._failed(
                            saved,
                            f"worker handler failed ({type(exc).__name__})",
                            terminal=saved.attempts >= self.max_attempts,
                        )
            return count

    def _failed(self, job: Job, reason: str, *, terminal: bool) -> None:
        key = f"worker-failure:{job.id}:{job.attempts}"
        updated = job.model_copy(
            update={
                "state": JobState.FAILED if terminal else JobState.QUEUED,
                "error": reason,
                "updated_at": self.clock.now(),
            }
        )
        event = audit_event(
            self.store,
            self.clock,
            project_id=job.project_id,
            actor="midflight",
            action="job.worker_failed" if terminal else "job.worker_retry",
            entity_ids=[job.id],
            reason=reason,
            correlation_id=job.correlation_id,
            idempotency_key=key,
        )
        self.store.commit(Commit(job.project_id, key, puts=[updated], audit=[event]))
