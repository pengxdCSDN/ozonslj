"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import get_quality_finding_gateway, get_store_workspace_gateway
from backend.app.domain.data_quality import QualityFinding, QualityFindingGateway
from backend.app.domain.sampling_policy import SamplingPolicyDecision, check_sampling_policy
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/sampling-policy", tags=["sampling-policy"])


class SamplingPolicyRequest(BaseModel):
    """说明 SamplingPolicyRequest 的职责、状态边界和对外协作关系。"""
    url: str
    robots_allowed: bool
    rate_limited: bool = False
    stop_requested: bool = False


@router.post("/check", response_model=SamplingPolicyDecision)
async def check_policy(payload: SamplingPolicyRequest) -> SamplingPolicyDecision:
    """执行 check_policy 的业务流程并返回该流程的结果。"""
    return check_sampling_policy(
        payload.url,
        robots_allowed=payload.robots_allowed,
        rate_limited=payload.rate_limited,
        stop_requested=payload.stop_requested,
    )


@router.post(
    "/store-workspaces/{workspace_id}/check-and-record",
    response_model=SamplingPolicyDecision,
)
async def check_and_record_policy(
    workspace_id: str,
    payload: SamplingPolicyRequest,
    gateway: Annotated[QualityFindingGateway, Depends(get_quality_finding_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> SamplingPolicyDecision:
    """请求前执行合规检查；禁止原因写入质量隔离区，调用方不得继续发请求。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    decision = await check_policy(payload)
    if not decision.allowed:
        await gateway.create_findings(workspace_id=workspace_id, findings=[QualityFinding(
            rule_code=f"RES-005-{decision.code.upper()}", field_name="url",
            severity="error", message=decision.message,
        )])
    return decision
