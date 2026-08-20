"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_advertising_metrics_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.advertising_metrics import (
    AdvertisingMetrics,
    AdvertisingMetricsGateway,
    calculate_advertising_metrics,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/advertising/metrics", tags=["advertising"])


class AdvertisingMetricsPayload(BaseModel):
    """说明 AdvertisingMetricsPayload 的职责、状态边界和对外协作关系。"""
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    orders: int = Field(ge=0)
    ad_sales_minor: int = Field(ge=0)
    total_sales_minor: int = Field(ge=0)
    spend_minor: int = Field(ge=0)
    currency: str
    window: str


@router.post("/calculate", response_model=AdvertisingMetrics)
async def calculate_metrics(payload: AdvertisingMetricsPayload) -> AdvertisingMetrics:
    """执行 calculate_metrics 的业务流程并返回该流程的结果。"""
    try:
        return calculate_advertising_metrics(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "advertising_metrics_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/calculate-and-save",
    response_model=AdvertisingMetrics,
)
async def calculate_and_save_metrics(
    workspace_id: str,
    payload: AdvertisingMetricsPayload,
    gateway: Annotated[AdvertisingMetricsGateway, Depends(get_advertising_metrics_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> AdvertisingMetrics:
    """执行 calculate_and_save_metrics 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    try:
        inputs = payload.model_dump()
        result = calculate_advertising_metrics(**inputs)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "advertising_metrics_invalid", "message": str(error)},
        ) from error
    return await gateway.save_snapshot(workspace_id=workspace_id, inputs=inputs, metrics=result)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[AdvertisingMetrics])
async def list_metric_snapshots(
    workspace_id: str,
    gateway: Annotated[AdvertisingMetricsGateway, Depends(get_advertising_metrics_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[AdvertisingMetrics]:
    """执行 list_metric_snapshots 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_snapshots(workspace_id=workspace_id, limit=limit)
