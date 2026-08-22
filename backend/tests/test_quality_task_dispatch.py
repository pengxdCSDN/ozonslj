"""质量任务 Scheduler 从 PostgreSQL 重建 Redis 投递的测试。"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

from backend.app.application.quality_task_dispatch import QualityTaskDispatcher
from backend.app.domain.data_quality import QualityCheckJob


def _job(job_id: str) -> QualityCheckJob:
    return QualityCheckJob(
        id=job_id, workspace_id="workspace-1", status="queued", data_version="v1",
        idempotency_key=f"key-{job_id}", parent_run_id="run-1", attempt_count=0,
        created_at=datetime.now(UTC),
    )


@dataclass
class Jobs:
    items: list[QualityCheckJob]

    async def list_dispatchable_quality_checks(self, *, limit: int) -> list[QualityCheckJob]:
        return self.items[:limit]


@dataclass
class Queue:
    accepted: set[str] = field(default_factory=set)

    async def enqueue_once(self, job_id: str) -> bool:
        if job_id in self.accepted:
            return False
        self.accepted.add(job_id)
        return True


def test_dispatcher_rebuilds_only_new_redis_messages() -> None:
    queue = Queue(accepted={"quality-1"})
    dispatcher = QualityTaskDispatcher(Jobs([_job("quality-1"), _job("quality-2")]), queue)

    assert asyncio.run(dispatcher.dispatch_once()) == 1
    assert queue.accepted == {"quality-1", "quality-2"}
