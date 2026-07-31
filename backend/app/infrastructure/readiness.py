from redis.asyncio import Redis

from backend.app.infrastructure.postgres.database import PostgresDatabase


class ServiceReadinessProbe:
    """检查 API 必需的 PostgreSQL 与 Redis 连接。"""

    def __init__(self, database: PostgresDatabase, redis: Redis) -> None:
        self._database = database
        self._redis = redis

    async def check(self) -> None:
        await self._database.ping()
        await self._redis.ping()
