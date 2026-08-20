"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_seller_product_snapshot_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.seller_product_snapshot import SellerProductSnapshotGateway
from backend.app.domain.seller_product_sync import (
    SellerProductSyncPreview,
    map_seller_product_response,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/seller/products", tags=["seller-api"])


class SellerProductSyncPayload(BaseModel):
    """说明 SellerProductSyncPayload 的职责、状态边界和对外协作关系。"""
    response: dict[str, object]
    cursor: str | None = None


@router.post("/sync-preview", response_model=SellerProductSyncPreview)
async def sync_preview(payload: SellerProductSyncPayload) -> SellerProductSyncPreview:
    """执行 sync_preview 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    try:
        return map_seller_product_response(payload.response, cursor=payload.cursor)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "seller_product_response_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/sync-and-save",
    response_model=SellerProductSyncPreview,
)
async def sync_and_save(
    workspace_id: str,
    payload: SellerProductSyncPayload,
    gateway: Annotated[SellerProductSnapshotGateway, Depends(get_seller_product_snapshot_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> SellerProductSyncPreview:
    """执行 sync_and_save 的业务流程并返回该流程的结果。

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
        preview = map_seller_product_response(payload.response, cursor=payload.cursor)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "seller_product_response_invalid", "message": str(error)},
        ) from error
    return await gateway.save_snapshot(workspace_id=workspace_id, preview=preview)


@router.get(
    "/store-workspaces/{workspace_id}/snapshots",
    response_model=list[SellerProductSyncPreview],
)
async def list_snapshots(
    workspace_id: str,
    gateway: Annotated[SellerProductSnapshotGateway, Depends(get_seller_product_snapshot_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SellerProductSyncPreview]:
    """执行 list_snapshots 的业务流程并返回该流程的结果。

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
    return await gateway.list_snapshots(workspace_id=workspace_id, limit=limit)
