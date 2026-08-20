"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.app.api.dependencies import get_quality_finding_gateway, get_store_workspace_gateway
from backend.app.domain.data_quality import (
    QualityFinding,
    QualityFindingGateway,
    QualityFindingRecord,
    QualityFindingStatus,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/store-workspaces", tags=["data-quality"])


class UpdateFindingRequest(BaseModel):
    """说明 UpdateFindingRequest 的职责、状态边界和对外协作关系。"""
    status: QualityFindingStatus


@router.post(
    "/{workspace_id}/data-quality/findings",
    response_model=list[QualityFindingRecord],
    status_code=201,
)
async def create_quality_findings(
    workspace_id: str,
    payload: list[QualityFinding],
    gateway: Annotated[QualityFindingGateway, Depends(get_quality_finding_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[QualityFindingRecord]:
    """执行 create_quality_findings 的业务流程并返回该流程的结果。

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
    workspace = await workspace_gateway.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.create_findings(workspace_id=workspace_id, findings=payload)


@router.get("/{workspace_id}/data-quality/findings", response_model=list[QualityFindingRecord])
async def list_quality_findings(
    workspace_id: str,
    gateway: Annotated[QualityFindingGateway, Depends(get_quality_finding_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    finding_status: Annotated[QualityFindingStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[QualityFindingRecord]:
    """执行 list_quality_findings 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。
    finding_status: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    workspace = await workspace_gateway.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_findings(
        workspace_id=workspace_id, status=finding_status, limit=limit
    )


@router.patch(
    "/{workspace_id}/data-quality/findings/{finding_id}",
    response_model=QualityFindingRecord,
)
async def update_quality_finding(
    workspace_id: str,
    finding_id: str,
    payload: UpdateFindingRequest,
    gateway: Annotated[QualityFindingGateway, Depends(get_quality_finding_gateway)],
) -> QualityFindingRecord:
    """执行 update_quality_finding 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    finding_id: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    record = await gateway.update_status(finding_id=finding_id, status=payload.status)
    if record is None or record.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "finding_not_found"},
        )
    return record
