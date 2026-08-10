from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import get_agent_trigger_gateway, get_store_workspace_gateway
from backend.app.domain.agent_trigger import AgentTrigger, AgentTriggerGateway, create_agent_trigger
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/agent-triggers", tags=["assistant"])


class AgentTriggerPayload(BaseModel):
    trigger_type: str
    target: str
    schedule: str | None = None
    event_name: str | None = None
    enabled: bool = False


@router.post("/validate", response_model=AgentTrigger)
async def validate_trigger(payload: AgentTriggerPayload) -> AgentTrigger:
    try:
        return create_agent_trigger(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "agent_trigger_invalid", "message": str(error)},
        ) from error


@router.post("/store-workspaces/{workspace_id}/validate-and-save", response_model=AgentTrigger)
async def validate_and_save_trigger(
    workspace_id: str,
    payload: AgentTriggerPayload,
    gateway: Annotated[AgentTriggerGateway, Depends(get_agent_trigger_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> AgentTrigger:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    trigger = await validate_trigger(payload)
    return await gateway.save_trigger(workspace_id=workspace_id, trigger=trigger)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[AgentTrigger])
async def list_trigger_history(
    workspace_id: str,
    gateway: Annotated[AgentTriggerGateway, Depends(get_agent_trigger_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[AgentTrigger]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_triggers(workspace_id=workspace_id, limit=limit)
