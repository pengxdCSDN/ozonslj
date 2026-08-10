from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_quality_finding_gateway, get_store_workspace_gateway
from backend.app.domain.data_quality import QualityFinding, QualityFindingGateway
from backend.app.domain.public_sampling import PublicSampler, SamplingRequest, SamplingResult
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/public-sampling", tags=["public-sampling"])


class SamplingRequestPayload(BaseModel):
    url: str
    robots_allowed: bool = True
    rate_limited: bool = False
    stop_requested: bool = False


class SamplingBatchPayload(BaseModel):
    requests: list[SamplingRequestPayload]
    global_limit: int = Field(default=2, ge=1, le=2)
    max_attempts: int = Field(default=3, ge=1, le=5)


async def _stub_fetch_page(url: str) -> int:
    """默认 Stub 只用于开发验证，真实 HTTP 适配器需单独实现并复核官方策略。"""
    del url
    return 200


@router.post("/preview", response_model=list[SamplingResult])
async def sample_preview(payload: SamplingBatchPayload) -> list[SamplingResult]:
    sampler = PublicSampler(
        _stub_fetch_page, global_limit=payload.global_limit, max_attempts=payload.max_attempts
    )
    return await sampler.sample([SamplingRequest(**item.model_dump()) for item in payload.requests])


@router.post(
    "/store-workspaces/{workspace_id}/preview-and-record",
    response_model=list[SamplingResult],
)
async def sample_preview_and_record(
    workspace_id: str,
    payload: SamplingBatchPayload,
    gateway: Annotated[QualityFindingGateway, Depends(get_quality_finding_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[SamplingResult]:
    """执行受控采样预览并记录被阻止的请求，当前仍只使用 Stub。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    results = await sample_preview(payload)
    findings = [QualityFinding(
        rule_code=f"RES-006-{result.message.split(':', 1)[0].upper()}",
        field_name="url", severity="error", message=result.message,
    ) for result in results if not result.allowed]
    if findings:
        await gateway.create_findings(workspace_id=workspace_id, findings=findings)
    return results
