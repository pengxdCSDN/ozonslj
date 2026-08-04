from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.api.dependencies import get_current_user, get_sync_job_gateway
from backend.app.domain.identity import AuthenticatedUser
from backend.app.domain.store_workspace import WorkspaceNotFoundError
from backend.app.domain.sync_job import (
    SyncJob,
    SyncJobAlreadyActiveError,
    SyncJobGateway,
    SyncMode,
    SyncResourceType,
)

router = APIRouter(tags=["sync-jobs"])


class CreateSyncJobRequest(BaseModel):
    resource_type: SyncResourceType
    sync_mode: SyncMode = "incremental"


@router.post(
    "/v1/store-workspaces/{workspace_id}/sync-jobs",
    response_model=SyncJob,
    status_code=status.HTTP_201_CREATED,
)
async def create_sync_job(
    workspace_id: str,
    request_body: CreateSyncJobRequest,
    gateway: Annotated[SyncJobGateway, Depends(get_sync_job_gateway)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> SyncJob:
    if workspace_id not in user.workspace_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该工作区")
    try:
        return await gateway.create_sync_job(
            workspace_id=workspace_id,
            resource_type=request_body.resource_type,
            sync_mode=request_body.sync_mode,
            requested_by=user.id,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="店铺工作区不存在或已停用",
        ) from error
    except SyncJobAlreadyActiveError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该工作区已有同步任务正在排队或运行",
        ) from error


@router.get("/v1/sync-jobs/{job_id}", response_model=SyncJob)
async def get_sync_job(
    job_id: str,
    gateway: Annotated[SyncJobGateway, Depends(get_sync_job_gateway)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> SyncJob:
    job = await gateway.get_sync_job(job_id=job_id, workspace_ids=user.workspace_ids)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="同步任务不存在")
    return job
