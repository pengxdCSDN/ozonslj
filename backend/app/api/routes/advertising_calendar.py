"""说明本模块的职责、边界和主要协作对象。"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_advertising_calendar_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.advertising_calendar import (
    AdvertisingCalendarDay,
    AdvertisingCalendarGateway,
    build_advertising_calendar,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/advertising/calendar", tags=["advertising"])


class AdvertisingCalendarPayload(BaseModel):
    """说明 AdvertisingCalendarPayload 的职责、状态边界和对外协作关系。"""
    start_date: date


@router.post("/build", response_model=list[AdvertisingCalendarDay])
async def build_calendar(payload: AdvertisingCalendarPayload) -> list[AdvertisingCalendarDay]:
    """执行 build_calendar 的业务流程并返回该流程的结果。"""
    return build_advertising_calendar(payload.start_date)


@router.post(
    "/store-workspaces/{workspace_id}/build-and-save",
    response_model=list[AdvertisingCalendarDay],
)
async def build_and_save_calendar(
    workspace_id: str,
    payload: AdvertisingCalendarPayload,
    gateway: Annotated[AdvertisingCalendarGateway, Depends(get_advertising_calendar_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[AdvertisingCalendarDay]:
    """执行 build_and_save_calendar 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    days = await build_calendar(payload)
    return await gateway.save_calendar(
        workspace_id=workspace_id, start_date=payload.start_date, days=days
    )


@router.get(
    "/store-workspaces/{workspace_id}/history",
    response_model=list[list[AdvertisingCalendarDay]],
)
async def list_calendar_history(
    workspace_id: str,
    gateway: Annotated[AdvertisingCalendarGateway, Depends(get_advertising_calendar_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 10,
) -> list[list[AdvertisingCalendarDay]]:
    """执行 list_calendar_history 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_calendars(workspace_id=workspace_id, limit=limit)
