from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_advertising_threshold_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.advertising_thresholds import (
    AdvertisingThresholdGateway,
    AdvertisingThresholds,
    create_advertising_thresholds,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/advertising/thresholds", tags=["advertising"])


class AdvertisingThresholdsPayload(BaseModel):
    version: int = Field(ge=1)
    min_impressions: int = Field(ge=0)
    min_clicks: int = Field(ge=0)
    high_cvr_percent: float = Field(ge=0)
    high_spend_minor: int = Field(ge=0)


@router.post("/validate", response_model=AdvertisingThresholds)
async def validate_thresholds(payload: AdvertisingThresholdsPayload) -> AdvertisingThresholds:
    try:
        return create_advertising_thresholds(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "advertising_thresholds_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/validate-and-save",
    response_model=AdvertisingThresholds,
)
async def validate_and_save_thresholds(
    workspace_id: str,
    payload: AdvertisingThresholdsPayload,
    gateway: Annotated[AdvertisingThresholdGateway, Depends(get_advertising_threshold_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> AdvertisingThresholds:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    thresholds = await validate_thresholds(payload)
    return await gateway.save(workspace_id=workspace_id, thresholds=thresholds)


@router.get(
    "/store-workspaces/{workspace_id}/versions",
    response_model=list[AdvertisingThresholds],
)
async def list_threshold_versions(
    workspace_id: str,
    gateway: Annotated[AdvertisingThresholdGateway, Depends(get_advertising_threshold_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[AdvertisingThresholds]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_versions(workspace_id=workspace_id, limit=limit)
