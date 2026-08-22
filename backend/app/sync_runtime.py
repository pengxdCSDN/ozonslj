"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import logging
import os
import signal
import socket

from redis.asyncio import Redis

from backend.app.application.composite_quality_runner import CompositeQualityRunner
from backend.app.application.operational_quality_runner import OperationalQualityRunner
from backend.app.application.product_quality_runner import ProductQualityRunner
from backend.app.application.public_snapshot_quality_runner import PublicSnapshotQualityRunner
from backend.app.application.quality_check_worker import QualityCheckWorker
from backend.app.application.quality_task_dispatch import QualityTaskDispatcher
from backend.app.application.rag_evaluation_worker import RagEvaluationWorker
from backend.app.application.rag_worker import RagWorker
from backend.app.application.sync_dispatch import SyncJobDispatcher
from backend.app.application.sync_processes import run_scheduler_loop, run_worker_loop
from backend.app.application.sync_worker import SyncWorker
from backend.app.config import Settings, get_settings
from backend.app.domain.sync_job import SyncHandler, SyncResourceType
from backend.app.infrastructure.observability import METRICS
from backend.app.infrastructure.postgresql.customer_orders import PostgresCustomerOrderGateway
from backend.app.infrastructure.postgresql.data_quality import PostgresQualityFindingGateway
from backend.app.infrastructure.postgresql.postings import PostgresPostingGateway
from backend.app.infrastructure.postgresql.product_offers import PostgresProductOfferGateway
from backend.app.infrastructure.postgresql.public_snapshots import PostgresPublicSnapshotGateway
from backend.app.infrastructure.postgresql.quality_check_jobs import PostgresQualityCheckJobGateway
from backend.app.infrastructure.postgresql.rag_evaluation import PostgresRagEvaluationGateway
from backend.app.infrastructure.postgresql.rag_tasks import PostgresRagTaskGateway
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext
from backend.app.infrastructure.postgresql.stock_positions import PostgresStockPositionGateway
from backend.app.infrastructure.postgresql.sync_jobs import PostgresSyncJobGateway
from backend.app.infrastructure.redis_automation_events import RedisAutomationEventPublisher
from backend.app.infrastructure.redis_quality_tasks import (
    RedisQualityTaskConsumer,
    RedisQualityTaskQueue,
)
from backend.app.infrastructure.redis_rag_evaluation import (
    RedisRagEvaluationTaskConsumer,
    RedisRagEvaluationTaskQueue,
)
from backend.app.infrastructure.redis_rag_tasks import RedisRagTaskConsumer, RedisRagTaskQueue
from backend.app.infrastructure.redis_sync_consumer import RedisSyncJobConsumer
from backend.app.infrastructure.redis_sync_queue import RedisSyncJobQueue
from backend.app.infrastructure.stub_sync_handlers import StubSyncHandler

logger = logging.getLogger(__name__)


def _require_runtime_urls(settings: Settings) -> tuple[str, str]:
    """同步进程同时依赖 PostgreSQL 和 Redis，缺失时必须启动失败。

    Args:
        settings: 参数语义、输入边界和安全约束。

    Returns:
        返回调用完成后的领域结果。

    Raises:
        RuntimeError: 业务约束或外部依赖失败时抛出。
    """
    if settings.database_url is None:
        raise RuntimeError("DATABASE_URL 未配置")
    if settings.redis_url is None:
        raise RuntimeError("REDIS_URL 未配置")
    return str(settings.database_url), str(settings.redis_url)


def _service_context(settings: Settings) -> TenantContext:
    """后台进程只使用部署绑定的固定数据边界，不接受客户端传入组织标识。

    Args:
        settings: 参数语义、输入边界和安全约束。

    Returns:
        返回调用完成后的领域结果。"""
    return TenantContext(settings.default_organization_id, "sync-service")


def _build_handlers(settings: Settings) -> dict[SyncResourceType, SyncHandler]:
    """Stub 环境提供确定性处理器；live 模式不得用空处理器伪装真实同步成功。

    Args:
        settings: 参数语义、输入边界和安全约束。

    Returns:
        返回调用完成后的领域结果。

    Raises:
        RuntimeError: 业务约束或外部依赖失败时抛出。
    """
    if settings.ozon_mode != "stub":
        raise RuntimeError("live 模式的 Ozon 同步处理器尚未配置，拒绝启动 Worker")
    handler = StubSyncHandler()
    return {
        "products": handler,
        "stock": handler,
        "orders": handler,
        "postings": handler,
    }


def _install_shutdown_handlers(stop: asyncio.Event) -> None:
    """把容器 SIGTERM 和终端中断转换为协作式停止信号。

    Args:
        stop: 参数语义、输入边界和安全约束。

    Returns:
        返回调用完成后的领域结果。"""

    def request_stop(_signum: int, _frame: object) -> None:
        """执行 request_stop 的业务流程并返回该流程的结果。

        Args:
            _signum: 参数语义、输入边界和安全约束。
            _frame: 参数语义、输入边界和安全约束。

        Returns:
            返回调用完成后的领域结果。"""
        stop.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, request_stop)


async def run_scheduler(settings: Settings) -> None:
    """组装并运行单组织运营部署的同步调度进程。

    Args:
        settings: 参数语义、输入边界和安全约束。

    Returns:
        返回调用完成后的领域结果。"""
    database_url, redis_url = _require_runtime_urls(settings)
    sessions = PostgresSessionFactory(database_url, max_size=2)
    redis = Redis.from_url(redis_url, decode_responses=True)
    stop = asyncio.Event()
    _install_shutdown_handlers(stop)
    try:
        sessions.open()
        jobs = PostgresSyncJobGateway(sessions, _service_context(settings))
        dispatcher = SyncJobDispatcher(jobs, RedisSyncJobQueue(redis))
        quality_jobs = PostgresQualityCheckJobGateway(sessions, _service_context(settings))
        quality_dispatcher = QualityTaskDispatcher(quality_jobs, RedisQualityTaskQueue(redis))
        rag_tasks = PostgresRagTaskGateway(sessions, _service_context(settings))
        rag_queue = RedisRagTaskQueue(redis)
        evaluation_runs = PostgresRagEvaluationGateway(sessions, _service_context(settings))
        evaluation_queue = RedisRagEvaluationTaskQueue(redis)

        async def dispatch_once() -> int:
            """执行 dispatch_once 的业务流程并返回该流程的结果。
            Returns:
                返回调用完成后的领域结果。"""
            count = await dispatcher.dispatch_due_jobs(limit=settings.sync_dispatch_batch_size)
            METRICS.set_gauge("ozonslj_scheduler_dispatched_jobs", count)
            METRICS.inc("ozonslj_scheduler_cycles_total")
            METRICS.set_gauge(
                "ozonslj_task_queue_stream_length",
                float(await redis.xlen("sync_jobs")),
                labels={"queue": "seller"},
            )
            if count:
                logger.info("同步调度本轮投递 %d 个任务", count)
            quality_count = await quality_dispatcher.dispatch_once(
                limit=settings.sync_dispatch_batch_size
            )
            if quality_count:
                logger.info("质量调度本轮投递 %d 个任务", quality_count)
            METRICS.set_gauge(
                "ozonslj_task_queue_stream_length",
                float(await redis.xlen("quality_check_tasks")),
                labels={"queue": "quality"},
            )
            rag_ids = await rag_tasks.dispatchable_ids(settings.sync_dispatch_batch_size)
            for task_id in rag_ids:
                await rag_queue.enqueue(task_id)
            METRICS.set_gauge(
                "ozonslj_task_queue_stream_length",
                float(await redis.xlen("rag_tasks")),
                labels={"queue": "rag"},
            )
            evaluation_ids = await evaluation_runs.dispatchable_run_ids(
                settings.sync_dispatch_batch_size
            )
            for run_id in evaluation_ids:
                await evaluation_queue.enqueue(run_id)
            METRICS.set_gauge(
                "ozonslj_task_queue_stream_length",
                float(await redis.xlen("rag_evaluation_runs")),
                labels={"queue": "rag-evaluation"},
            )
            return count + quality_count + len(rag_ids) + len(evaluation_ids)

        await run_scheduler_loop(
            dispatch_once,
            stop,
            interval_seconds=settings.sync_dispatch_interval_seconds,
        )
    finally:
        await redis.aclose()
        sessions.close()


async def run_worker(settings: Settings) -> None:
    """组装并运行单并发同步 Worker，最终状态始终先落 PostgreSQL。

    Args:
        settings: 参数语义、输入边界和安全约束。

    Returns:
        返回调用完成后的领域结果。"""
    database_url, redis_url = _require_runtime_urls(settings)
    handlers = _build_handlers(settings)
    sessions = PostgresSessionFactory(database_url, max_size=2)
    redis = Redis.from_url(redis_url, decode_responses=True)
    stop = asyncio.Event()
    _install_shutdown_handlers(stop)
    worker_id = f"{socket.gethostname()}-{os.getpid()}"
    try:
        sessions.open()
        jobs = PostgresSyncJobGateway(sessions, _service_context(settings))
        consumer = RedisSyncJobConsumer(redis, consumer_name=worker_id)
        worker = SyncWorker(
            jobs,
            consumer,
            handlers,
            worker_id=worker_id,
            lease_seconds=settings.sync_worker_lease_seconds,
            retry_delay_seconds=settings.sync_worker_retry_delay_seconds,
            event_publisher=RedisAutomationEventPublisher(redis),
        )

        async def process_one() -> bool:
            """执行 process_one 的业务流程并返回该流程的结果。
            Returns:
                返回调用完成后的领域结果。"""
            processed = await worker.process_one(block_ms=settings.sync_worker_block_ms)
            METRICS.inc(
                "ozonslj_worker_processed_jobs_total",
                labels={"worker": "seller"},
                value=int(processed),
            )
            return processed

        rag_tasks = PostgresRagTaskGateway(sessions, _service_context(settings))
        rag_consumer = RedisRagTaskConsumer(redis, consumer_name=f"rag-{worker_id}")
        rag_worker = RagWorker(
            rag_tasks,
            rag_consumer,
            worker_id=worker_id,
            lease_seconds=settings.sync_worker_lease_seconds,
        )

        async def process_rag_one() -> bool:
            """执行 process_rag_one 的业务流程并返回该流程的结果。
            Returns:
                返回调用完成后的领域结果。"""
            processed = await rag_worker.process_one(block_ms=settings.sync_worker_block_ms)
            METRICS.inc(
                "ozonslj_worker_processed_jobs_total",
                labels={"worker": "rag"},
                value=int(processed),
            )
            return processed

        evaluation_runs = PostgresRagEvaluationGateway(sessions, _service_context(settings))
        evaluation_consumer = RedisRagEvaluationTaskConsumer(
            redis, consumer_name=f"rag-evaluation-{worker_id}"
        )
        evaluation_worker = RagEvaluationWorker(
            evaluation_runs,
            evaluation_consumer,
            worker_id=worker_id,
            lease_seconds=settings.sync_worker_lease_seconds,
        )

        async def process_evaluation_one() -> bool:
            """执行 process_evaluation_one 的业务流程并返回该流程的结果。
            Returns:
                返回调用完成后的领域结果。"""
            processed = await evaluation_worker.process_one(block_ms=settings.sync_worker_block_ms)
            METRICS.inc(
                "ozonslj_worker_processed_jobs_total",
                labels={"worker": "rag-evaluation"},
                value=int(processed),
            )
            return processed

        quality_jobs = PostgresQualityCheckJobGateway(sessions, _service_context(settings))
        quality_findings = PostgresQualityFindingGateway(sessions, _service_context(settings))
        quality_consumer = RedisQualityTaskConsumer(redis, consumer_name=f"quality-{worker_id}")
        quality_runner = CompositeQualityRunner(
            (
                ProductQualityRunner(
                    PostgresProductOfferGateway(sessions, _service_context(settings))
                ),
                OperationalQualityRunner(
                    PostgresStockPositionGateway(sessions, _service_context(settings)),
                    PostgresCustomerOrderGateway(sessions, _service_context(settings)),
                    PostgresPostingGateway(sessions, _service_context(settings)),
                ),
                PublicSnapshotQualityRunner(
                    PostgresPublicSnapshotGateway(sessions, _service_context(settings))
                ),
            )
        )
        quality_worker = QualityCheckWorker(
            quality_jobs,
            quality_findings,
            quality_consumer,
            quality_runner,
            worker_id=worker_id,
            lease_seconds=settings.sync_worker_lease_seconds,
            retry_delay_seconds=settings.sync_worker_retry_delay_seconds,
        )

        async def process_quality_one() -> bool:
            """执行质量检查任务并写回质量隔离记录。"""
            processed = await quality_worker.process_one(block_ms=settings.sync_worker_block_ms)
            METRICS.inc(
                "ozonslj_worker_processed_jobs_total",
                labels={"worker": "quality"},
                value=int(processed),
            )
            return processed

        await asyncio.gather(
            run_worker_loop(process_one, stop),
            run_worker_loop(process_rag_one, stop),
            run_worker_loop(process_evaluation_one, stop),
            run_worker_loop(process_quality_one, stop),
        )
    finally:
        await redis.aclose()
        sessions.close()


def scheduler_main() -> None:
    """执行 scheduler_main 的业务流程并返回该流程的结果。
    Returns:
        返回调用完成后的领域结果。"""
    logging.basicConfig(level=get_settings().log_level)
    asyncio.run(run_scheduler(get_settings()))


def worker_main() -> None:
    """执行 worker_main 的业务流程并返回该流程的结果。
    Returns:
        返回调用完成后的领域结果。"""
    logging.basicConfig(level=get_settings().log_level)
    asyncio.run(run_worker(get_settings()))
