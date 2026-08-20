"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_external_notification_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.external_notification import (
    ExternalNotificationConfig,
    ExternalNotificationGateway,
    render_notification_preview,
    validate_notification_config,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


class ExternalNotificationPayload(BaseModel):
    """说明 ExternalNotificationPayload 的职责、状态边界和对外协作关系。"""
    channel: str = Field(min_length=1)
    enabled: bool = False
    template: str = Field(min_length=1, max_length=2000)
    retry_limit: int = Field(default=2, ge=0, le=5)
    sensitive_data_allowed: bool = False


class NotificationPreviewPayload(BaseModel):
    """说明 NotificationPreviewPayload 的职责、状态边界和对外协作关系。"""
    template: str = Field(min_length=1, max_length=2000)
    values: dict[str, object] = Field(default_factory=dict)


@router.post("/preview", response_model=str)
async def preview_notification(payload: NotificationPreviewPayload) -> str:
    """执行 preview_notification 的业务流程并返回该流程的结果。"""
    try:
        return render_notification_preview(payload.template, payload.values)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "notification_template_invalid", "message": str(error)},
        ) from error


@router.post("/validate", response_model=ExternalNotificationConfig)
async def validate(payload: ExternalNotificationPayload) -> ExternalNotificationConfig:
    """执行 validate 的业务流程并返回该流程的结果。"""
    try:
        return validate_notification_config(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "notification_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/validate-and-save",
    response_model=ExternalNotificationConfig,
)
async def validate_and_save(
    workspace_id: str,
    payload: ExternalNotificationPayload,
    gateway: Annotated[ExternalNotificationGateway, Depends(get_external_notification_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> ExternalNotificationConfig:
    """执行 validate_and_save 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    config = await validate(payload)
    return await gateway.save_config(workspace_id=workspace_id, config=config)


@router.get(
    "/store-workspaces/{workspace_id}/history",
    response_model=list[ExternalNotificationConfig],
)
async def list_notification_configs(
    workspace_id: str,
    gateway: Annotated[ExternalNotificationGateway, Depends(get_external_notification_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[ExternalNotificationConfig]:
    """执行 list_notification_configs 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_configs(workspace_id=workspace_id, limit=limit)
