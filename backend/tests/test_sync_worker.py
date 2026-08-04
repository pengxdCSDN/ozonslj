import asyncio
from datetime import UTC, datetime

import pytest

from backend.app.application.sync_worker import SyncExecutionError, SyncWorker
from backend.app.domain.sync_job import ClaimedSyncJob


def _job() -> ClaimedSyncJob:
    return ClaimedSyncJob(
        id="sync_1",
        workspace_id="local",
        resource_type="products",
        sync_mode="incremental",
        status="running",
        created_at=datetime(2026, 8, 4, tzinfo=UTC),
        attempt_count=2,
    )


class _Gateway:
    def __init__(self, job: ClaimedSyncJob | None) -> None:
        self.job = job
        self.heartbeats = 0
        self.succeeded = False
        self.failure: tuple[str, str] | None = None

    async def claim_next(self, *, lease_seconds: int) -> ClaimedSyncJob | None:
        assert lease_seconds == 1
        return self.job

    async def heartbeat(self, job: ClaimedSyncJob, *, lease_seconds: int) -> None:
        assert job.attempt_count == 2
        self.heartbeats += 1

    async def mark_succeeded(self, job: ClaimedSyncJob) -> None:
        self.succeeded = True

    async def mark_failed(self, job: ClaimedSyncJob, *, code: str, message: str) -> None:
        self.failure = (code, message)


class _SuccessfulHandler:
    async def execute(self, job: ClaimedSyncJob) -> None:
        await asyncio.sleep(0.03)


class _FailedHandler:
    async def execute(self, job: ClaimedSyncJob) -> None:
        raise SyncExecutionError("UPSTREAM_TIMEOUT", "Ozon 请求超时")


class _UnexpectedFailedHandler:
    async def execute(self, job: ClaimedSyncJob) -> None:
        raise RuntimeError("Api-Key=不得进入任务记录")


@pytest.mark.asyncio
async def test_worker_renews_lease_and_completes_job() -> None:
    gateway = _Gateway(_job())
    worker = SyncWorker(gateway, _SuccessfulHandler(), lease_seconds=1, heartbeat_seconds=0.01)

    assert await worker.run_once() is True
    assert gateway.heartbeats >= 1
    assert gateway.succeeded is True
    assert gateway.failure is None


@pytest.mark.asyncio
async def test_worker_records_safe_execution_error() -> None:
    gateway = _Gateway(_job())
    worker = SyncWorker(gateway, _FailedHandler(), lease_seconds=1, heartbeat_seconds=0.01)

    assert await worker.run_once() is True
    assert gateway.succeeded is False
    assert gateway.failure == ("UPSTREAM_TIMEOUT", "Ozon 请求超时")


@pytest.mark.asyncio
async def test_worker_redacts_unexpected_error_message() -> None:
    gateway = _Gateway(_job())
    worker = SyncWorker(
        gateway,
        _UnexpectedFailedHandler(),
        lease_seconds=1,
        heartbeat_seconds=0.01,
    )

    assert await worker.run_once() is True
    assert gateway.failure == ("UNEXPECTED_SYNC_ERROR", "同步任务发生未分类错误")
    assert "Api-Key" not in gateway.failure[1]


@pytest.mark.asyncio
async def test_worker_returns_false_when_queue_is_empty() -> None:
    gateway = _Gateway(None)
    worker = SyncWorker(gateway, _SuccessfulHandler(), lease_seconds=1, heartbeat_seconds=0.01)

    assert await worker.run_once() is False


def test_worker_rejects_heartbeat_not_shorter_than_lease() -> None:
    with pytest.raises(ValueError, match="心跳间隔"):
        SyncWorker(_Gateway(None), _SuccessfulHandler(), lease_seconds=30, heartbeat_seconds=30)
