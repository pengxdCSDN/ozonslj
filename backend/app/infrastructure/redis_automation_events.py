"""自动化事件 Redis Stream 适配器。

Redis 只负责可重建的事件唤醒，不保存业务事实。事件以稳定 event_id 做短期幂等，
重复投递返回 False；投递失败会释放去重标记，使后续 Scheduler/Worker 可以安全恢复。
"""

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from backend.app.domain.automation_orchestration import AutomationEvent, AutomationEventMessage


class RedisAutomationEventPublisher:
    """发布脱敏自动化事件，并抑制相同 event_id 的重复消息。"""

    def __init__(
        self,
        redis: Redis,
        *,
        stream_name: str = "automation_events",
        dedupe_seconds: int = 3_600,
        maxlen: int = 10_000,
    ) -> None:
        """配置事件流、幂等标记保留时间和 Stream 长度上限。"""
        if dedupe_seconds < 1 or maxlen < 1:
            raise ValueError("自动化事件队列参数必须为正数")
        self._redis = redis
        self._stream_name = stream_name
        self._dedupe_seconds = dedupe_seconds
        self._maxlen = maxlen

    async def publish_once(self, event: AutomationEvent) -> bool:
        """按 event_id 幂等发布；失败时释放标记，禁止留下假成功状态。"""
        marker = f"automation:event:{event.event_id}"
        acquired = await self._redis.set(marker, "1", ex=self._dedupe_seconds, nx=True)
        if not acquired:
            return False
        try:
            await self._redis.xadd(
                self._stream_name,
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "workspace_id": event.workspace_id,
                    "run_id": event.run_id,
                    "root_run_id": event.root_run_id,
                    "source": event.source,
                    "data_version": event.data_version,
                },
                maxlen=self._maxlen,
                approximate=True,
            )
        except Exception:
            await self._redis.delete(marker)
            raise
        return True


class RedisAutomationEventConsumer:
    """以 Consumer Group 消费事实变化事件；非法消息确认后丢弃，避免毒丸阻塞队列。"""

    def __init__(
        self,
        redis: Redis,
        *,
        consumer_name: str,
        stream_name: str = "automation_events",
        group_name: str = "automation_workers",
    ) -> None:
        self._redis = redis
        self._consumer_name = consumer_name
        self._stream_name = stream_name
        self._group_name = group_name
        self._group_ready = False

    async def read_one(self, *, block_ms: int) -> AutomationEventMessage | None:
        """读取一条事件；字段不完整时确认并跳过，不把非法输入交给业务层。"""
        await self._ensure_group()
        streams = await self._redis.xreadgroup(
            self._group_name, self._consumer_name, {self._stream_name: ">"},
            count=1, block=block_ms,
        )
        if not streams:
            return None
        message_id, fields = streams[0][1][0]
        required = (
            "event_id", "event_type", "workspace_id", "run_id", "root_run_id",
            "source", "data_version",
        )
        if not all(isinstance(fields.get(name), str) and fields[name] for name in required):
            await self.acknowledge(str(message_id))
            return None
        event_type = fields["event_type"]
        if event_type != "external_fact_changed":
            await self.acknowledge(str(message_id))
            return None
        return AutomationEventMessage(
            message_id=str(message_id),
            event=AutomationEvent(
                event_id=fields["event_id"], event_type="external_fact_changed",
                workspace_id=fields["workspace_id"], run_id=fields["run_id"],
                root_run_id=fields["root_run_id"], source=fields["source"],
                data_version=fields["data_version"],
            ),
        )

    async def acknowledge(self, message_id: str) -> None:
        """确认消息；业务事实仍由 PostgreSQL 保存。"""
        await self._redis.xack(self._stream_name, self._group_name, message_id)

    async def _ensure_group(self) -> None:
        """幂等创建 Consumer Group，Stream 不存在时由 Redis 自动创建。"""
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
