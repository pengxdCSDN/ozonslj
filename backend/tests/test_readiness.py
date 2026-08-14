import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock

from redis.asyncio import Redis

from backend.app.infrastructure.postgresql.session import PostgresSessionFactory
from backend.app.infrastructure.readiness import InfrastructureReadinessProbe


def test_probe_checks_postgresql_and_redis() -> None:
    sessions = MagicMock()
    redis = MagicMock()
    redis.ping = AsyncMock(return_value=True)
    probe = InfrastructureReadinessProbe(
        cast(PostgresSessionFactory, sessions),
        cast(Redis, redis),
    )

    asyncio.run(probe.check())

    sessions.check.assert_called_once_with()
    redis.ping.assert_awaited_once_with()
