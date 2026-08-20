"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from backend.app.domain.data_quality import (
    QualityFinding,
    check_amount_and_inventory,
    check_cross_source_consistency,
    check_relationship_and_time,
    check_required_and_enum,
)

router = APIRouter(prefix="/v1/data-quality", tags=["data-quality"])


class QualityCheckRequest(BaseModel):
    """说明 QualityCheckRequest 的职责、状态边界和对外协作关系。"""
    record: dict[str, object]
    required_fields: tuple[str, ...] = Field(default_factory=tuple)
    enum_fields: dict[str, frozenset[str]] = Field(default_factory=dict)
    required_relationships: tuple[tuple[str, str], ...] = Field(default_factory=tuple)
    time_order: tuple[str, str] | None = None
    source_pairs: tuple[tuple[str, str], ...] = Field(default_factory=tuple)


class QualityCheckResponse(BaseModel):
    """说明 QualityCheckResponse 的职责、状态边界和对外协作关系。"""
    findings: list[QualityFinding]
    valid: bool


@router.post("/check", response_model=QualityCheckResponse)
async def check_quality(payload: Annotated[QualityCheckRequest, Body()]) -> QualityCheckResponse:
    """执行 check_quality 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    findings = check_required_and_enum(
        payload.record,
        required_fields=payload.required_fields,
        enum_fields=payload.enum_fields,
    )
    findings.extend(
        check_relationship_and_time(
            payload.record,
            required_relationships=payload.required_relationships,
            time_order=payload.time_order,
        )
    )
    findings.extend(check_amount_and_inventory(payload.record))
    findings.extend(
        check_cross_source_consistency(
            payload.record,
            source_pairs=tuple(payload.source_pairs),
        )
    )
    return QualityCheckResponse(findings=findings, valid=not findings)
