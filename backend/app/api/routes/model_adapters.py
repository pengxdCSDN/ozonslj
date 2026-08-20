"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_model_adapter_gateway, get_store_workspace_gateway
from backend.app.domain.model_adapter import (
    ModelAdapterConfig,
    ModelAdapterGateway,
    inspect_model_adapter,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/model-adapters", tags=["model-adapters"])


class ModelAdapterPayload(BaseModel):
    """说明 ModelAdapterPayload 的职责、状态边界和对外协作关系。"""
    adapter: str = Field(min_length=1, max_length=80)
    provider: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=160)
    base_url: str | None = None
    enabled: bool = False
    credential_configured: bool = False


@router.post("/inspect", response_model=ModelAdapterConfig)
async def inspect_adapter(payload: ModelAdapterPayload) -> ModelAdapterConfig:
    """执行 inspect_adapter 的业务流程并返回该流程的结果。"""
    try:
        return inspect_model_adapter(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "model_adapter_invalid", "message": str(error)},
        ) from error


@router.post("/store-workspaces/{workspace_id}/inspect-and-save", response_model=ModelAdapterConfig)
async def inspect_and_save_adapter(
    workspace_id: str,
    payload: ModelAdapterPayload,
    gateway: Annotated[ModelAdapterGateway, Depends(get_model_adapter_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> ModelAdapterConfig:
    """执行 inspect_and_save_adapter 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    config = await inspect_adapter(payload)
    return await gateway.save_config(workspace_id=workspace_id, config=config)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[ModelAdapterConfig])
async def list_adapter_history(
    workspace_id: str,
    gateway: Annotated[ModelAdapterGateway, Depends(get_model_adapter_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[ModelAdapterConfig]:
    """执行 list_adapter_history 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_configs(workspace_id=workspace_id, limit=limit)


@router.get("/store-workspaces/{workspace_id}/active", response_model=ModelAdapterConfig | None)
async def get_active_adapter(
    workspace_id: str,
    gateway: Annotated[ModelAdapterGateway, Depends(get_model_adapter_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> ModelAdapterConfig | None:
    """执行 get_active_adapter 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.get_active_config(workspace_id=workspace_id)
