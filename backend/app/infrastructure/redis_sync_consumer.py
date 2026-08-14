from redis.asyncio import Redis
from redis.exceptions import ResponseError

from backend.app.domain.sync_job import SyncJobMessage


class RedisSyncJobConsumer:
    """Redis Consumer Group 适配器；消息体只读取 job_id。"""

    def __init__(
        self,
        redis: Redis,
        *,
        consumer_name: str,
        stream_name: str = "sync_jobs",
        group_name: str = "sync_workers",
    ) -> None:
        self._redis = redis
        self._consumer_name = consumer_name
        self._stream_name = stream_name
        self._group_name = group_name
        self._group_ready = False

    async def read_one(self, *, block_ms: int) -> SyncJobMessage | None:
        await self._ensure_group()
        streams = await self._redis.xreadgroup(
            self._group_name,
            self._consumer_name,
            {self._stream_name: ">"},
            count=1,
            block=block_ms,
        )
        if not streams:
            return None
        _, messages = streams[0]
        message_id, fields = messages[0]
        job_id = fields.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            await self.acknowledge(str(message_id))
            return None
        return SyncJobMessage(message_id=str(message_id), job_id=job_id)

    async def acknowledge(self, message_id: str) -> None:
        await self._redis.xack(self._stream_name, self._group_name, message_id)

    async def _ensure_group(self) -> None:
        if self._group_ready:
            return
        try:
            await self._redis.xgroup_create(
                self._stream_name, self._group_name, id="0", mkstream=True
            )
        except ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise
        self._group_ready = True
