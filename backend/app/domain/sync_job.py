from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

SyncResourceType = Literal["products", "stock", "orders", "postings"]
SyncJobStatus = Literal["queued", "running", "succeeded", "partial", "failed", "cancelled"]


class SyncJob(BaseModel):
    """PostgreSQL 中可恢复的同步任务状态。"""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    resource_type: SyncResourceType
    status: SyncJobStatus
    processed_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    error_code: str | None = None
    error_message: str | None = None
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1, le=10)
    next_attempt_at: datetime
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    heartbeat_at: datetime | None = None


class SyncJobPage(BaseModel):
    """按工作区倒序返回同步任务历史；错误字段已由 Worker 脱敏。"""

    items: list[SyncJob]
    total: int = Field(ge=0)
    next_cursor: str | None = None


class SyncJobGateway(Protocol):
    async def create_sync_job(
        self,
        *,
        workspace_id: str,
        resource_type: SyncResourceType,
        idempotency_key: str,
    ) -> SyncJob: ...

    async def get_sync_job(self, job_id: str) -> SyncJob | None: ...

    async def list_sync_jobs(
        self, *, workspace_id: str, cursor: str | None, limit: int
    ) -> SyncJobPage: ...

    async def request_cancel_sync_job(self, *, job_id: str) -> bool: ...

    async def retry_sync_job(self, *, job_id: str) -> SyncJob | None: ...

    async def list_dispatchable_sync_jobs(self, *, limit: int) -> list[SyncJob]: ...

    async def claim_sync_job(
        self, *, job_id: str, worker_id: str, lease_seconds: int
    ) -> SyncJob | None: ...

    async def heartbeat_sync_job(
        self, *, job_id: str, worker_id: str, lease_seconds: int
    ) -> bool: ...

    async def complete_sync_job(
        self, *, job_id: str, worker_id: str, processed_count: int, failure_count: int
    ) -> bool: ...

    async def fail_sync_job(
        self,
        *,
        job_id: str,
        worker_id: str,
        error_code: str,
        error_message: str,
        retry_delay_seconds: int,
    ) -> bool: ...


class SyncJobQueue(Protocol):
    """可重建的任务投递端口；实现不得保存唯一业务状态。"""

    async def enqueue_once(self, job: SyncJob) -> bool: ...


class SyncJobMessage(BaseModel):
    """Redis 只携带定位任务所需的最小消息。"""

    model_config = ConfigDict(frozen=True)

    message_id: str
    job_id: str


class SyncJobConsumer(Protocol):
    async def read_one(self, *, block_ms: int) -> SyncJobMessage | None: ...

    async def acknowledge(self, message_id: str) -> None: ...


class SyncResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    processed_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)


class SyncHandler(Protocol):
    async def run(self, job: SyncJob) -> SyncResult: ...
