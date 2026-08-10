from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.api.dependencies import ReadinessProbe, get_readiness_probe

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


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
