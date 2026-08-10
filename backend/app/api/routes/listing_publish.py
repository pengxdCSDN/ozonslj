from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import get_listing_publish_gateway, get_store_workspace_gateway
from backend.app.domain.listing_publish import (
    ListingPublishGateway,
    PublishCommand,
    PublishStatus,
    execute_controlled_publish,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/listing/publish", tags=["listing"])


class PublishPayload(BaseModel):
    idempotency_key: str
    version: int
    status: PublishStatus
    requested_text: str
    readback_text: str | None = None


@router.post("/execute", response_model=PublishCommand)
async def publish_listing(payload: PublishPayload) -> PublishCommand:
    return execute_controlled_publish(**payload.model_dump())


@router.post("/store-workspaces/{workspace_id}/execute", response_model=PublishCommand)
async def execute_workspace_listing_publish(
    workspace_id: str,
    payload: PublishPayload,
    gateway: Annotated[ListingPublishGateway, Depends(get_listing_publish_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> PublishCommand:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    command = await publish_listing(payload)
    return await gateway.save_command(
        workspace_id=workspace_id, product_scope="listing", command=command
    )


@router.get("/store-workspaces/{workspace_id}", response_model=list[PublishCommand])
async def list_workspace_listing_publishes(
    workspace_id: str,
    gateway: Annotated[ListingPublishGateway, Depends(get_listing_publish_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[PublishCommand]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_commands(
        workspace_id=workspace_id, product_scope="listing", limit=limit
    )
