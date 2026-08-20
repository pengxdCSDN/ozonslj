"""基础设施就绪检查，验证 PostgreSQL 和 Redis 是否同时可用。"""

import asyncio

from redis.asyncio import Redis

from backend.app.infrastructure.postgresql.session import PostgresSessionFactory


class InfrastructureReadinessProbe:
    """并行验证 PostgreSQL 与 Redis；任一失败都不得报告服务就绪。"""

    def __init__(self, sessions: PostgresSessionFactory, redis: Redis) -> None:
        """保存 PostgreSQL 会话工厂和 Redis 客户端，供就绪检查复用。"""
        self._sessions = sessions
        self._redis = redis

    async def check(self) -> None:
        """并行执行依赖检查；任一依赖异常都会向上抛出并阻止就绪。"""
        postgresql_check = asyncio.to_thread(self._sessions.check)
        redis_check = self._redis.ping()
        await asyncio.gather(postgresql_check, redis_check)
