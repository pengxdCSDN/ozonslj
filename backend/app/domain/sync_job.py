from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

SyncResourceType = Literal["products", "stocks", "orders", "postings", "all"]
SyncMode = Literal["initial", "incremental", "reconcile"]
SyncJobStatus = Literal["queued", "running", "succeeded", "partial", "failed", "cancelled"]


class SyncJobAlreadyActiveError(RuntimeError):
    """同一工作区已有排队中或运行中的同步任务。"""


class SyncJobLeaseLostError(RuntimeError):
    """当前 Worker 的任务租约已过期或被其他尝试接管。"""


class SyncJob(BaseModel):
    """提交给后台 Worker 的同步任务摘要。"""

    model_config = ConfigDict(frozen=True)

    id: str
    workspace_id: str
    resource_type: SyncResourceType
    sync_mode: SyncMode
    status: SyncJobStatus
    created_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


class ClaimedSyncJob(SyncJob):
    """Worker 已领取任务；attempt_count 是状态写入的栅栏令牌。"""

    attempt_count: int


class SyncJobGateway(Protocol):
    async def create_sync_job(
        self,
        *,
        workspace_id: str,
        resource_type: SyncResourceType,
        sync_mode: SyncMode,
        requested_by: str,
    ) -> SyncJob: ...

    async def get_sync_job(
        self,
        *,
        job_id: str,
        workspace_ids: tuple[str, ...],
    ) -> SyncJob | None: ...


class SyncJobRunnerGateway(Protocol):
    async def claim_next(self, *, lease_seconds: int) -> ClaimedSyncJob | None: ...

    async def heartbeat(self, job: ClaimedSyncJob, *, lease_seconds: int) -> None: ...

    async def mark_succeeded(self, job: ClaimedSyncJob) -> None: ...

    async def mark_failed(self, job: ClaimedSyncJob, *, code: str, message: str) -> None: ...
