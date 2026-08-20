"""说明本模块的职责、边界和主要协作对象。"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_public_snapshot_gateway, get_store_workspace_gateway
from backend.app.domain.public_snapshot import (
    PublicSnapshot,
    PublicSnapshotError,
    PublicSnapshotGateway,
    normalize_public_snapshot,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/public-snapshots", tags=["public-snapshots"])


class PublicSnapshotPayload(BaseModel):
    """说明 PublicSnapshotPayload 的职责、状态边界和对外协作关系。"""
    url: str
    title: str | None = None
    price_minor: int | None = Field(default=None, ge=0)
    currency: str | None = None
    rating: str | None = None
    review_count: int | None = Field(default=None, ge=0)
    image_url: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    sample_size: int = Field(default=1, ge=1)


@router.post("/normalize", response_model=PublicSnapshot)
async def normalize_snapshot(payload: PublicSnapshotPayload) -> PublicSnapshot:
    """执行 normalize_snapshot 的业务流程并返回该流程的结果。"""
    try:
        return normalize_public_snapshot(payload.model_dump(), sampled_at=datetime.now(UTC))
    except PublicSnapshotError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "public_snapshot_invalid", "message": str(error)},
        ) from error


@router.post("/store-workspaces/{workspace_id}/save", response_model=PublicSnapshot)
async def save_snapshot(
    workspace_id: str,
    payload: PublicSnapshotPayload,
    gateway: Annotated[PublicSnapshotGateway, Depends(get_public_snapshot_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> PublicSnapshot:
    """执行 save_snapshot 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    try:
        snapshot = normalize_public_snapshot(payload.model_dump(), sampled_at=datetime.now(UTC))
    except PublicSnapshotError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "public_snapshot_invalid", "message": str(error)},
        ) from error
    return await gateway.save_snapshot(workspace_id=workspace_id, snapshot=snapshot)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[PublicSnapshot])
async def list_snapshot_history(
    workspace_id: str,
    gateway: Annotated[PublicSnapshotGateway, Depends(get_public_snapshot_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[PublicSnapshot]:
    """返回规范化公开快照历史，明确采样时间和估算属性。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_snapshots(workspace_id=workspace_id, limit=limit)
