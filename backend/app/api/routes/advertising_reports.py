"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import get_advertising_report_gateway, get_store_workspace_gateway
from backend.app.domain.advertising_report import (
    AdvertisingReportGateway,
    AdvertisingReportRow,
    normalize_advertising_report,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/advertising/reports", tags=["advertising"])


class AdvertisingReportPayload(BaseModel):
    """说明 AdvertisingReportPayload 的职责、状态边界和对外协作关系。"""
    rows: list[dict[str, object]]


@router.post("/sync-preview", response_model=list[AdvertisingReportRow])
async def sync_report_preview(payload: AdvertisingReportPayload) -> list[AdvertisingReportRow]:
    """执行 sync_report_preview 的业务流程并返回该流程的结果。"""
    try:
        return [normalize_advertising_report(row) for row in payload.rows]
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "advertising_report_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/sync-and-save",
    response_model=list[AdvertisingReportRow],
)
async def sync_and_save_reports(
    workspace_id: str,
    payload: AdvertisingReportPayload,
    gateway: Annotated[AdvertisingReportGateway, Depends(get_advertising_report_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[AdvertisingReportRow]:
    """执行 sync_and_save_reports 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    try:
        rows = [normalize_advertising_report(row) for row in payload.rows]
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "advertising_report_invalid", "message": str(error)},
        ) from error
    return await gateway.save_rows(workspace_id=workspace_id, rows=rows)


@router.get("/store-workspaces/{workspace_id}", response_model=list[AdvertisingReportRow])
async def list_saved_reports(
    workspace_id: str,
    gateway: Annotated[AdvertisingReportGateway, Depends(get_advertising_report_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 100,
) -> list[AdvertisingReportRow]:
    """执行 list_saved_reports 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_rows(workspace_id=workspace_id, limit=limit)
