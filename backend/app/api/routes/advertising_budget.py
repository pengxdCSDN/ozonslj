"""说明本模块的职责、边界和主要协作对象。"""

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
    """说明 AdvertisingBudgetPayload 的职责、状态边界和对外协作关系。"""
    budget_minor: int = Field(gt=0)
    spend_minor: int = Field(ge=0)
    days_elapsed: int = Field(gt=0)
    days_total: int = Field(gt=0)


@router.post("/analyze", response_model=AdvertisingBudgetAnalysis)
async def analyze_budget(payload: AdvertisingBudgetPayload) -> AdvertisingBudgetAnalysis:
    """执行 analyze_budget 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
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
    """执行 analyze_workspace_budget 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await analyze_budget(payload)
