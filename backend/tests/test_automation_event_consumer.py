"""自动化事件 Consumer Group 的字段校验和毒丸消息测试。"""

import asyncio
from typing import cast

from redis.asyncio import Redis

from backend.app.infrastructure.redis_automation_events import RedisAutomationEventConsumer


class FakeConsumerRedis:
    def __init__(self, fields: dict[str, str]) -> None:
        self.fields = fields
        self.acked: list[str] = []
        self.created = False

    async def xgroup_create(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        self.created = True

    async def xreadgroup(self, *args: object, **kwargs: object) -> list[object]:
        del args, kwargs
        return [["automation_events", [("1-0", self.fields)]]]

    async def xack(self, stream: str, group: str, message_id: str) -> int:
        del stream, group
        self.acked.append(message_id)
        return 1


def _fields() -> dict[str, str]:
    return {
        "event_id": "run-1:external_fact_changed",
        "event_type": "external_fact_changed",
        "workspace_id": "workspace-1",
        "run_id": "run-1",
        "root_run_id": "run-1",
        "source": "stock",
        "data_version": "version-1",
    }


def test_consumer_parses_valid_event_and_creates_group() -> None:
    redis = FakeConsumerRedis(_fields())
    consumer = RedisAutomationEventConsumer(cast(Redis, redis), consumer_name="worker-1")

    message = asyncio.run(consumer.read_one(block_ms=1))

    assert message is not None
    assert message.event.event_id == "run-1:external_fact_changed"
    assert redis.created is True
    assert redis.acked == []


def test_consumer_acknowledges_invalid_event_without_poisoning_stream() -> None:
    fields = _fields()
    fields.pop("data_version")
    redis = FakeConsumerRedis(fields)
    consumer = RedisAutomationEventConsumer(cast(Redis, redis), consumer_name="worker-1")

    assert asyncio.run(consumer.read_one(block_ms=1)) is None
    assert redis.acked == ["1-0"]


def test_consumer_rejects_non_fact_event() -> None:
    fields = _fields()
    fields["event_type"] = "display_refreshed"
    redis = FakeConsumerRedis(fields)
    consumer = RedisAutomationEventConsumer(cast(Redis, redis), consumer_name="worker-1")

    assert asyncio.run(consumer.read_one(block_ms=1)) is None
    assert redis.acked == ["1-0"]
