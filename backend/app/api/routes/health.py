import os
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.api.dependencies import ReadinessProbe, get_readiness_probe
from backend.app.infrastructure.local.chroma_health import ChromaHealthProbe

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


class RagHealthResponse(BaseModel):
    state: Literal["healthy", "not_configured"]
    latency_ms: int | None
    detail: str | None


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
