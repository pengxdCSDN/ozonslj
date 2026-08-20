"""同步任务调度应用服务，将到期任务投递到带幂等保护的队列。"""

from backend.app.domain.sync_job import SyncJobGateway, SyncJobQueue


class SyncJobDispatcher:
    """把 PostgreSQL 到期任务投递到可重建队列。"""

    def __init__(self, jobs: SyncJobGateway, queue: SyncJobQueue) -> None:
        """注入任务事实网关和去重队列，保持调度器不依赖具体基础设施。"""
        self._jobs = jobs
        self._queue = queue

    async def dispatch_due_jobs(self, *, limit: int = 100) -> int:
        """返回本轮新增投递数；短期重复任务由队列适配器抑制。"""
        jobs = await self._jobs.list_dispatchable_sync_jobs(limit=limit)
        dispatched = 0
        for job in jobs:
            if await self._queue.enqueue_once(job):
                dispatched += 1
        return dispatched
