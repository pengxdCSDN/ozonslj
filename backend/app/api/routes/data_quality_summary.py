"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.app.api.dependencies import get_quality_finding_gateway, get_store_workspace_gateway
from backend.app.domain.data_quality import QualityFindingGateway, QualityFindingStatus
from backend.app.domain.quality_dashboard import summarize_quality_findings
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/store-workspaces", tags=["data-quality"])


class QualitySummaryResponse(BaseModel):
    """说明 QualitySummaryResponse 的职责、状态边界和对外协作关系。"""
    total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_rule: dict[str, int]


@router.get("/{workspace_id}/data-quality/summary", response_model=QualitySummaryResponse)
async def get_quality_summary(
    workspace_id: str,
    gateway: Annotated[QualityFindingGateway, Depends(get_quality_finding_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    finding_status: Annotated[QualityFindingStatus | None, Query(alias="status")] = None,
) -> QualitySummaryResponse:
    """返回质量中心摘要；只读查询，不改变隔离记录和业务事实。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。
    finding_status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""

    workspace = await workspace_gateway.get_workspace(workspace_id)
    if workspace is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    findings = await gateway.list_findings(
        workspace_id=workspace_id, status=finding_status, limit=100
    )
    return QualitySummaryResponse(**asdict(summarize_quality_findings(findings)))
