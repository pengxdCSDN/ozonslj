"""质量任务 Redis 队列的幂等投递和毒丸消息测试。"""

import asyncio
from typing import cast

from redis.asyncio import Redis

from backend.app.infrastructure.redis_quality_tasks import (
    RedisQualityTaskConsumer,
    RedisQualityTaskQueue,
)


class FakeRedis:
    def __init__(self, *, acquired: bool = True, fields: dict[str, str] | None = None) -> None:
        self.acquired = acquired
        self.fields = {"job_id": "quality-1"} if fields is None else fields
        self.deleted: list[str] = []
        self.acked: list[str] = []
        self.added: list[tuple[str, dict[str, str]]] = []

    async def set(self, *args: object, **kwargs: object) -> bool:
        del args, kwargs
        return self.acquired

    async def xadd(self, stream: str, fields: dict[str, str], **kwargs: object) -> str:
        del kwargs
        self.added.append((stream, fields))
        return "1-0"

    async def delete(self, key: str) -> int:
        self.deleted.append(key)
        return 1

    async def xgroup_create(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    async def xreadgroup(self, *args: object, **kwargs: object) -> list[object]:
        del args, kwargs
        return [["quality_check_tasks", [("1-0", self.fields)]]]

    async def xack(self, stream: str, group: str, message_id: str) -> int:
        del stream, group
        self.acked.append(message_id)
        return 1


def test_quality_task_queue_suppresses_duplicate() -> None:
    redis = FakeRedis(acquired=False)
    queue = RedisQualityTaskQueue(cast(Redis, redis))
    assert asyncio.run(queue.enqueue_once("quality-1")) is False
    assert redis.added == []


def test_quality_task_consumer_reads_valid_job() -> None:
    redis = FakeRedis()
    consumer = RedisQualityTaskConsumer(cast(Redis, redis), consumer_name="worker-1")
    assert asyncio.run(consumer.read_one(block_ms=1)) == ("1-0", "quality-1")


def test_quality_task_consumer_acknowledges_poison_message() -> None:
    redis = FakeRedis(fields={})
    consumer = RedisQualityTaskConsumer(cast(Redis, redis), consumer_name="worker-1")
    assert asyncio.run(consumer.read_one(block_ms=1)) is None
    assert redis.acked == ["1-0"]
