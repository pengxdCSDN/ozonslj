"""说明本模块的职责、边界和主要协作对象。"""

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
    # 自动化编排上下文：旧任务允许为空，新增任务由应用层填充，便于追踪触发链。
    run_id: str | None = None
    root_run_id: str | None = None
    parent_run_id: str | None = None
    trigger_source: str = "manual"
    data_version: str | None = None
    trigger_depth: int = Field(default=0, ge=0)


class SyncJobPage(BaseModel):
    """按工作区倒序返回同步任务历史；错误字段已由 Worker 脱敏。"""

    items: list[SyncJob]
    total: int = Field(ge=0)
    next_cursor: str | None = None


class SyncJobGateway(Protocol):
    """说明 SyncJobGateway 的职责、状态边界和对外协作关系。"""
    async def create_sync_job(
        self,
        *,
        workspace_id: str,
        resource_type: SyncResourceType,
        idempotency_key: str,
    ) -> SyncJob:
        """执行 create_sync_job 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    resource_type: 参数语义、输入边界和安全约束。
    idempotency_key: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def get_sync_job(self, job_id: str) -> SyncJob | None:
        """执行 get_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_sync_jobs(
        self, *, workspace_id: str, cursor: str | None, limit: int
    ) -> SyncJobPage:
        """执行 list_sync_jobs 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    cursor: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def request_cancel_sync_job(self, *, job_id: str) -> bool:
        """执行 request_cancel_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def retry_sync_job(self, *, job_id: str) -> SyncJob | None:
        """执行 retry_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_dispatchable_sync_jobs(self, *, limit: int) -> list[SyncJob]:
        """执行 list_dispatchable_sync_jobs 的业务流程并返回该流程的结果。

Args:
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def claim_sync_job(
        self, *, job_id: str, worker_id: str, lease_seconds: int
    ) -> SyncJob | None:
        """执行 claim_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    lease_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def heartbeat_sync_job(
        self, *, job_id: str, worker_id: str, lease_seconds: int
    ) -> bool:
        """执行 heartbeat_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    lease_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def complete_sync_job(
        self, *, job_id: str, worker_id: str, processed_count: int, failure_count: int
    ) -> bool:
        """执行 complete_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    processed_count: 参数语义、输入边界和安全约束。
    failure_count: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def fail_sync_job(
        self,
        *,
        job_id: str,
        worker_id: str,
        error_code: str,
        error_message: str,
        retry_delay_seconds: int,
    ) -> bool:
        """执行 fail_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    error_code: 参数语义、输入边界和安全约束。
    error_message: 参数语义、输入边界和安全约束。
    retry_delay_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


class SyncJobQueue(Protocol):
    """可重建的任务投递端口；实现不得保存唯一业务状态。"""

    async def enqueue_once(self, job: SyncJob) -> bool:
        """执行 enqueue_once 的业务流程并返回该流程的结果。

Args:
    job: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


class SyncJobMessage(BaseModel):
    """Redis 只携带定位任务所需的最小消息。"""

    model_config = ConfigDict(frozen=True)

    message_id: str
    job_id: str


class SyncJobConsumer(Protocol):
    """说明 SyncJobConsumer 的职责、状态边界和对外协作关系。"""
    async def read_one(self, *, block_ms: int) -> SyncJobMessage | None:
        """执行 read_one 的业务流程并返回该流程的结果。

Args:
    block_ms: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def acknowledge(self, message_id: str) -> None:
        """执行 acknowledge 的业务流程并返回该流程的结果。

Args:
    message_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


class SyncResult(BaseModel):
    """说明 SyncResult 的职责、状态边界和对外协作关系。"""
    model_config = ConfigDict(frozen=True)

    processed_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)


class SyncHandler(Protocol):
    """说明 SyncHandler 的职责、状态边界和对外协作关系。"""
    async def run(self, job: SyncJob) -> SyncResult:
        """执行 run 的业务流程并返回该流程的结果。

Args:
    job: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
