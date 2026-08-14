from backend.app.domain.sync_job import SyncJobGateway, SyncJobQueue


class SyncJobDispatcher:
    """把 PostgreSQL 到期任务投递到可重建队列。"""

    def __init__(self, jobs: SyncJobGateway, queue: SyncJobQueue) -> None:
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
