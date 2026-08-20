"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_quality_finding_gateway, get_store_workspace_gateway
from backend.app.domain.data_quality import QualityFinding, QualityFindingGateway
from backend.app.domain.relationship_quality import RelationshipFinding, check_relationship_and_time
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/data-quality", tags=["data-quality"])


class RelationshipPayload(BaseModel):
    """说明 RelationshipPayload 的职责、状态边界和对外协作关系。"""
    rows: list[dict[str, object]]
    parent_ids: set[str] = Field(default_factory=set)
    id_field: str = "id"
    parent_field: str = "parent_id"
    time_field: str = "observed_at"


@router.post("/relationship-check", response_model=list[RelationshipFinding])
async def relationship_check(payload: RelationshipPayload) -> list[RelationshipFinding]:
    """执行 relationship_check 的业务流程并返回该流程的结果。"""
    return check_relationship_and_time(
        payload.rows, parent_ids=payload.parent_ids, id_field=payload.id_field,
        parent_field=payload.parent_field, time_field=payload.time_field,
    )


@router.post(
    "/store-workspaces/{workspace_id}/relationship-check-and-isolate",
    response_model=list[RelationshipFinding],
)
async def relationship_check_and_isolate(
    workspace_id: str,
    payload: RelationshipPayload,
    gateway: Annotated[QualityFindingGateway, Depends(get_quality_finding_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[RelationshipFinding]:
    """将孤儿、重复和时间倒退记录写入质量隔离区。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    findings = await relationship_check(payload)
    isolated = [QualityFinding(
        rule_code=item.rule_code, field_name=f"row_{item.row_index}",
        severity=cast(Literal["warning", "error"], item.severity), message=item.message,
    ) for item in findings]
    if isolated:
        await gateway.create_findings(workspace_id=workspace_id, findings=isolated)
    return findings
