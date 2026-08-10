import asyncio

from redis.asyncio import Redis

from backend.app.infrastructure.postgresql.session import PostgresSessionFactory


class InfrastructureReadinessProbe:
    """并行验证 PostgreSQL 与 Redis；任一失败都不得报告服务就绪。"""

    def __init__(self, sessions: PostgresSessionFactory, redis: Redis) -> None:
        self._sessions = sessions
        self._redis = redis

    async def check(self) -> None:
        postgresql_check = asyncio.to_thread(self._sessions.check)
        redis_check = self._redis.ping()
        await asyncio.gather(postgresql_check, redis_check)
