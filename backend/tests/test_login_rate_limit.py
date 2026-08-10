import asyncio
from typing import cast

from redis.asyncio import Redis

from backend.app.infrastructure.login_rate_limit import RedisLoginRateLimiter


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expiries: dict[str, int] = {}

    async def get(self, key: str) -> int | None:
        return self.values.get(key)

    async def ttl(self, key: str) -> int:
        return self.expiries.get(key, -1)

    async def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expiries[key] = seconds

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)
        self.expiries.pop(key, None)


def test_rate_limit_key_hides_email_and_clears_after_success() -> None:
    redis = FakeRedis()
    limiter = RedisLoginRateLimiter(
        cast(Redis, redis),
        max_attempts=2,
        window_seconds=300,
    )

    asyncio.run(limiter.record_failure("Owner@Example.com", "127.0.0.1"))
    asyncio.run(limiter.record_failure("owner@example.com", "127.0.0.1"))

    key = next(iter(redis.values))
    assert "owner@example.com" not in key
    assert asyncio.run(limiter.retry_after("owner@example.com", "127.0.0.1")) == 300
    asyncio.run(limiter.clear("owner@example.com", "127.0.0.1"))
    assert redis.values == {}
