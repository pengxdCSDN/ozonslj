from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_data_freshness_gateway, get_store_workspace_gateway
from backend.app.domain.data_freshness import (
    DataFreshnessDecision,
    DataFreshnessGateway,
    check_data_freshness,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/review/freshness", tags=["review"])


class FreshnessPayload(BaseModel):
    data_domain: str = Field(min_length=1, max_length=100)
    observed_at: datetime
    max_age_seconds: int = Field(ge=0)
    now: datetime | None = None
    last_success_at: datetime | None = None
    window: str | None = Field(default=None, max_length=100)
    latency_seconds: int | None = Field(default=None, ge=0)
    record_count: int | None = Field(default=None, ge=0)
    error_summary: str | None = Field(default=None, max_length=300)


@router.post("/check", response_model=DataFreshnessDecision)
async def check_freshness(payload: FreshnessPayload) -> DataFreshnessDecision:
    return check_data_freshness(**payload.model_dump())


@router.post(
    "/store-workspaces/{workspace_id}/check-and-save",
    response_model=DataFreshnessDecision,
)
async def check_and_save_freshness(
    workspace_id: str,
    payload: FreshnessPayload,
    gateway: Annotated[DataFreshnessGateway, Depends(get_data_freshness_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> DataFreshnessDecision:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    decision = await check_freshness(payload)
    return await gateway.save_decision(workspace_id=workspace_id, decision=decision)


@router.get(
    "/store-workspaces/{workspace_id}/history",
    response_model=list[DataFreshnessDecision],
)
async def list_freshness_history(
    workspace_id: str,
    gateway: Annotated[DataFreshnessGateway, Depends(get_data_freshness_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[DataFreshnessDecision]:
    """返回最近新鲜度判定，供过期数据重新读取前复核。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_decisions(workspace_id=workspace_id, limit=limit)
