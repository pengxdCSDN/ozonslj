"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_advertising_analysis_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.advertising_analysis import (
    AdvertisingAnalysis,
    AdvertisingAnalysisGateway,
    analyze_advertising,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/analysis/advertising", tags=["analysis"])


class AdvertisingAnalysisPayload(BaseModel):
    """说明 AdvertisingAnalysisPayload 的职责、状态边界和对外协作关系。"""
    spend_minor: int = Field(ge=0)
    ad_sales_minor: int = Field(ge=0)
    total_sales_minor: int = Field(ge=0)
    keyword_count: int = Field(ge=0)
    unconverted_keyword_count: int = Field(ge=0)
    acos_alert_percent: float = Field(ge=0)


@router.post("/analyze", response_model=AdvertisingAnalysis)
async def analyze(payload: AdvertisingAnalysisPayload) -> AdvertisingAnalysis:
    """执行 analyze 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    try:
        return analyze_advertising(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "advertising_analysis_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/analyze-and-save",
    response_model=AdvertisingAnalysis,
)
async def analyze_and_save(
    workspace_id: str,
    payload: AdvertisingAnalysisPayload,
    gateway: Annotated[AdvertisingAnalysisGateway, Depends(get_advertising_analysis_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> AdvertisingAnalysis:
    """执行 analyze_and_save 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    report = await analyze(payload)
    return await gateway.save_report(workspace_id=workspace_id, report=report)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[AdvertisingAnalysis])
async def list_analysis_history(
    workspace_id: str,
    gateway: Annotated[AdvertisingAnalysisGateway, Depends(get_advertising_analysis_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[AdvertisingAnalysis]:
    """执行 list_analysis_history 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_reports(workspace_id=workspace_id, limit=limit)
