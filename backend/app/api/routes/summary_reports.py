from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_store_workspace_gateway, get_summary_report_gateway
from backend.app.domain.store_workspace import StoreWorkspaceGateway
from backend.app.domain.summary_report import (
    SummaryReport,
    SummaryReportGateway,
    build_summary_report,
)

router = APIRouter(prefix="/v1/reports", tags=["reports"])


class SummaryReportPayload(BaseModel):
    report_type: str = Field(min_length=1)
    period: str = Field(min_length=1)
    sales_change_percent: float | None = None
    stockout_risk_count: int = Field(ge=0)
    advertising_anomaly_count: int = Field(ge=0)
    opportunity_count: int = Field(ge=0)


@router.post("/summary", response_model=SummaryReport)
async def summary(payload: SummaryReportPayload) -> SummaryReport:
    try:
        return build_summary_report(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "summary_report_invalid", "message": str(error)},
        ) from error


@router.post("/store-workspaces/{workspace_id}/summary-and-save", response_model=SummaryReport)
async def summary_and_save(
    workspace_id: str,
    payload: SummaryReportPayload,
    gateway: Annotated[SummaryReportGateway, Depends(get_summary_report_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> SummaryReport:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    report = await summary(payload)
    return await gateway.save_report(workspace_id=workspace_id, report=report)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[SummaryReport])
async def list_report_history(
    workspace_id: str,
    gateway: Annotated[SummaryReportGateway, Depends(get_summary_report_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[SummaryReport]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_reports(workspace_id=workspace_id, limit=limit)
