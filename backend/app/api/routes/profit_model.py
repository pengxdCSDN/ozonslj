"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_profit_model_gateway, get_store_workspace_gateway
from backend.app.domain.assumption_version import assumption_version
from backend.app.domain.profit_model import (
    ProfitModelGateway,
    ProfitModelInput,
    ProfitScenario,
    calculate_profit_model,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/selection/profit-model", tags=["selection"])


class ProfitModelPayload(BaseModel):
    """说明 ProfitModelPayload 的职责、状态边界和对外协作关系。"""
    selling_price_minor: int = Field(ge=0)
    purchase_cost_minor: int = Field(ge=0)
    fbo_logistics_minor: int = Field(ge=0)
    fbs_logistics_minor: int = Field(ge=0)
    commission_minor: int = Field(ge=0)
    ad_cost_minor: int = Field(ge=0)
    return_loss_minor: int = Field(ge=0)
    fixed_cost_minor: int = Field(default=0, ge=0)


@router.post("/calculate", response_model=list[ProfitScenario])
async def calculate_profit(payload: ProfitModelPayload) -> list[ProfitScenario]:
    """执行 calculate_profit 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return list(calculate_profit_model(ProfitModelInput(**payload.model_dump())))


@router.post(
    "/store-workspaces/{workspace_id}/calculate-and-save",
    response_model=list[ProfitScenario],
)
async def calculate_and_save_profit(
    workspace_id: str,
    payload: ProfitModelPayload,
    gateway: Annotated[ProfitModelGateway, Depends(get_profit_model_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[ProfitScenario]:
    """执行 calculate_and_save_profit 的业务流程并返回该流程的结果。

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
    assumptions = payload.model_dump()
    assumptions["assumption_version"] = assumption_version(assumptions)
    scenarios = calculate_profit_model(ProfitModelInput(**assumptions))
    saved = await gateway.save_model(
        workspace_id=workspace_id, assumptions=assumptions, scenarios=scenarios
    )
    return list(saved)
