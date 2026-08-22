"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_quality_finding_gateway, get_store_workspace_gateway
from backend.app.config import get_settings
from backend.app.domain.data_quality import QualityFinding, QualityFindingGateway
from backend.app.domain.public_sampling import PublicSampler, SamplingRequest, SamplingResult
from backend.app.domain.store_workspace import StoreWorkspaceGateway
from backend.app.infrastructure.public_sampling import PublicHttpFetcher

router = APIRouter(prefix="/v1/public-sampling", tags=["public-sampling"])


class SamplingRequestPayload(BaseModel):
    """说明 SamplingRequestPayload 的职责、状态边界和对外协作关系。"""
    url: str
    robots_allowed: bool = True
    rate_limited: bool = False
    stop_requested: bool = False


class SamplingBatchPayload(BaseModel):
    """说明 SamplingBatchPayload 的职责、状态边界和对外协作关系。"""
    requests: list[SamplingRequestPayload]
    global_limit: int = Field(default=2, ge=1, le=2)
    max_attempts: int = Field(default=3, ge=1, le=5)


async def _stub_fetch_page(url: str) -> int:
    """默认 Stub 只用于开发验证，真实 HTTP 适配器需单独实现并复核官方策略。

Args:
    url: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    del url
    return 200


@router.post("/preview", response_model=list[SamplingResult])
async def sample_preview(payload: SamplingBatchPayload) -> list[SamplingResult]:
    """执行 sample_preview 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    sampler = PublicSampler(
        _stub_fetch_page, global_limit=payload.global_limit, max_attempts=payload.max_attempts
    )
    return await sampler.sample([SamplingRequest(**item.model_dump()) for item in payload.requests])


@router.post("/live-preview", response_model=list[SamplingResult])
async def live_sample_preview(payload: SamplingBatchPayload) -> list[SamplingResult]:
    """使用服务端白名单执行真实只读采样；未配置白名单时拒绝启动网络请求。"""
    try:
        settings = get_settings()
    except ValueError as error:
        raise HTTPException(status_code=503, detail={"code": "sampling_not_configured"}) from error
    allowed_hosts = frozenset(
        host.strip().lower()
        for host in settings.public_sampling_allowed_hosts.split(",")
        if host.strip()
    )
    if not allowed_hosts:
        raise HTTPException(status_code=503, detail={"code": "sampling_not_configured"})
    async with httpx.AsyncClient(timeout=10.0) as client:
        fetcher = PublicHttpFetcher(
            client, allowed_hosts=allowed_hosts, user_agent=settings.public_sampling_user_agent
        )
        sampler = PublicSampler(
            fetcher.fetch_page,
            global_limit=payload.global_limit,
            max_attempts=payload.max_attempts,
        )
        return await sampler.sample(
            [
                SamplingRequest(item.url, stop_requested=item.stop_requested)
                for item in payload.requests
            ]
        )


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
    """执行受控采样预览并记录被阻止的请求，当前仍只使用 Stub。

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
    results = await sample_preview(payload)
    findings = [QualityFinding(
        rule_code=f"RES-006-{result.message.split(':', 1)[0].upper()}",
        field_name="url", severity="error", message=result.message,
    ) for result in results if not result.allowed]
    if findings:
        await gateway.create_findings(workspace_id=workspace_id, findings=findings)
    return results
