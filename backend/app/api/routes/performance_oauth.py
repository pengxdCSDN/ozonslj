from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, SecretStr

from backend.app.api.dependencies import (
    get_performance_credential_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.performance_credentials import (
    PerformanceCredentialGateway,
    PerformanceCredentialStatus,
)
from backend.app.domain.performance_oauth import PerformanceToken, build_performance_token
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/advertising/performance-oauth", tags=["advertising"])


class PerformanceTokenPayload(BaseModel):
    access_token: str
    expires_at: datetime
    refresh_token: str | None = None


class SavePerformanceCredentialPayload(BaseModel):
    """Performance OAuth 令牌写入载荷；SecretStr 防止调试输出意外泄露明文。"""

    client_id_present: bool = False
    access_token: SecretStr
    refresh_token: SecretStr | None = None
    expires_at: datetime


@router.post("/inspect", response_model=PerformanceToken)
async def inspect_performance_token(payload: PerformanceTokenPayload) -> PerformanceToken:
    try:
        return build_performance_token(
            payload.access_token, payload.expires_at, payload.refresh_token
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "performance_oauth_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/credentials",
    response_model=PerformanceCredentialStatus,
)
async def save_performance_credentials(
    workspace_id: str,
    payload: SavePerformanceCredentialPayload,
    gateway: Annotated[PerformanceCredentialGateway, Depends(get_performance_credential_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> PerformanceCredentialStatus:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    try:
        return await gateway.save_tokens(
            workspace_id=workspace_id,
            client_id_present=payload.client_id_present,
            access_token=payload.access_token.get_secret_value(),
            refresh_token=(
                payload.refresh_token.get_secret_value()
                if payload.refresh_token is not None
                else None
            ),
            expires_at=payload.expires_at.isoformat(),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "performance_credentials_invalid", "message": str(error)},
        ) from error


@router.get(
    "/store-workspaces/{workspace_id}/credentials",
    response_model=PerformanceCredentialStatus,
)
async def get_performance_credentials_status(
    workspace_id: str,
    gateway: Annotated[PerformanceCredentialGateway, Depends(get_performance_credential_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> PerformanceCredentialStatus:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    status_result = await gateway.get_status(workspace_id=workspace_id)
    if status_result is None:
        raise HTTPException(status_code=404, detail={"code": "performance_credentials_not_found"})
    return status_result
