from redis.asyncio import Redis

from backend.app.domain.sync_job import SyncJob


class RedisSyncJobQueue:
    """使用 Redis Stream 投递任务，并通过短期键抑制 Scheduler 重复扫描。"""

    def __init__(
        self,
        redis: Redis,
        *,
        stream_name: str = "sync_jobs",
        dedupe_seconds: int = 60,
        maxlen: int = 10_000,
    ) -> None:
        self._redis = redis
        self._stream_name = stream_name
        self._dedupe_seconds = dedupe_seconds
        self._maxlen = maxlen

    async def enqueue_once(self, job: SyncJob) -> bool:
        marker = f"sync:dispatch:{job.id}"
        acquired = await self._redis.set(marker, "1", ex=self._dedupe_seconds, nx=True)
        if not acquired:
            return False
        try:
            await self._redis.xadd(
                self._stream_name,
                {
                    "job_id": job.id,
                    "workspace_id": job.workspace_id,
                    "resource_type": job.resource_type,
                },
                maxlen=self._maxlen,
                approximate=True,
            )
        except Exception:
            # 投递失败必须释放短期标记，让下一轮 Scheduler 可以恢复投递。
            await self._redis.delete(marker)
            raise
        return True
