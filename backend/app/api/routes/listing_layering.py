"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import get_listing_layer_gateway, get_store_workspace_gateway
from backend.app.domain.listing_layering import (
    LayeredKeyword,
    ListingLayerGateway,
    classify_listing_keywords,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/listing/keywords", tags=["listing"])


class LayeringPayload(BaseModel):
    """说明 LayeringPayload 的职责、状态边界和对外协作关系。"""
    keywords: list[str]
    core_terms: list[str] = []
    attribute_terms: list[str] = []
    scene_terms: list[str] = []


@router.post("/classify", response_model=list[LayeredKeyword])
async def classify_keywords(payload: LayeringPayload) -> list[LayeredKeyword]:
    """执行 classify_keywords 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return classify_listing_keywords(
        payload.keywords,
        core_terms=set(payload.core_terms),
        attribute_terms=set(payload.attribute_terms),
        scene_terms=set(payload.scene_terms),
    )


@router.post(
    "/store-workspaces/{workspace_id}/classify-and-save",
    response_model=list[LayeredKeyword],
)
async def classify_and_save_keywords(
    workspace_id: str,
    payload: LayeringPayload,
    gateway: Annotated[ListingLayerGateway, Depends(get_listing_layer_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[LayeredKeyword]:
    """执行 classify_and_save_keywords 的业务流程并返回该流程的结果。

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
    layers = classify_listing_keywords(
        payload.keywords,
        core_terms=set(payload.core_terms),
        attribute_terms=set(payload.attribute_terms),
        scene_terms=set(payload.scene_terms),
    )
    return await gateway.save_layers(workspace_id=workspace_id, layers=layers)


@router.get("/store-workspaces/{workspace_id}/layers/history", response_model=list[LayeredKeyword])
async def list_layer_history(
    workspace_id: str,
    gateway: Annotated[ListingLayerGateway, Depends(get_listing_layer_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[LayeredKeyword]:
    """返回最近分层结果，支持运营复核规则原因和人工确认状态。

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
    return await gateway.list_layers(workspace_id=workspace_id, limit=limit)
