from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_inventory_analysis_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.inventory_analysis import (
    InventoryAnalysis,
    InventoryAnalysisGateway,
    analyze_inventory,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/analysis/inventory", tags=["analysis"])


class InventoryAnalysisPayload(BaseModel):
    available_units: int = Field(ge=0)
    inbound_units: int = Field(ge=0)
    average_daily_sales: float = Field(ge=0)
    safety_days: int = Field(ge=0)
    overstock_days: int = Field(ge=0)


@router.post("/analyze", response_model=InventoryAnalysis)
async def analyze(payload: InventoryAnalysisPayload) -> InventoryAnalysis:
    try:
        return analyze_inventory(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "inventory_analysis_invalid", "message": str(error)},
        ) from error


@router.post("/store-workspaces/{workspace_id}/analyze-and-save", response_model=InventoryAnalysis)
async def analyze_and_save(
    workspace_id: str,
    payload: InventoryAnalysisPayload,
    gateway: Annotated[InventoryAnalysisGateway, Depends(get_inventory_analysis_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> InventoryAnalysis:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    report = await analyze(payload)
    return await gateway.save_report(workspace_id=workspace_id, report=report)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[InventoryAnalysis])
async def list_analysis_history(
    workspace_id: str,
    gateway: Annotated[InventoryAnalysisGateway, Depends(get_inventory_analysis_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[InventoryAnalysis]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_reports(workspace_id=workspace_id, limit=limit)
