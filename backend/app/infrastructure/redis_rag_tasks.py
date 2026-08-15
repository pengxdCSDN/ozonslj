"""RAG 任务 Redis Stream 适配器；Redis 只传递任务 ID，不保存任务事实。"""

from redis.asyncio import Redis
from redis.exceptions import ResponseError


class RedisRagTaskQueue:
    def __init__(self, redis: Redis, *, stream_name: str = "rag_tasks") -> None:
        self._redis = redis
        self._stream_name = stream_name

    async def enqueue(self, task_id: str) -> None:
        await self._redis.xadd(self._stream_name, {"task_id": task_id}, maxlen=10_000)


class RedisRagTaskConsumer:
    def __init__(self, redis: Redis, *, consumer_name: str,
                 stream_name: str = "rag_tasks", group_name: str = "rag_workers") -> None:
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
        task_id = fields.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            await self.acknowledge(str(message_id))
            return None
        return str(message_id), task_id

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
