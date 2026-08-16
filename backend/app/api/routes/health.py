import os
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.api.dependencies import ReadinessProbe, get_readiness_probe
from backend.app.infrastructure.local.chroma_health import ChromaHealthProbe
from backend.app.infrastructure.observability import update_resource_metrics

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


class RagHealthResponse(BaseModel):
    state: Literal["healthy", "not_configured"]
    latency_ms: int | None
    detail: str | None


class OpsHealthResponse(BaseModel):
    status: Literal["ok", "warning"]
    disk_used_ratio: float | None
    memory_available_bytes: int | None
    swap_free_bytes: int | None


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def readiness(
    probe: Annotated[ReadinessProbe, Depends(get_readiness_probe)],
) -> HealthResponse:
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
    """报告 Chroma 状态；未配置时不阻塞核心 API，配置后故障返回 503。"""

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
    """发布后资源门禁；阈值只用于告警，不阻断登录和业务只读页面。"""
    snapshot = update_resource_metrics()
    warning = snapshot.disk_used_ratio is not None and snapshot.disk_used_ratio >= 0.85
    return OpsHealthResponse(
        status="warning" if warning else "ok",
        disk_used_ratio=snapshot.disk_used_ratio,
        memory_available_bytes=snapshot.memory_bytes,
        swap_free_bytes=snapshot.swap_bytes,
    )
