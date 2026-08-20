"""说明本模块的职责、边界和主要协作对象。"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import get_listing_keyword_gateway, get_store_workspace_gateway
from backend.app.domain.listing_keyword import (
    KeywordLayer,
    ListingKeyword,
    ListingKeywordError,
    ListingKeywordGateway,
    normalize_listing_keyword,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/listing/keywords", tags=["listing"])


class ListingKeywordPayload(BaseModel):
    """说明 ListingKeywordPayload 的职责、状态边界和对外协作关系。"""
    keyword: str
    source: str
    observed_at: datetime
    language: str
    layer: KeywordLayer
    product_scope: str


@router.post("/normalize", response_model=ListingKeyword)
async def normalize_keyword(payload: ListingKeywordPayload) -> ListingKeyword:
    """执行 normalize_keyword 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    try:
        return normalize_listing_keyword(ListingKeyword(**payload.model_dump()))
    except ListingKeywordError as error:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail={"code": "listing_keyword_invalid", "message": str(error)},
        ) from error


@router.post("/store-workspaces/{workspace_id}/normalize-and-save", response_model=ListingKeyword)
async def normalize_and_save_keyword(
    workspace_id: str,
    payload: ListingKeywordPayload,
    gateway: Annotated[ListingKeywordGateway, Depends(get_listing_keyword_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> ListingKeyword:
    """执行 normalize_and_save_keyword 的业务流程并返回该流程的结果。

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
    try:
        keyword = normalize_listing_keyword(ListingKeyword(**payload.model_dump()))
    except ListingKeywordError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "listing_keyword_invalid", "message": str(error)},
        ) from error
    return await gateway.save_keyword(workspace_id=workspace_id, keyword=keyword)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[ListingKeyword])
async def list_keyword_history(
    workspace_id: str,
    gateway: Annotated[ListingKeywordGateway, Depends(get_listing_keyword_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[ListingKeyword]:
    """返回关键词库最近记录，供运营核对来源、分层和适用商品范围。

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
    return await gateway.list_keywords(workspace_id=workspace_id, limit=limit)
