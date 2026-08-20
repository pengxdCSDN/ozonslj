"""说明本模块的职责、边界和主要协作对象。"""

from datetime import UTC, datetime, timedelta
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
from backend.app.infrastructure.ozon.performance_client import (
    PerformanceApiError,
    PerformanceTokenError,
    fetch_performance_campaigns,
    request_performance_token,
)

router = APIRouter(prefix="/v1/advertising/performance-oauth", tags=["advertising"])


class PerformanceTokenPayload(BaseModel):
    """说明 PerformanceTokenPayload 的职责、状态边界和对外协作关系。"""
    access_token: str
    expires_at: datetime
    refresh_token: str | None = None


class SavePerformanceCredentialPayload(BaseModel):
    """Performance OAuth 令牌写入载荷；SecretStr 防止调试输出意外泄露明文。"""

    client_id_present: bool = False
    access_token: SecretStr
    refresh_token: SecretStr | None = None
    expires_at: datetime


class SavePerformanceClientCredentialsPayload(BaseModel):
    """说明 SavePerformanceClientCredentialsPayload 的职责、状态边界和对外协作关系。"""
    client_id: str
    client_secret: SecretStr


@router.post("/inspect", response_model=PerformanceToken)
async def inspect_performance_token(payload: PerformanceTokenPayload) -> PerformanceToken:
    """执行 inspect_performance_token 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
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
    """执行 save_performance_credentials 的业务流程并返回该流程的结果。

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
    """执行 get_performance_credentials_status 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    status_result = await gateway.get_status(workspace_id=workspace_id)
    if status_result is None:
        raise HTTPException(status_code=404, detail={"code": "performance_credentials_not_found"})
    return status_result


@router.post(
    "/store-workspaces/{workspace_id}/client-credentials",
    response_model=PerformanceCredentialStatus,
)
async def save_performance_client_credentials(
    workspace_id: str,
    payload: SavePerformanceClientCredentialsPayload,
    gateway: Annotated[PerformanceCredentialGateway, Depends(get_performance_credential_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> PerformanceCredentialStatus:
    """执行 save_performance_client_credentials 的业务流程并返回该流程的结果。

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
    try:
        return await gateway.save_client_credentials(
            workspace_id=workspace_id,
            client_id=payload.client_id,
            client_secret=payload.client_secret.get_secret_value(),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "performance_client_credentials_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/token",
    response_model=PerformanceCredentialStatus,
)
async def refresh_performance_token(
    workspace_id: str,
    gateway: Annotated[PerformanceCredentialGateway, Depends(get_performance_credential_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> PerformanceCredentialStatus:
    """执行 refresh_performance_token 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    credentials = await gateway.get_client_credentials(workspace_id=workspace_id)
    if credentials is None:
        raise HTTPException(
            status_code=422, detail={"code": "performance_client_credentials_missing"}
        )
    try:
        access_token, expires_at = await request_performance_token(
            client_id=credentials[0], client_secret=credentials[1],
        )
        return await gateway.save_tokens(
            workspace_id=workspace_id,
            client_id_present=True,
            access_token=access_token,
            refresh_token=None,
            expires_at=expires_at.isoformat(),
        )
    except PerformanceTokenError as error:
        raise HTTPException(
            status_code=502,
            detail={"code": error.code, "message": str(error)},
        ) from error


async def _ensure_performance_access_token(
    workspace_id: str, gateway: PerformanceCredentialGateway,
) -> str:
    """在真实只读调用前复用有效令牌，临近过期时自动换取新令牌。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    current = await gateway.get_access_token(workspace_id=workspace_id)
    if current is not None:
        token, stored_expires_at = current
        expiry = datetime.fromisoformat(stored_expires_at.replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        if expiry > datetime.now(UTC) + timedelta(seconds=60):
            return token
    credentials = await gateway.get_client_credentials(workspace_id=workspace_id)
    if credentials is None:
        raise HTTPException(
            status_code=422, detail={"code": "performance_client_credentials_missing"}
        )
    try:
        token, token_expires_at = await request_performance_token(
            client_id=credentials[0], client_secret=credentials[1],
        )
        await gateway.save_tokens(
            workspace_id=workspace_id, client_id_present=True, access_token=token,
            refresh_token=None, expires_at=token_expires_at.isoformat(),
        )
        return token
    except PerformanceTokenError as error:
        raise HTTPException(
            status_code=502,
            detail={"code": error.code, "message": str(error)},
        ) from error


@router.get("/store-workspaces/{workspace_id}/campaigns")
async def list_performance_campaigns(
    workspace_id: str,
    gateway: Annotated[PerformanceCredentialGateway, Depends(get_performance_credential_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> dict[str, object]:
    """自动刷新令牌后读取 Performance 广告活动；该接口只读。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    token = await _ensure_performance_access_token(workspace_id, gateway)
    try:
        return await fetch_performance_campaigns(access_token=token)
    except PerformanceApiError as error:
        raise HTTPException(
            status_code=403 if error.code == "performance_permission_denied" else 502,
            detail={"code": error.code, "message": str(error)},
        ) from error
