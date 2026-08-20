"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_listing_title_draft_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.listing_title_draft import (
    ListingTitleDraft,
    ListingTitleDraftGateway,
    generate_russian_title,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/listing/title-drafts", tags=["listing"])


class TitleDraftPayload(BaseModel):
    """说明 TitleDraftPayload 的职责、状态边界和对外协作关系。"""
    category: str
    core_terms: list[str] = []
    attribute_terms: list[str] = []
    scene_terms: list[str] = []
    max_characters: int = Field(default=120, ge=30, le=200)


@router.post("/generate", response_model=ListingTitleDraft)
async def generate_title_draft(payload: TitleDraftPayload) -> ListingTitleDraft:
    """执行 generate_title_draft 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return generate_russian_title(**payload.model_dump())


@router.post("/store-workspaces/{workspace_id}/generate-and-save", response_model=ListingTitleDraft)
async def generate_and_save_title_draft(
    workspace_id: str,
    payload: TitleDraftPayload,
    gateway: Annotated[ListingTitleDraftGateway, Depends(get_listing_title_draft_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> ListingTitleDraft:
    """执行 generate_and_save_title_draft 的业务流程并返回该流程的结果。

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
    draft = generate_russian_title(**payload.model_dump())
    return await gateway.save_draft(
        workspace_id=workspace_id, product_scope=payload.category, draft=draft
    )


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[ListingTitleDraft])
async def list_title_draft_history(
    workspace_id: str,
    gateway: Annotated[ListingTitleDraftGateway, Depends(get_listing_title_draft_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[ListingTitleDraft]:
    """返回标题草稿历史，供人工修改和风险复核。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_drafts(workspace_id=workspace_id, limit=limit)
