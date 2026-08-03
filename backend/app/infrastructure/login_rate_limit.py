import hashlib

from redis.asyncio import Redis


class RedisLoginRateLimiter:
    """使用 Redis 短期计数限制登录猜测，不在键中保存邮箱明文。"""

    def __init__(self, redis: Redis, *, max_attempts: int, window_seconds: int) -> None:
        self._redis = redis
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds

    async def retry_after(self, email: str, client_key: str) -> int | None:
        key = self._key(email, client_key)
        attempts = await self._redis.get(key)
        if attempts is None or int(attempts) < self._max_attempts:
            return None
        ttl = await self._redis.ttl(key)
        return max(int(ttl), 1)

    async def record_failure(self, email: str, client_key: str) -> None:
        key = self._key(email, client_key)
        attempts = await self._redis.incr(key)
        if attempts == 1:
            await self._redis.expire(key, self._window_seconds)

    async def clear(self, email: str, client_key: str) -> None:
        await self._redis.delete(self._key(email, client_key))

    @staticmethod
    def _key(email: str, client_key: str) -> str:
        identity = f"{email.strip().lower()}\0{client_key}".encode()
        return f"auth:login:{hashlib.sha256(identity).hexdigest()}"
