"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_advertising_campaign_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.advertising_campaign import (
    AdvertisingCampaign,
    AdvertisingCampaignGateway,
    map_performance_campaign,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/advertising/campaigns", tags=["advertising"])


class CampaignSyncPayload(BaseModel):
    """说明 CampaignSyncPayload 的职责、状态边界和对外协作关系。"""
    campaigns: list[dict[str, object]]


@router.post("/sync-preview", response_model=list[AdvertisingCampaign])
async def sync_campaign_preview(payload: CampaignSyncPayload) -> list[AdvertisingCampaign]:
    """执行 sync_campaign_preview 的业务流程并返回该流程的结果。"""
    return [map_performance_campaign(item) for item in payload.campaigns]


@router.post(
    "/store-workspaces/{workspace_id}/sync-and-save",
    response_model=list[AdvertisingCampaign],
)
async def sync_and_save_campaigns(
    workspace_id: str,
    payload: CampaignSyncPayload,
    gateway: Annotated[AdvertisingCampaignGateway, Depends(get_advertising_campaign_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[AdvertisingCampaign]:
    """执行 sync_and_save_campaigns 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    campaigns = [map_performance_campaign(item) for item in payload.campaigns]
    return await gateway.save_campaigns(workspace_id=workspace_id, campaigns=campaigns)


@router.get("/store-workspaces/{workspace_id}", response_model=list[AdvertisingCampaign])
async def list_saved_campaigns(
    workspace_id: str,
    gateway: Annotated[AdvertisingCampaignGateway, Depends(get_advertising_campaign_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 100,
) -> list[AdvertisingCampaign]:
    """执行 list_saved_campaigns 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_campaigns(workspace_id=workspace_id, limit=limit)
