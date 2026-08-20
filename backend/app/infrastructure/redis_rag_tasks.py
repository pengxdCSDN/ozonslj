"""RAG 任务 Redis Stream 适配器；Redis 只传递任务 ID，不保存任务事实。"""

from redis.asyncio import Redis
from redis.exceptions import ResponseError


class RedisRagTaskQueue:
    """说明 RedisRagTaskQueue 的职责、状态边界和对外协作关系。"""
    def __init__(self, redis: Redis, *, stream_name: str = "rag_tasks") -> None:
        """初始化对象依赖和运行时状态。

Args:
    redis: 参数语义、输入边界和安全约束。
    stream_name: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._redis = redis
        self._stream_name = stream_name

    async def enqueue(self, task_id: str) -> None:
        """执行 enqueue 的业务流程并返回该流程的结果。

Args:
    task_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._redis.xadd(self._stream_name, {"task_id": task_id}, maxlen=10_000)


class RedisRagTaskConsumer:
    """说明 RedisRagTaskConsumer 的职责、状态边界和对外协作关系。"""
    def __init__(self, redis: Redis, *, consumer_name: str,
                 stream_name: str = "rag_tasks", group_name: str = "rag_workers") -> None:
        """初始化对象依赖和运行时状态。

Args:
    redis: 参数语义、输入边界和安全约束。
    consumer_name: 参数语义、输入边界和安全约束。
    stream_name: 参数语义、输入边界和安全约束。
    group_name: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._redis = redis
        self._consumer_name = consumer_name
        self._stream_name = stream_name
        self._group_name = group_name
        self._ready = False

    async def read_one(self, *, block_ms: int) -> tuple[str, str] | None:
        """执行 read_one 的业务流程并返回该流程的结果。

Args:
    block_ms: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
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
        """执行 acknowledge 的业务流程并返回该流程的结果。

Args:
    message_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await self._redis.xack(self._stream_name, self._group_name, message_id)

    async def _ensure_group(self) -> None:
        """执行内部步骤 _ensure_group，供同一模块的公开流程复用。
Returns:
    返回调用完成后的领域结果。"""
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
