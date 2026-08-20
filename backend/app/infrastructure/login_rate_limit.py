"""说明本模块的职责、边界和主要协作对象。"""

import hashlib

from redis.asyncio import Redis


class RedisLoginRateLimiter:
    """使用 Redis 短期计数限制登录猜测，键名不保存邮箱或客户端地址明文。"""

    def __init__(self, redis: Redis, *, max_attempts: int, window_seconds: int) -> None:
        """初始化对象依赖和运行时状态。"""
        self._redis = redis
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds

    async def retry_after(self, email: str, client_key: str) -> int | None:
        """执行 retry_after 的业务流程并返回该流程的结果。"""
        key = self._key(email, client_key)
        attempts = await self._redis.get(key)
        if attempts is None or int(attempts) < self._max_attempts:
            return None
        ttl = await self._redis.ttl(key)
        return max(int(ttl), 1)

    async def record_failure(self, email: str, client_key: str) -> None:
        """执行 record_failure 的业务流程并返回该流程的结果。"""
        key = self._key(email, client_key)
        attempts = await self._redis.incr(key)
        if attempts == 1:
            await self._redis.expire(key, self._window_seconds)

    async def clear(self, email: str, client_key: str) -> None:
        """执行 clear 的业务流程并返回该流程的结果。"""
        await self._redis.delete(self._key(email, client_key))

    @staticmethod
    def _key(email: str, client_key: str) -> str:
        """执行内部步骤 _key，供同一模块的公开流程复用。"""
        identity = f"{email.strip().lower()}\0{client_key}".encode()
        return f"auth:login:{hashlib.sha256(identity).hexdigest()}"
