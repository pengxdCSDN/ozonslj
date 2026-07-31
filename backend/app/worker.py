import asyncio
import logging

from redis.asyncio import Redis

from backend.app.config import get_settings
from backend.app.infrastructure.postgres.database import PostgresDatabase

_CHECK_INTERVAL_SECONDS = 30


async def run_worker() -> None:
    """保持 Worker 进程存活并验证任务依赖，真实同步任务将在后续切片接入。"""

    settings = get_settings()
    database = PostgresDatabase(
        settings.postgres_dsn(),
        min_size=1,
        max_size=2,
    )
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await database.open(seed_offers=())
    try:
        while True:
            await database.ping()
            await redis.ping()
            logging.info("Worker 依赖检查正常")
            await asyncio.sleep(_CHECK_INTERVAL_SECONDS)
    finally:
        await redis.aclose()
        await database.close()


def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
