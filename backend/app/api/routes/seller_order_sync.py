from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_seller_order_snapshot_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.seller_order_snapshot import SellerOrderSnapshotGateway
from backend.app.domain.seller_order_sync import SellerOrderSyncPreview, map_seller_order_response
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/seller/orders", tags=["seller-api"])


class SellerOrderSyncPayload(BaseModel):
    response: dict[str, object]


@router.post("/sync-preview", response_model=SellerOrderSyncPreview)
async def sync_preview(payload: SellerOrderSyncPayload) -> SellerOrderSyncPreview:
    try:
        return map_seller_order_response(payload.response)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "seller_order_response_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/sync-and-save",
    response_model=SellerOrderSyncPreview,
)
async def sync_and_save(
    workspace_id: str,
    payload: SellerOrderSyncPayload,
    gateway: Annotated[SellerOrderSnapshotGateway, Depends(get_seller_order_snapshot_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> SellerOrderSyncPreview:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    try:
        preview = map_seller_order_response(payload.response)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "seller_order_response_invalid", "message": str(error)},
        ) from error
    return await gateway.save_snapshot(workspace_id=workspace_id, preview=preview)


@router.get(
    "/store-workspaces/{workspace_id}/snapshots",
    response_model=list[SellerOrderSyncPreview],
)
async def list_snapshots(
    workspace_id: str,
    gateway: Annotated[SellerOrderSnapshotGateway, Depends(get_seller_order_snapshot_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SellerOrderSyncPreview]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_snapshots(workspace_id=workspace_id, limit=limit)
