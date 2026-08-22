"""质量任务 Scheduler 调度应用服务。"""

from typing import Protocol

from backend.app.domain.data_quality import QualityCheckJobGateway


class QualityTaskQueue(Protocol):
    """质量任务 Redis 投递端口。"""

    async def enqueue_once(self, job_id: str) -> bool:
        """按任务 ID 幂等投递。"""


class QualityTaskDispatcher:
    """从 PostgreSQL 任务事实重建质量任务 Redis 投递。"""

    def __init__(self, jobs: QualityCheckJobGateway, queue: QualityTaskQueue) -> None:
        self._jobs = jobs
        self._queue = queue

    async def dispatch_once(self, *, limit: int = 100) -> int:
        """投递一轮到期任务，返回新增 Redis 消息数量。"""
        if not 1 <= limit <= 500:
            raise ValueError("质量任务调度批量大小必须在 1 到 500 之间")
        jobs = await self._jobs.list_dispatchable_quality_checks(limit=limit)
        count = 0
        for job in jobs:
            if await self._queue.enqueue_once(job.id):
                count += 1
        return count
