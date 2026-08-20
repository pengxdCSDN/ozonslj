"""说明本模块的职责、边界和主要协作对象。"""

import os
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.api.dependencies import ReadinessProbe, get_readiness_probe
from backend.app.infrastructure.local.chroma_health import ChromaHealthProbe
from backend.app.infrastructure.observability import update_resource_metrics

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """说明 HealthResponse 的职责、状态边界和对外协作关系。"""
    status: Literal["ok"]


class RagHealthResponse(BaseModel):
    """说明 RagHealthResponse 的职责、状态边界和对外协作关系。"""
    state: Literal["healthy", "not_configured"]
    latency_ms: int | None
    detail: str | None


class OpsHealthResponse(BaseModel):
    """说明 OpsHealthResponse 的职责、状态边界和对外协作关系。"""
    status: Literal["ok", "warning"]
    disk_used_ratio: float | None
    memory_available_bytes: int | None
    swap_free_bytes: int | None


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """执行 liveness 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def readiness(
    probe: Annotated[ReadinessProbe, Depends(get_readiness_probe)],
) -> HealthResponse:
    """执行 readiness 的业务流程并返回该流程的结果。

Args:
    probe: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    try:
        await probe.check()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "infrastructure_unavailable", "message": "依赖服务尚未就绪"},
        ) from error
    return HealthResponse(status="ok")


@router.get("/rag", response_model=RagHealthResponse)
async def rag_health() -> RagHealthResponse:
    """报告 Chroma 状态；未配置时不阻塞核心 API，配置后故障返回 503。
Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""

    result = await ChromaHealthProbe(os.getenv("CHROMA_URL")).check()
    if result.state == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "chroma_unavailable", "message": result.detail},
        )
    return RagHealthResponse(
        state=cast(Literal["healthy", "not_configured"], result.state),
        latency_ms=result.latency_ms,
        detail=result.detail,
    )


@router.get("/ops", response_model=OpsHealthResponse)
async def operations_health() -> OpsHealthResponse:
    """发布后资源门禁；阈值只用于告警，不阻断登录和业务只读页面。
Returns:
    返回调用完成后的领域结果。"""
    snapshot = update_resource_metrics()
    warning = snapshot.disk_used_ratio is not None and snapshot.disk_used_ratio >= 0.85
    return OpsHealthResponse(
        status="warning" if warning else "ok",
        disk_used_ratio=snapshot.disk_used_ratio,
        memory_available_bytes=snapshot.memory_bytes,
        swap_free_bytes=snapshot.swap_bytes,
    )
