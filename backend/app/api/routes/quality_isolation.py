"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_quality_finding_gateway, get_store_workspace_gateway
from backend.app.domain.data_quality import QualityFinding, QualityFindingGateway
from backend.app.domain.quality_isolation import IsolationResult, isolate_invalid_records
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/data-quality", tags=["data-quality"])


class IsolationPayload(BaseModel):
    """说明 IsolationPayload 的职责、状态边界和对外协作关系。"""
    records: list[dict[str, object]]
    invalid_rows: set[int] = Field(default_factory=set)
    reason: str = Field(min_length=1, max_length=300)


@router.post("/isolate", response_model=IsolationResult)
async def isolate(payload: IsolationPayload) -> IsolationResult:
    """执行 isolate 的业务流程并返回该流程的结果。"""
    return isolate_invalid_records(**payload.model_dump())


@router.post("/store-workspaces/{workspace_id}/isolate-and-save", response_model=IsolationResult)
async def isolate_and_save(
    workspace_id: str,
    payload: IsolationPayload,
    gateway: Annotated[QualityFindingGateway, Depends(get_quality_finding_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> IsolationResult:
    """把隔离行写入质量中心，原始记录保持只读且不参与业务分析。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    result = await isolate(payload)
    findings = [QualityFinding(
        rule_code="DQ-007-ISOLATED", field_name=f"row_{item.row_index}",
        severity="error", message=item.reason,
    ) for item in result.isolated]
    if findings:
        await gateway.create_findings(workspace_id=workspace_id, findings=findings)
    return result
