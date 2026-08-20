"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_quality_finding_gateway, get_store_workspace_gateway
from backend.app.domain.data_quality import QualityFinding, QualityFindingGateway
from backend.app.domain.data_quality_schema import QualitySchemaResult, check_required_and_enums
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/data-quality", tags=["data-quality"])


class QualitySchemaPayload(BaseModel):
    """说明 QualitySchemaPayload 的职责、状态边界和对外协作关系。"""
    rows: list[dict[str, object]]
    required_fields: list[str] = Field(default_factory=list)
    enum_fields: dict[str, list[str]] = Field(default_factory=dict)


@router.post("/schema-check", response_model=QualitySchemaResult)
async def schema_check(payload: QualitySchemaPayload) -> QualitySchemaResult:
    """执行 schema_check 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    try:
        return check_required_and_enums(
            payload.rows, required_fields=payload.required_fields, enum_fields=payload.enum_fields
        )
    except ValueError as error:
        detail = {"code": "quality_schema_invalid", "message": str(error)}
        raise HTTPException(status_code=422, detail=detail) from error


@router.post(
    "/store-workspaces/{workspace_id}/schema-check-and-isolate",
    response_model=QualitySchemaResult,
)
async def schema_check_and_isolate(
    workspace_id: str,
    payload: QualitySchemaPayload,
    gateway: Annotated[QualityFindingGateway, Depends(get_quality_finding_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> QualitySchemaResult:
    """执行 DQ-003 检查，并把异常转入 PostgreSQL 隔离区而非业务分析。

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
    result = await schema_check(payload)
    findings = [QualityFinding(
        rule_code=item.rule_code, field_name=f"row_{item.row_index}.{item.field}",
        severity=cast(Literal["warning", "error"], item.severity), message=item.message,
    ) for item in result.findings]
    if findings:
        await gateway.create_findings(workspace_id=workspace_id, findings=findings)
    return result
