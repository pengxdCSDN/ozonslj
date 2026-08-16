from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_store_workspace_gateway
from backend.app.domain.advertising_budget import (
    AdvertisingBudgetAnalysis,
    analyze_advertising_budget,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/advertising/budget", tags=["advertising"])


class AdvertisingBudgetPayload(BaseModel):
    budget_minor: int = Field(gt=0)
    spend_minor: int = Field(ge=0)
    days_elapsed: int = Field(gt=0)
    days_total: int = Field(gt=0)


@router.post("/analyze", response_model=AdvertisingBudgetAnalysis)
async def analyze_budget(payload: AdvertisingBudgetPayload) -> AdvertisingBudgetAnalysis:
    try:
        return analyze_advertising_budget(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "advertising_budget_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/analyze",
    response_model=AdvertisingBudgetAnalysis,
)
async def analyze_workspace_budget(
    workspace_id: str,
    payload: AdvertisingBudgetPayload,
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> AdvertisingBudgetAnalysis:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await analyze_budget(payload)
