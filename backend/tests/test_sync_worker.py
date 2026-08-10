import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

from backend.app.application.sync_worker import SyncWorker
from backend.app.domain.sync_job import SyncJob, SyncJobMessage, SyncResult


def _job() -> SyncJob:
    now = datetime.now(UTC)
    return SyncJob(
        id="sync-1", workspace_id="store-1", resource_type="stock", status="running",
        processed_count=0, failure_count=0, attempt_count=1, max_attempts=3,
        next_attempt_at=now, created_at=now, lease_owner="worker-1",
        lease_expires_at=now,
    )


@dataclass
class FakeConsumer:
    message: SyncJobMessage | None = field(
        default_factory=lambda: SyncJobMessage(message_id="1-0", job_id="sync-1")
    )
    acknowledged: list[str] = field(default_factory=list)

    async def read_one(self, *, block_ms: int) -> SyncJobMessage | None:
        del block_ms
        return self.message

    async def acknowledge(self, message_id: str) -> None:
        self.acknowledged.append(message_id)


@dataclass
class FakeJobs:
    claimed: SyncJob | None = field(default_factory=_job)
    complete_persisted: bool = True
    failed: tuple[str, str] | None = None

    async def claim_sync_job(self, **kwargs: object) -> SyncJob | None:
        del kwargs
        return self.claimed

    async def heartbeat_sync_job(self, **kwargs: object) -> bool:
        del kwargs
        return True

    async def complete_sync_job(self, **kwargs: object) -> bool:
        del kwargs
        return self.complete_persisted

    async def fail_sync_job(self, **kwargs: object) -> bool:
        self.failed = (str(kwargs["error_code"]), str(kwargs["error_message"]))
        return True


class SuccessHandler:
    async def run(self, job: SyncJob) -> SyncResult:
        del job
        return SyncResult(processed_count=8, failure_count=0)


class SecretFailureHandler:
    async def run(self, job: SyncJob) -> SyncResult:
        del job
        raise RuntimeError("Api-Key=should-never-be-persisted")


def test_worker_acknowledges_only_after_completion_persists() -> None:
    jobs = FakeJobs()
    consumer = FakeConsumer()
    worker = SyncWorker(
        jobs, consumer, {"stock": SuccessHandler()}, worker_id="worker-1"
    )

    assert asyncio.run(worker.process_one()) is True
    assert consumer.acknowledged == ["1-0"]


def test_worker_does_not_ack_when_completion_is_not_persisted() -> None:
    jobs = FakeJobs(complete_persisted=False)
    consumer = FakeConsumer()
    worker = SyncWorker(
        jobs, consumer, {"stock": SuccessHandler()}, worker_id="worker-1"
    )

    assert asyncio.run(worker.process_one()) is False
    assert consumer.acknowledged == []


def test_duplicate_message_without_lease_is_safely_acknowledged() -> None:
    jobs = FakeJobs(claimed=None)
    consumer = FakeConsumer()
    worker = SyncWorker(jobs, consumer, {}, worker_id="worker-1")

    assert asyncio.run(worker.process_one()) is True
    assert consumer.acknowledged == ["1-0"]


def test_handler_exception_is_redacted_before_retry() -> None:
    jobs = FakeJobs()
    consumer = FakeConsumer()
    worker = SyncWorker(
        jobs, consumer, {"stock": SecretFailureHandler()}, worker_id="worker-1"
    )

    assert asyncio.run(worker.process_one()) is True
    assert jobs.failed == ("sync_handler_failed", "同步处理失败")
    assert "Api-Key" not in str(jobs.failed)
    assert consumer.acknowledged == ["1-0"]
