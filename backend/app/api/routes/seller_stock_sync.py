"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_seller_stock_snapshot_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.seller_stock_snapshot import SellerStockSnapshotGateway
from backend.app.domain.seller_stock_sync import SellerStockSyncPreview, map_seller_stock_response
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/seller/stock", tags=["seller-api"])


class SellerStockSyncPayload(BaseModel):
    """说明 SellerStockSyncPayload 的职责、状态边界和对外协作关系。"""
    response: dict[str, object]


@router.post("/sync-preview", response_model=SellerStockSyncPreview)
async def sync_preview(payload: SellerStockSyncPayload) -> SellerStockSyncPreview:
    """执行 sync_preview 的业务流程并返回该流程的结果。"""
    try:
        return map_seller_stock_response(payload.response)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "seller_stock_response_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/sync-and-save",
    response_model=SellerStockSyncPreview,
)
async def sync_and_save(
    workspace_id: str,
    payload: SellerStockSyncPayload,
    gateway: Annotated[SellerStockSnapshotGateway, Depends(get_seller_stock_snapshot_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> SellerStockSyncPreview:
    """执行 sync_and_save 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    try:
        preview = map_seller_stock_response(payload.response)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "seller_stock_response_invalid", "message": str(error)},
        ) from error
    return await gateway.save_snapshot(workspace_id=workspace_id, preview=preview)


@router.get(
    "/store-workspaces/{workspace_id}/snapshots",
    response_model=list[SellerStockSyncPreview],
)
async def list_snapshots(
    workspace_id: str,
    gateway: Annotated[SellerStockSnapshotGateway, Depends(get_seller_stock_snapshot_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SellerStockSyncPreview]:
    """执行 list_snapshots 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_snapshots(workspace_id=workspace_id, limit=limit)
