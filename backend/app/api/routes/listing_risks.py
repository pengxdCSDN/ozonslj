"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_listing_risk_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.listing_risk import (
    ListingRiskGateway,
    ListingRiskReport,
    detect_listing_risks,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/listing/risks", tags=["listing"])


class ListingRiskPayload(BaseModel):
    """说明 ListingRiskPayload 的职责、状态边界和对外协作关系。"""
    text: str
    authorized_brands: list[str] = []
    verified_certifications: list[str] = []


@router.post("/check", response_model=ListingRiskReport)
async def check_listing_risks(payload: ListingRiskPayload) -> ListingRiskReport:
    """执行 check_listing_risks 的业务流程并返回该流程的结果。"""
    return detect_listing_risks(
        payload.text,
        authorized_brands=set(payload.authorized_brands),
        verified_certifications=set(payload.verified_certifications),
    )


@router.post("/store-workspaces/{workspace_id}/check-and-save", response_model=ListingRiskReport)
async def check_and_save_listing_risks(
    workspace_id: str,
    payload: ListingRiskPayload,
    gateway: Annotated[ListingRiskGateway, Depends(get_listing_risk_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> ListingRiskReport:
    """执行 check_and_save_listing_risks 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    report = await check_listing_risks(payload)
    return await gateway.save_report(
        workspace_id=workspace_id, product_scope="listing", report=report
    )


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[ListingRiskReport])
async def list_listing_risk_history(
    workspace_id: str,
    gateway: Annotated[ListingRiskGateway, Depends(get_listing_risk_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[ListingRiskReport]:
    """返回内容风险历史，供人工确认品牌、疗效和认证风险。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_reports(workspace_id=workspace_id, limit=limit)
