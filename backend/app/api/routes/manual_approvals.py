"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_manual_approval_gateway, get_store_workspace_gateway
from backend.app.domain.manual_approval import (
    ManualApproval,
    ManualApprovalGateway,
    validate_approval_request,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/review/approvals", tags=["review"])


class ApprovalPayload(BaseModel):
    """说明 ApprovalPayload 的职责、状态边界和对外协作关系。"""
    command_type: str = Field(min_length=1, max_length=100)
    payload: dict[str, object] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=200)


class ApprovalDecision(BaseModel):
    """说明 ApprovalDecision 的职责、状态边界和对外协作关系。"""
    reviewer: str = Field(min_length=1, max_length=200)


@router.post("/store-workspaces/{workspace_id}", response_model=ManualApproval)
async def create_approval(
    workspace_id: str,
    payload: ApprovalPayload,
    gateway: Annotated[ManualApprovalGateway, Depends(get_manual_approval_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> ManualApproval:
    """执行 create_approval 的业务流程并返回该流程的结果。

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
    validate_approval_request(**payload.model_dump())
    return await gateway.create(workspace_id=workspace_id, **payload.model_dump())


@router.post("/{approval_id}/approve", response_model=ManualApproval)
async def approve(
    approval_id: str,
    decision: ApprovalDecision,
    gateway: Annotated[ManualApprovalGateway, Depends(get_manual_approval_gateway)],
) -> ManualApproval:
    """执行 approve 的业务流程并返回该流程的结果。

Args:
    approval_id: 参数语义、输入边界和安全约束。
    decision: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    result = await gateway.approve(approval_id=approval_id, reviewer=decision.reviewer)
    if result is None:
        raise HTTPException(
            status_code=404, detail={"code": "approval_not_found_or_already_decided"}
        )
    return result


@router.get(
    "/store-workspaces/{workspace_id}",
    response_model=list[ManualApproval],
)
async def list_pending_approvals(
    workspace_id: str,
    gateway: Annotated[ManualApprovalGateway, Depends(get_manual_approval_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[ManualApproval]:
    """执行 list_pending_approvals 的业务流程并返回该流程的结果。

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
    return await gateway.list_pending(workspace_id=workspace_id, limit=limit)
