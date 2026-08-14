from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_seller_fulfillment_snapshot_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.seller_fulfillment_snapshot import SellerFulfillmentSnapshotGateway
from backend.app.domain.seller_fulfillment_sync import (
    SellerFulfillmentSyncPreview,
    map_seller_fulfillment_response,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/seller/fulfillment", tags=["seller-api"])


class SellerFulfillmentSyncPayload(BaseModel):
    response: dict[str, object]


@router.post("/sync-preview", response_model=SellerFulfillmentSyncPreview)
async def sync_preview(payload: SellerFulfillmentSyncPayload) -> SellerFulfillmentSyncPreview:
    try:
        return map_seller_fulfillment_response(payload.response)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "seller_fulfillment_response_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/sync-and-save",
    response_model=SellerFulfillmentSyncPreview,
)
async def sync_and_save(
    workspace_id: str,
    payload: SellerFulfillmentSyncPayload,
    gateway: Annotated[
        SellerFulfillmentSnapshotGateway,
        Depends(get_seller_fulfillment_snapshot_gateway),
    ],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> SellerFulfillmentSyncPreview:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    try:
        preview = map_seller_fulfillment_response(payload.response)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "seller_fulfillment_response_invalid", "message": str(error)},
        ) from error
    return await gateway.save_snapshot(workspace_id=workspace_id, preview=preview)


@router.get(
    "/store-workspaces/{workspace_id}/snapshots",
    response_model=list[SellerFulfillmentSyncPreview],
)
async def list_snapshots(
    workspace_id: str,
    gateway: Annotated[
        SellerFulfillmentSnapshotGateway,
        Depends(get_seller_fulfillment_snapshot_gateway),
    ],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SellerFulfillmentSyncPreview]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_snapshots(workspace_id=workspace_id, limit=limit)
