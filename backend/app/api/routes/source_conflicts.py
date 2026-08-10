from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_quality_finding_gateway, get_store_workspace_gateway
from backend.app.domain.data_quality import QualityFinding, QualityFindingGateway
from backend.app.domain.source_conflict import SourceConflict, find_source_conflicts
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/data-quality", tags=["data-quality"])


class SourceConflictPayload(BaseModel):
    records: dict[str, dict[str, object]]
    fields: list[str] = Field(default_factory=list)


@router.post("/source-conflicts", response_model=list[SourceConflict])
async def source_conflicts(payload: SourceConflictPayload) -> list[SourceConflict]:
    return find_source_conflicts(**payload.model_dump())


@router.post(
    "/store-workspaces/{workspace_id}/source-conflicts-and-isolate",
    response_model=list[SourceConflict],
)
async def source_conflicts_and_isolate(
    workspace_id: str,
    payload: SourceConflictPayload,
    gateway: Annotated[QualityFindingGateway, Depends(get_quality_finding_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[SourceConflict]:
    """保存跨来源冲突到质量隔离区，官方事实不会被估算或导入值覆盖。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    conflicts = await source_conflicts(payload)
    findings = [QualityFinding(
        rule_code="DQ-006-CONFLICT", field_name=item.field,
        severity="warning", message=item.message,
    ) for item in conflicts]
    if findings:
        await gateway.create_findings(workspace_id=workspace_id, findings=findings)
    return conflicts
