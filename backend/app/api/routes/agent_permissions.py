"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_agent_permission_gateway, get_store_workspace_gateway
from backend.app.domain.agent_permissions import (
    AgentPermissionDecision,
    AgentPermissionGateway,
    evaluate_agent_permissions,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/agents", tags=["assistant"])


class AgentPermissionPayload(BaseModel):
    """说明 AgentPermissionPayload 的职责、状态边界和对外协作关系。"""
    agent: str = Field(min_length=1, max_length=100)
    requested_capabilities: list[str] = Field(default_factory=list)


@router.post("/permissions/check", response_model=AgentPermissionDecision)
async def check_permissions(payload: AgentPermissionPayload) -> AgentPermissionDecision:
    """执行 check_permissions 的业务流程并返回该流程的结果。"""
    try:
        return evaluate_agent_permissions(payload.agent, payload.requested_capabilities)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "agent_permissions_invalid", "message": str(error)},
        ) from error


@router.post(
    "/permissions/store-workspaces/{workspace_id}/check-and-save",
    response_model=AgentPermissionDecision,
)
async def check_and_save_permissions(
    workspace_id: str,
    payload: AgentPermissionPayload,
    gateway: Annotated[AgentPermissionGateway, Depends(get_agent_permission_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> AgentPermissionDecision:
    """执行 check_and_save_permissions 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    decision = await check_permissions(payload)
    return await gateway.save_decision(workspace_id=workspace_id, decision=decision)


@router.get(
    "/permissions/store-workspaces/{workspace_id}/history",
    response_model=list[AgentPermissionDecision],
)
async def list_permission_history(
    workspace_id: str,
    gateway: Annotated[AgentPermissionGateway, Depends(get_agent_permission_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[AgentPermissionDecision]:
    """执行 list_permission_history 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_decisions(workspace_id=workspace_id, limit=limit)
