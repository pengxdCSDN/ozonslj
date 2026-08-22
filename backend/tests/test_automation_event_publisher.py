"""自动化事件 Redis 发布适配器的幂等和失败恢复测试。"""

import asyncio
from typing import cast

import pytest
from redis.asyncio import Redis

from backend.app.domain.automation_orchestration import AutomationEvent
from backend.app.infrastructure.redis_automation_events import RedisAutomationEventPublisher


class FakeRedis:
    def __init__(self, *, fail_xadd: bool = False, acquired: bool = True) -> None:
        self.fail_xadd = fail_xadd
        self.acquired = acquired
        self.deleted: list[str] = []
        self.added: list[tuple[str, dict[str, str]]] = []

    async def set(self, key: str, value: str, *, ex: int, nx: bool) -> bool:
        del key, value, ex, nx
        return self.acquired

    async def xadd(self, stream: str, fields: dict[str, str], **kwargs: object) -> str:
        del kwargs
        if self.fail_xadd:
            raise RuntimeError("redis unavailable")
        self.added.append((stream, fields))
        return "1-0"

    async def delete(self, key: str) -> int:
        self.deleted.append(key)
        return 1


def _event() -> AutomationEvent:
    return AutomationEvent(
        event_id="run-1:external_fact_changed",
        event_type="external_fact_changed",
        workspace_id="workspace-1",
        run_id="run-1",
        root_run_id="run-1",
        source="stock",
        data_version="version-1",
    )


def test_event_publisher_writes_sanitized_event_once() -> None:
    redis = FakeRedis()
    publisher = RedisAutomationEventPublisher(cast(Redis, redis))

    assert asyncio.run(publisher.publish_once(_event())) is True
    assert redis.added[0][0] == "automation_events"
    assert redis.added[0][1]["event_id"] == "run-1:external_fact_changed"


def test_duplicate_event_id_is_suppressed() -> None:
    redis = FakeRedis(acquired=False)
    publisher = RedisAutomationEventPublisher(cast(Redis, redis))

    assert asyncio.run(publisher.publish_once(_event())) is False
    assert redis.added == []


def test_failed_event_publish_releases_dedupe_marker() -> None:
    redis = FakeRedis(fail_xadd=True)
    publisher = RedisAutomationEventPublisher(cast(Redis, redis))

    with pytest.raises(RuntimeError, match="redis unavailable"):
        asyncio.run(publisher.publish_once(_event()))
    assert redis.deleted == ["automation:event:run-1:external_fact_changed"]
