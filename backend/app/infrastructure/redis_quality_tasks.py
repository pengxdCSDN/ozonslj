"""质量检查任务 Redis Stream 适配器；Redis 仅保存可重建唤醒信号。"""

from redis.asyncio import Redis
from redis.exceptions import ResponseError


class RedisQualityTaskQueue:
    """按质量任务 ID 幂等投递，避免同一任务重复唤醒。"""

    def __init__(self, redis: Redis, *, stream_name: str = "quality_check_tasks") -> None:
        self._redis = redis
        self._stream_name = stream_name

    async def enqueue_once(self, job_id: str) -> bool:
        """短期抑制重复投递；Redis 丢失后由 Scheduler 从 PostgreSQL 恢复。"""
        marker = f"quality:dispatch:{job_id}"
        acquired = await self._redis.set(marker, "1", ex=3600, nx=True)
        if not acquired:
            return False
        try:
            await self._redis.xadd(
                self._stream_name, {"job_id": job_id}, maxlen=10_000, approximate=True
            )
        except Exception:
            await self._redis.delete(marker)
            raise
        return True


class RedisQualityTaskConsumer:
    """Consumer Group 消费质量任务；缺失任务 ID 的毒丸消息会被确认丢弃。"""

    def __init__(
        self,
        redis: Redis,
        *,
        consumer_name: str,
        stream_name: str = "quality_check_tasks",
        group_name: str = "quality_workers",
    ) -> None:
        self._redis = redis
        self._consumer_name = consumer_name
        self._stream_name = stream_name
        self._group_name = group_name
        self._ready = False

    async def read_one(self, *, block_ms: int) -> tuple[str, str] | None:
        await self._ensure_group()
        streams = await self._redis.xreadgroup(
            self._group_name, self._consumer_name, {self._stream_name: ">"},
            count=1, block=block_ms,
        )
        if not streams:
            return None
        message_id, fields = streams[0][1][0]
        job_id = fields.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            await self.acknowledge(str(message_id))
            return None
        return str(message_id), job_id

    async def acknowledge(self, message_id: str) -> None:
        await self._redis.xack(self._stream_name, self._group_name, message_id)

    async def _ensure_group(self) -> None:
        if self._ready:
            return
        try:
            await self._redis.xgroup_create(
                self._stream_name, self._group_name, id="0", mkstream=True
            )
        except ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise
        self._ready = True
