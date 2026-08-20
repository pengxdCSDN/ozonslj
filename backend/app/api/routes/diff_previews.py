"""说明本模块的职责、边界和主要协作对象。"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_diff_preview_gateway, get_store_workspace_gateway
from backend.app.domain.diff_preview import (
    DiffPreview,
    DiffPreviewGateway,
    StalePreviewError,
    build_diff_preview,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/review/diff-previews", tags=["review"])


class DiffPreviewPayload(BaseModel):
    """说明 DiffPreviewPayload 的职责、状态边界和对外协作关系。"""
    old_values: dict[str, object] = Field(default_factory=dict)
    new_values: dict[str, object] = Field(default_factory=dict)
    source: str = Field(min_length=1, max_length=200)
    impact: str = Field(min_length=1, max_length=500)
    observed_at: datetime | None = None
    max_age_seconds: int | None = Field(default=None, ge=0)
    now: datetime | None = None


@router.post("/build", response_model=list[DiffPreview])
async def build_preview(payload: DiffPreviewPayload) -> list[DiffPreview]:
    """执行 build_preview 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    try:
        return build_diff_preview(**payload.model_dump())
    except StalePreviewError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "preview_data_stale", "message": str(exc)},
        ) from exc


@router.post("/store-workspaces/{workspace_id}/build-and-save", response_model=list[DiffPreview])
async def build_and_save_preview(
    workspace_id: str,
    payload: DiffPreviewPayload,
    gateway: Annotated[DiffPreviewGateway, Depends(get_diff_preview_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[DiffPreview]:
    """执行 build_and_save_preview 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    previews = await build_preview(payload)
    return await gateway.save_preview(workspace_id=workspace_id, previews=previews)
