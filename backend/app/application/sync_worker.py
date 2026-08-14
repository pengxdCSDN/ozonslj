import asyncio
from contextlib import suppress

from backend.app.domain.sync_job import (
    SyncHandler,
    SyncJobConsumer,
    SyncJobGateway,
    SyncResourceType,
)


class SyncWorker:
    """消费最小任务消息，以 PostgreSQL 租约保护同步处理。"""

    def __init__(
        self,
        jobs: SyncJobGateway,
        consumer: SyncJobConsumer,
        handlers: dict[SyncResourceType, SyncHandler],
        *,
        worker_id: str,
        lease_seconds: int = 30,
        retry_delay_seconds: int = 60,
    ) -> None:
        self._jobs = jobs
        self._consumer = consumer
        self._handlers = handlers
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds
        self._retry_delay_seconds = retry_delay_seconds

    async def process_one(self, *, block_ms: int = 1_000) -> bool:
        message = await self._consumer.read_one(block_ms=block_ms)
        if message is None:
            return False
        job = await self._jobs.claim_sync_job(
            job_id=message.job_id,
            worker_id=self._worker_id,
            lease_seconds=self._lease_seconds,
        )
        if job is None:
            await self._consumer.acknowledge(message.message_id)
            return True

        heartbeat = asyncio.create_task(self._heartbeat(job.id))
        try:
            handler = self._handlers.get(job.resource_type)
            if handler is None:
                persisted = await self._jobs.fail_sync_job(
                    job_id=job.id,
                    worker_id=self._worker_id,
                    error_code="handler_not_configured",
                    error_message="同步处理器未配置",
                    retry_delay_seconds=self._retry_delay_seconds,
                )
            else:
                try:
                    result = await handler.run(job)
                except Exception:
                    # 外部异常不得原样写入任务，避免凭据或敏感响应进入错误摘要。
                    persisted = await self._jobs.fail_sync_job(
                        job_id=job.id,
                        worker_id=self._worker_id,
                        error_code="sync_handler_failed",
                        error_message="同步处理失败",
                        retry_delay_seconds=self._retry_delay_seconds,
                    )
                else:
                    persisted = await self._jobs.complete_sync_job(
                        job_id=job.id,
                        worker_id=self._worker_id,
                        processed_count=result.processed_count,
                        failure_count=result.failure_count,
                    )
            if persisted:
                await self._consumer.acknowledge(message.message_id)
            return persisted
        finally:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat

    async def _heartbeat(self, job_id: str) -> None:
        interval = max(self._lease_seconds // 3, 1)
        while True:
            await asyncio.sleep(interval)
            renewed = await self._jobs.heartbeat_sync_job(
                job_id=job_id,
                worker_id=self._worker_id,
                lease_seconds=self._lease_seconds,
            )
            if not renewed:
                return
