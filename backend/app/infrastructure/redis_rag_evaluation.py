"""RAG 评测队列 Redis 适配器；Redis 只传递运行 ID，运行事实保存在 PostgreSQL。"""

from redis.asyncio import Redis
from redis.exceptions import ResponseError


class RedisRagEvaluationTaskQueue:
    """向独立 Stream 投递评测运行，避免与知识索引任务互相消费。"""

    def __init__(self, redis: Redis, *, stream_name: str = "rag_evaluation_runs") -> None:
        self._redis = redis
        self._stream_name = stream_name

    async def enqueue(self, run_id: str) -> None:
        await self._redis.xadd(self._stream_name, {"run_id": run_id}, maxlen=10_000)


class RedisRagEvaluationTaskConsumer:
    """消费评测运行 ID；重复唤醒由 PostgreSQL claim 原子排除。"""

    def __init__(
        self,
        redis: Redis,
        *,
        consumer_name: str,
        stream_name: str = "rag_evaluation_runs",
        group_name: str = "rag_evaluation_workers",
    ) -> None:
        self._redis = redis
        self._consumer_name = consumer_name
        self._stream_name = stream_name
        self._group_name = group_name
        self._ready = False

    async def read_one(self, *, block_ms: int) -> tuple[str, str] | None:
        await self._ensure_group()
        # Worker 崩溃后消息会留在旧消费者的 pending 列表；先接管超过 30 秒的消息，
        # 否则新 Worker 永远只读到 “>”，旧消息会长期占用队列监控并阻断恢复。
        claimed = await self._redis.xautoclaim(
            self._stream_name, self._group_name, self._consumer_name,
            min_idle_time=30_000, start_id="0-0", count=1,
        )
        pending = claimed[1]
        if pending:
            message_id, fields = pending[0]
            run_id = fields.get("run_id")
            if isinstance(run_id, str) and run_id:
                return str(message_id), run_id
            await self.acknowledge(str(message_id))
        streams = await self._redis.xreadgroup(
            self._group_name, self._consumer_name, {self._stream_name: ">"},
            count=1, block=block_ms,
        )
        if not streams:
            return None
        message_id, fields = streams[0][1][0]
        run_id = fields.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            await self.acknowledge(str(message_id))
            return None
        return str(message_id), run_id

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
