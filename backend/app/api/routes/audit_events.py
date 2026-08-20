"""说明本模块的职责、边界和主要协作对象。"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_audit_event_gateway, get_store_workspace_gateway
from backend.app.domain.audit_event import AuditEvent, create_audit_event
from backend.app.domain.audit_event_store import AuditEventGateway, StoredAuditEvent
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/review/audit-events", tags=["review"])


class AuditEventPayload(BaseModel):
    """说明 AuditEventPayload 的职责、状态边界和对外协作关系。"""
    event_type: str = Field(min_length=1, max_length=100)
    subject_id: str = Field(min_length=1, max_length=200)
    detail: dict[str, object] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class StoredAuditEventResponse(BaseModel):
    """说明 StoredAuditEventResponse 的职责、状态边界和对外协作关系。"""
    event_id: str
    workspace_id: str
    event: AuditEvent


@router.post("/build", response_model=AuditEvent)
async def build_event(payload: AuditEventPayload) -> AuditEvent:
    """执行 build_event 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return create_audit_event(**payload.model_dump())


@router.post("/store-workspaces/{workspace_id}", response_model=StoredAuditEventResponse)
async def save_event(
    workspace_id: str,
    payload: AuditEventPayload,
    gateway: Annotated[AuditEventGateway, Depends(get_audit_event_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> StoredAuditEvent:
    """执行 save_event 的业务流程并返回该流程的结果。

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
    return await gateway.save(
        workspace_id=workspace_id, event=create_audit_event(**payload.model_dump())
    )


@router.get("/store-workspaces/{workspace_id}", response_model=list[StoredAuditEventResponse])
async def list_events(
    workspace_id: str,
    gateway: Annotated[AuditEventGateway, Depends(get_audit_event_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[StoredAuditEvent]:
    """执行 list_events 的业务流程并返回该流程的结果。

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
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_events(workspace_id=workspace_id, limit=limit)
