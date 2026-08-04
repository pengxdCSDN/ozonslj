import asyncio
import logging

from redis.asyncio import Redis

from backend.app.application.sync_worker import (
    LiveSyncJobHandler,
    StubSyncJobHandler,
    SyncWorker,
)
from backend.app.config import get_settings
from backend.app.infrastructure.postgres.database import PostgresDatabase
from backend.app.infrastructure.postgres.sync_jobs import PostgresSyncJobGateway

_DEPENDENCY_CHECK_INTERVAL_SECONDS = 30


async def run_worker() -> None:
    """领取同步任务，并在空闲期周期性验证 PostgreSQL 与 Redis。"""

    settings = get_settings()
    database = PostgresDatabase(
        settings.postgres_dsn(),
        min_size=1,
        max_size=2,
    )
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await database.open(seed_offers=())
    handler = StubSyncJobHandler() if settings.ozon_mode == "stub" else LiveSyncJobHandler()
    worker = SyncWorker(
        PostgresSyncJobGateway(database.pool),
        handler,
        lease_seconds=settings.sync_lease_seconds,
        heartbeat_seconds=settings.sync_heartbeat_seconds,
    )
    last_dependency_check = 0.0
    try:
        while True:
            processed = await worker.run_once()
            now = asyncio.get_running_loop().time()
            if now - last_dependency_check >= _DEPENDENCY_CHECK_INTERVAL_SECONDS:
                await database.ping()
                await redis.ping()
                last_dependency_check = now
            if not processed:
                await asyncio.sleep(settings.worker_poll_seconds)
    finally:
        await redis.aclose()
        await database.close()


def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
