import asyncio
import logging
from contextlib import suppress
from typing import Protocol

from backend.app.domain.sync_job import ClaimedSyncJob, SyncJobRunnerGateway

logger = logging.getLogger(__name__)


class SyncExecutionError(RuntimeError):
    """可安全返回到任务记录的同步执行错误。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


class SyncJobHandler(Protocol):
    async def execute(self, job: ClaimedSyncJob) -> None: ...


class StubSyncJobHandler:
    """Stub 数据在启动时已写入，任务仅验证完整状态流转。"""

    async def execute(self, job: ClaimedSyncJob) -> None:
        await asyncio.sleep(0)


class LiveSyncJobHandler:
    """真实 Ozon 适配器接入前明确失败，不伪造同步成功。"""

    async def execute(self, job: ClaimedSyncJob) -> None:
        raise SyncExecutionError("LIVE_SYNC_NOT_IMPLEMENTED", "真实 Ozon 同步适配器尚未启用")


class SyncWorker:
    """领取一个任务并在租约保护下执行，适合低资源单进程 Worker。"""

    def __init__(
        self,
        gateway: SyncJobRunnerGateway,
        handler: SyncJobHandler,
        *,
        lease_seconds: int,
        heartbeat_seconds: int,
    ) -> None:
        if heartbeat_seconds >= lease_seconds:
            raise ValueError("同步心跳间隔必须小于租约时长")
        self._gateway = gateway
        self._handler = handler
        self._lease_seconds = lease_seconds
        self._heartbeat_seconds = heartbeat_seconds

    async def run_once(self) -> bool:
        job = await self._gateway.claim_next(lease_seconds=self._lease_seconds)
        if job is None:
            return False

        heartbeat_task = asyncio.create_task(self._keep_lease(job))
        try:
            await self._handler.execute(job)
        except SyncExecutionError as error:
            await self._gateway.mark_failed(job, code=error.code, message=error.safe_message)
        except Exception:
            logger.error("同步任务发生未分类错误，任务编号=%s", job.id)
            await self._gateway.mark_failed(
                job,
                code="UNEXPECTED_SYNC_ERROR",
                message="同步任务发生未分类错误",
            )
        else:
            await self._gateway.mark_succeeded(job)
        finally:
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task
        return True

    async def _keep_lease(self, job: ClaimedSyncJob) -> None:
        while True:
            await asyncio.sleep(self._heartbeat_seconds)
            await self._gateway.heartbeat(job, lease_seconds=self._lease_seconds)
