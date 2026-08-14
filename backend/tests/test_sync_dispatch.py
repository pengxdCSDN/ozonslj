import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast

import pytest
from redis.asyncio import Redis

from backend.app.application.sync_dispatch import SyncJobDispatcher
from backend.app.domain.sync_job import SyncJob
from backend.app.infrastructure.redis_sync_queue import RedisSyncJobQueue


def _job(job_id: str = "sync-1") -> SyncJob:
    now = datetime.now(UTC)
    return SyncJob(
        id=job_id, workspace_id="store-1", resource_type="stock", status="queued",
        processed_count=0, failure_count=0, attempt_count=0, max_attempts=3,
        next_attempt_at=now, created_at=now,
    )


@dataclass
class FakeJobs:
    jobs: list[SyncJob]

    async def list_dispatchable_sync_jobs(self, *, limit: int) -> list[SyncJob]:
        return self.jobs[:limit]


@dataclass
class FakeQueue:
    accepted: set[str] = field(default_factory=set)

    async def enqueue_once(self, job: SyncJob) -> bool:
        if job.id in self.accepted:
            return False
        self.accepted.add(job.id)
        return True


def test_dispatcher_counts_only_new_messages() -> None:
    queue = FakeQueue()
    dispatcher = SyncJobDispatcher(FakeJobs([_job(), _job()]), queue)

    assert asyncio.run(dispatcher.dispatch_due_jobs()) == 1


class FakeRedis:
    def __init__(self, *, fail_xadd: bool = False) -> None:
        self.markers: set[str] = set()
        self.messages: list[dict[str, str]] = []
        self.fail_xadd = fail_xadd

    async def set(self, key: str, value: str, **kwargs: object) -> bool:
        del value, kwargs
        if key in self.markers:
            return False
        self.markers.add(key)
        return True

    async def xadd(self, stream: str, fields: dict[str, str], **kwargs: object) -> str:
        del stream, kwargs
        if self.fail_xadd:
            raise ConnectionError("redis unavailable")
        self.messages.append(fields)
        return "1-0"

    async def delete(self, key: str) -> int:
        self.markers.discard(key)
        return 1


def test_redis_queue_suppresses_duplicate_dispatch() -> None:
    redis = FakeRedis()
    queue = RedisSyncJobQueue(cast(Redis, redis))

    assert asyncio.run(queue.enqueue_once(_job())) is True
    assert asyncio.run(queue.enqueue_once(_job())) is False
    assert redis.messages == [
        {"job_id": "sync-1", "workspace_id": "store-1", "resource_type": "stock"}
    ]


def test_redis_queue_releases_marker_after_publish_failure() -> None:
    redis = FakeRedis(fail_xadd=True)
    queue = RedisSyncJobQueue(cast(Redis, redis))

    with pytest.raises(ConnectionError):
        asyncio.run(queue.enqueue_once(_job()))

    assert redis.markers == set()
