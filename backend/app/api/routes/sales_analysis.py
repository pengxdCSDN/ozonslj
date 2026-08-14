from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_sales_analysis_gateway, get_store_workspace_gateway
from backend.app.domain.sales_analysis import SalesAnalysis, SalesAnalysisGateway, analyze_sales
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/analysis/sales", tags=["analysis"])


class SalesAnalysisPayload(BaseModel):
    current_sales_minor: int = Field(ge=0)
    previous_sales_minor: int = Field(ge=0)
    current_orders: int = Field(ge=0)
    previous_orders: int = Field(ge=0)
    current_window: str = Field(min_length=1)
    previous_window: str = Field(min_length=1)


@router.post("/analyze", response_model=SalesAnalysis)
async def analyze(payload: SalesAnalysisPayload) -> SalesAnalysis:
    try:
        return analyze_sales(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "sales_analysis_invalid", "message": str(error)},
        ) from error


@router.post("/store-workspaces/{workspace_id}/analyze-and-save", response_model=SalesAnalysis)
async def analyze_and_save(
    workspace_id: str,
    payload: SalesAnalysisPayload,
    gateway: Annotated[SalesAnalysisGateway, Depends(get_sales_analysis_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> SalesAnalysis:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    report = await analyze(payload)
    return await gateway.save_report(workspace_id=workspace_id, report=report)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[SalesAnalysis])
async def list_analysis_history(
    workspace_id: str,
    gateway: Annotated[SalesAnalysisGateway, Depends(get_sales_analysis_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[SalesAnalysis]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_reports(workspace_id=workspace_id, limit=limit)
