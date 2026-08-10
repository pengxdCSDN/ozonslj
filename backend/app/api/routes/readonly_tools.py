from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_readonly_tool_gateway, get_store_workspace_gateway
from backend.app.domain.readonly_tool import (
    ReadonlyToolDecision,
    ReadonlyToolGateway,
    authorize_readonly_tool,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/assistant/tools", tags=["assistant"])


class ReadonlyToolPayload(BaseModel):
    tool: str = Field(min_length=1, max_length=80)
    parameters: dict[str, object] = Field(default_factory=dict)


@router.post("/authorize", response_model=ReadonlyToolDecision)
async def authorize_tool(payload: ReadonlyToolPayload) -> ReadonlyToolDecision:
    return authorize_readonly_tool(payload.tool, payload.parameters)


@router.post(
    "/store-workspaces/{workspace_id}/authorize-and-save",
    response_model=ReadonlyToolDecision,
)
async def authorize_and_save_tool(
    workspace_id: str,
    payload: ReadonlyToolPayload,
    gateway: Annotated[ReadonlyToolGateway, Depends(get_readonly_tool_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> ReadonlyToolDecision:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    decision = await authorize_tool(payload)
    return await gateway.save_decision(workspace_id=workspace_id, decision=decision)


@router.get(
    "/store-workspaces/{workspace_id}/history",
    response_model=list[ReadonlyToolDecision],
)
async def list_tool_history(
    workspace_id: str,
    gateway: Annotated[ReadonlyToolGateway, Depends(get_readonly_tool_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[ReadonlyToolDecision]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_decisions(workspace_id=workspace_id, limit=limit)
