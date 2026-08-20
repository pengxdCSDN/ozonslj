"""说明本模块的职责、边界和主要协作对象。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.domain.performance_credentials import (
    PerformanceCredentialStatus,
    inspect_performance_credentials,
)

router = APIRouter(prefix="/v1/performance/credentials", tags=["advertising"])


class PerformanceCredentialPayload(BaseModel):
    """说明 PerformanceCredentialPayload 的职责、状态边界和对外协作关系。"""
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: str | None = None


@router.post("/inspect", response_model=PerformanceCredentialStatus)
async def inspect(payload: PerformanceCredentialPayload) -> PerformanceCredentialStatus:
    """执行 inspect 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    try:
        return inspect_performance_credentials(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "performance_credentials_invalid", "message": str(error)},
        ) from error
