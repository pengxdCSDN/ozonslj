from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_advertising_boundary_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.advertising_readonly import (
    AdvertisingBoundaryGateway,
    AdvertisingReadOnlyDecision,
    check_advertising_action,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/advertising/boundary", tags=["advertising"])


class AdvertisingActionPayload(BaseModel):
    action: str = Field(min_length=1, max_length=80)


@router.post("/check", response_model=AdvertisingReadOnlyDecision)
async def check_boundary(payload: AdvertisingActionPayload) -> AdvertisingReadOnlyDecision:
    return check_advertising_action(payload.action)


@router.post(
    "/store-workspaces/{workspace_id}/check-and-save",
    response_model=AdvertisingReadOnlyDecision,
)
async def check_and_save_boundary(
    workspace_id: str,
    payload: AdvertisingActionPayload,
    gateway: Annotated[AdvertisingBoundaryGateway, Depends(get_advertising_boundary_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> AdvertisingReadOnlyDecision:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    decision = await check_boundary(payload)
    return await gateway.save_check(workspace_id=workspace_id, decision=decision)


@router.get(
    "/store-workspaces/{workspace_id}/history",
    response_model=list[AdvertisingReadOnlyDecision],
)
async def list_boundary_history(
    workspace_id: str,
    gateway: Annotated[AdvertisingBoundaryGateway, Depends(get_advertising_boundary_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[AdvertisingReadOnlyDecision]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_checks(workspace_id=workspace_id, limit=limit)
