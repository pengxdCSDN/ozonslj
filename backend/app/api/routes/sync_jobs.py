"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from pydantic import BaseModel

from backend.app.api.dependencies import get_store_workspace_gateway, get_sync_job_gateway
from backend.app.domain.store_workspace import StoreWorkspaceGateway
from backend.app.domain.sync_job import SyncJob, SyncJobGateway, SyncJobPage, SyncResourceType

router = APIRouter(tags=["sync-jobs"])


class CreateSyncJobRequest(BaseModel):
    """说明 CreateSyncJobRequest 的职责、状态边界和对外协作关系。"""
    resource_type: SyncResourceType


@router.post(
    "/v1/store-workspaces/{workspace_id}/sync-jobs",
    response_model=SyncJob,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_sync_job(
    workspace_id: str,
    payload: CreateSyncJobRequest,
    response: Response,
    gateway: Annotated[SyncJobGateway, Depends(get_sync_job_gateway)],
    workspace_gateway: Annotated[
        StoreWorkspaceGateway, Depends(get_store_workspace_gateway)
    ],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=120)],
) -> SyncJob:
    """执行 create_sync_job 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。
    response: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。
    idempotency_key: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    workspace = await workspace_gateway.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if workspace.status != "active":
        raise HTTPException(status_code=409, detail={"code": "workspace_not_active"})
    job = await gateway.create_sync_job(
        workspace_id=workspace_id,
        resource_type=payload.resource_type,
        idempotency_key=idempotency_key,
    )
    response.headers["Location"] = f"/v1/sync-jobs/{job.id}"
    response.headers["Retry-After"] = "2"
    response.headers["Cache-Control"] = "no-store"
    return job


@router.get("/v1/sync-jobs/{job_id}", response_model=SyncJob)
async def get_sync_job(
    job_id: str,
    response: Response,
    gateway: Annotated[SyncJobGateway, Depends(get_sync_job_gateway)],
) -> SyncJob:
    """执行 get_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。
    response: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    job = await gateway.get_sync_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "sync_job_not_found", "message": "同步任务不存在"},
        )
    response.headers["Cache-Control"] = "no-store"
    return job


@router.get("/v1/store-workspaces/{workspace_id}/sync-jobs", response_model=SyncJobPage)
async def list_sync_jobs(
    workspace_id: str,
    response: Response,
    gateway: Annotated[SyncJobGateway, Depends(get_sync_job_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    cursor: Annotated[str | None, Query(pattern=r"^\d+$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SyncJobPage:
    """返回当前工作区的同步历史，页面只读任务事实。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    response: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。
    cursor: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    workspace = await workspace_gateway.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if workspace.status != "active":
        raise HTTPException(status_code=409, detail={"code": "workspace_not_active"})
    response.headers["Cache-Control"] = "no-store"
    return await gateway.list_sync_jobs(workspace_id=workspace_id, cursor=cursor, limit=limit)


@router.post("/v1/sync-jobs/{job_id}/cancel", response_model=SyncJob)
async def cancel_sync_job(
    job_id: str,
    response: Response,
    gateway: Annotated[SyncJobGateway, Depends(get_sync_job_gateway)],
) -> SyncJob:
    """请求取消排队或执行中的任务，并返回数据库最新状态。

Args:
    job_id: 参数语义、输入边界和安全约束。
    response: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if not await gateway.request_cancel_sync_job(job_id=job_id):
        raise HTTPException(status_code=409, detail={"code": "sync_job_not_cancellable"})
    job = await gateway.get_sync_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"code": "sync_job_not_found"})
    response.headers["Retry-After"] = "2"
    response.headers["Cache-Control"] = "no-store"
    return job


@router.post("/v1/sync-jobs/{job_id}/retry", response_model=SyncJob)
async def retry_sync_job(
    job_id: str,
    response: Response,
    gateway: Annotated[SyncJobGateway, Depends(get_sync_job_gateway)],
) -> SyncJob:
    """仅允许失败或部分成功任务重新排队。

Args:
    job_id: 参数语义、输入边界和安全约束。
    response: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    job = await gateway.retry_sync_job(job_id=job_id)
    if job is None:
        raise HTTPException(status_code=409, detail={"code": "sync_job_not_retryable"})
    response.headers["Location"] = f"/v1/sync-jobs/{job.id}"
    response.headers["Retry-After"] = "2"
    response.headers["Cache-Control"] = "no-store"
    return job
