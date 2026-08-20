from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.domain.performance_credentials import (
    PerformanceCredentialStatus,
    inspect_performance_credentials,
)

router = APIRouter(prefix="/v1/performance/credentials", tags=["advertising"])


class PerformanceCredentialPayload(BaseModel):
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: str | None = None


@router.post("/inspect", response_model=PerformanceCredentialStatus)
async def inspect(payload: PerformanceCredentialPayload) -> PerformanceCredentialStatus:
    try:
        return inspect_performance_credentials(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "performance_credentials_invalid", "message": str(error)},
        ) from error
