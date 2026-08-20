"""说明本模块的职责、边界和主要协作对象。"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import get_public_snapshot_gateway, get_store_workspace_gateway
from backend.app.domain.public_snapshot import PublicSnapshotGateway
from backend.app.domain.sample_scope import SampleScope, summarize_sample_scope
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/public-samples", tags=["public-samples"])


class SampleRecord(BaseModel):
    """说明 SampleRecord 的职责、状态边界和对外协作关系。"""
    sampled_at: datetime | None = None
    title: str | None = None
    price_minor: int | None = None
    rating: str | None = None
    review_count: int | None = None
    image_url: str | None = None


class SampleScopePayload(BaseModel):
    """说明 SampleScopePayload 的职责、状态边界和对外协作关系。"""
    records: list[SampleRecord]


@router.post("/scope", response_model=SampleScope)
async def sample_scope(payload: SampleScopePayload) -> SampleScope:
    """执行 sample_scope 的业务流程并返回该流程的结果。"""
    return summarize_sample_scope([record.model_dump() for record in payload.records])


@router.get("/store-workspaces/{workspace_id}/scope", response_model=SampleScope)
async def workspace_sample_scope(
    workspace_id: str,
    gateway: Annotated[PublicSnapshotGateway, Depends(get_public_snapshot_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> SampleScope:
    """从已保存的公开快照生成可回溯的样本范围摘要。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    snapshots = await gateway.list_snapshots(workspace_id=workspace_id, limit=limit)
    return summarize_sample_scope([{
        "sampled_at": item.sampled_at, "title": item.title, "price_minor": item.price_minor,
        "rating": item.rating, "review_count": item.review_count, "image_url": item.image_url,
    } for item in snapshots])
