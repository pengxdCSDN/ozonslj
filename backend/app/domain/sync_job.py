from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

SyncResourceType = Literal["products", "stocks", "orders", "postings", "all"]
SyncMode = Literal["initial", "incremental", "reconcile"]
SyncJobStatus = Literal["queued", "running", "succeeded", "partial", "failed", "cancelled"]


class SyncJobAlreadyActiveError(RuntimeError):
    """同一工作区已有排队中或运行中的同步任务。"""


class SyncJob(BaseModel):
    """提交给后台 Worker 的同步任务摘要。"""

    model_config = ConfigDict(frozen=True)

    id: str
    workspace_id: str
    resource_type: SyncResourceType
    sync_mode: SyncMode
    status: SyncJobStatus
    created_at: datetime


class SyncJobGateway(Protocol):
    async def create_sync_job(
        self,
        *,
        workspace_id: str,
        resource_type: SyncResourceType,
        sync_mode: SyncMode,
        requested_by: str,
    ) -> SyncJob: ...
