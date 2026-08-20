"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_store_workspace_gateway, get_validate_result_gateway
from backend.app.domain.assumption_version import assumption_version
from backend.app.domain.selection_validate import (
    ValidateInput,
    ValidateResult,
    ValidateResultGateway,
    validate_product,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/selection/validate", tags=["selection"])


class ValidatePayload(BaseModel):
    """说明 ValidatePayload 的职责、状态边界和对外协作关系。"""
    sku: str
    selling_price_minor: int = Field(ge=0)
    purchase_cost_minor: int = Field(ge=0)
    logistics_cost_minor: int = Field(ge=0)
    commission_minor: int = Field(ge=0)
    ad_cost_minor: int = Field(ge=0)
    return_loss_minor: int = Field(ge=0)
    fixed_launch_cost_minor: int = Field(default=0, ge=0)
    competitor_count: int = Field(default=0, ge=0)
    own_stock: int = Field(default=0, ge=0)
    monthly_sales: int = Field(default=0, ge=0)
    certification_required: bool = False


@router.post("/run", response_model=ValidateResult)
async def run_validate(payload: ValidatePayload) -> ValidateResult:
    """执行 run_validate 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return validate_product(ValidateInput(**payload.model_dump()))


@router.post("/store-workspaces/{workspace_id}/run-and-save", response_model=ValidateResult)
async def run_and_save_validate(
    workspace_id: str,
    payload: ValidatePayload,
    gateway: Annotated[ValidateResultGateway, Depends(get_validate_result_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> ValidateResult:
    """执行 run_and_save_validate 的业务流程并返回该流程的结果。

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
    result = validate_product(ValidateInput(**assumptions))
    return await gateway.save_validation(
        workspace_id=workspace_id, assumptions=assumptions, result=result
    )


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[ValidateResult])
async def list_validation_history(
    workspace_id: str,
    gateway: Annotated[ValidateResultGateway, Depends(get_validate_result_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[ValidateResult]:
    """执行 list_validation_history 的业务流程并返回该流程的结果。

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
    return await gateway.list_validations(workspace_id=workspace_id, limit=limit)
