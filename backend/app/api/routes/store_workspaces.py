"""说明本模块的职责、边界和主要协作对象。"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.dependencies import (
    get_credential_protector,
    get_seller_account_verifier,
    get_store_workspace_gateway,
    require_account_manager,
)
from backend.app.domain.identity import AuthenticatedUser
from backend.app.domain.store_workspace import (
    ClientIdConflictError,
    CreateStoreWorkspace,
    CredentialProtectionError,
    CredentialProtector,
    OzonAuthenticationError,
    OzonCredentials,
    OzonMalformedResponseError,
    OzonPermissionError,
    OzonRateLimitError,
    OzonTemporaryError,
    ReplaceStoreCredentials,
    SellerAccountVerifier,
    StoreWorkspace,
    StoreWorkspaceGateway,
)

router = APIRouter(prefix="/v1/store-workspaces", tags=["store-workspaces"])


@router.get("", response_model=list[StoreWorkspace])
async def list_store_workspaces(
    gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[StoreWorkspace]:
    """执行 list_store_workspaces 的业务流程并返回该流程的结果。"""
    return await gateway.list_workspaces()


@router.post(
    "",
    response_model=StoreWorkspace,
    status_code=status.HTTP_201_CREATED,
)
async def create_store_workspace(
    request: CreateStoreWorkspace,
    gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    protector: Annotated[CredentialProtector, Depends(get_credential_protector)],
    _account_manager: Annotated[AuthenticatedUser, Depends(require_account_manager)],
) -> StoreWorkspace:
    """执行 create_store_workspace 的业务流程并返回该流程的结果。"""
    encrypted_api_key = protector.protect(request.api_key.get_secret_value())
    try:
        return await gateway.create_workspace(
            display_name=request.display_name,
            client_id=request.client_id,
            encrypted_api_key=encrypted_api_key,
            credential_version=protector.key_version,
        )
    except ClientIdConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "client_id_conflict", "message": "Client ID 已被使用"},
        ) from error


@router.put("/{workspace_id}/credentials", response_model=StoreWorkspace)
async def replace_store_credentials(
    workspace_id: str,
    request: ReplaceStoreCredentials,
    gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    protector: Annotated[CredentialProtector, Depends(get_credential_protector)],
    _account_manager: Annotated[AuthenticatedUser, Depends(require_account_manager)],
) -> StoreWorkspace:
    """执行 replace_store_credentials 的业务流程并返回该流程的结果。"""
    encrypted_api_key = protector.protect(request.api_key.get_secret_value())
    try:
        workspace = await gateway.replace_credentials(
            workspace_id=workspace_id,
            client_id=request.client_id,
            encrypted_api_key=encrypted_api_key,
            credential_version=protector.key_version,
        )
    except ClientIdConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "client_id_conflict", "message": "Client ID 已被使用"},
        ) from error
    if workspace is None:
        raise _workspace_not_found()
    return workspace


@router.post("/{workspace_id}/verify", response_model=StoreWorkspace)
async def verify_store_workspace(
    workspace_id: str,
    gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    protector: Annotated[CredentialProtector, Depends(get_credential_protector)],
    verifier: Annotated[SellerAccountVerifier, Depends(get_seller_account_verifier)],
    _account_manager: Annotated[AuthenticatedUser, Depends(require_account_manager)],
) -> StoreWorkspace:
    """执行 verify_store_workspace 的业务流程并返回该流程的结果。"""
    workspace = await gateway.get_workspace(workspace_id)
    stored_credentials = await gateway.load_credentials(workspace_id)
    if workspace is None or stored_credentials is None:
        raise _workspace_not_found()

    client_id, encrypted_api_key, credential_version = stored_credentials
    try:
        api_key = protector.unprotect(
            encrypted_api_key,
            credential_version=credential_version,
        )
    except CredentialProtectionError as error:
        await gateway.set_verification_status(
            workspace_id=workspace_id,
            status="invalid",
            verified_at=None,
            audit_result="failed",
            audit_detail={"error_type": "credential_protection"},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "credential_unavailable",
                "message": "本机无法解密凭据，请重新填写后验证",
            },
        ) from error

    try:
        await verifier.verify(OzonCredentials(client_id=client_id, api_key=api_key))
    except OzonAuthenticationError as error:
        return await _mark_invalid_and_raise(
            gateway,
            workspace_id,
            "authentication_failed",
            "Ozon 拒绝了当前凭据",
            status.HTTP_401_UNAUTHORIZED,
            error,
        )
    except OzonPermissionError as error:
        return await _mark_invalid_and_raise(
            gateway,
            workspace_id,
            "permission_denied",
            "当前凭据缺少必要权限",
            status.HTTP_403_FORBIDDEN,
            error,
        )
    except OzonRateLimitError as error:
        await _audit_retryable_failure(gateway, workspace, "rate_limited")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limited", "message": "Ozon 请求受限，请稍后重试"},
        ) from error
    except (OzonTemporaryError, OzonMalformedResponseError) as error:
        error_type = (
            "malformed_response"
            if isinstance(error, OzonMalformedResponseError)
            else "temporary_failure"
        )
        await _audit_retryable_failure(gateway, workspace, error_type)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": error_type,
                "message": "暂时无法完成 Ozon 验证，请稍后重试",
            },
        ) from error

    verified = await gateway.set_verification_status(
        workspace_id=workspace_id,
        status="active",
        verified_at=datetime.now(UTC),
        audit_result="success",
        audit_detail={"status": "active"},
    )
    if verified is None:
        raise _workspace_not_found()
    return verified


async def _mark_invalid_and_raise(
    gateway: StoreWorkspaceGateway,
    workspace_id: str,
    error_type: str,
    message: str,
    status_code: int,
    cause: Exception,
) -> StoreWorkspace:
    """执行内部步骤 _mark_invalid_and_raise，供同一模块的公开流程复用。"""
    await gateway.set_verification_status(
        workspace_id=workspace_id,
        status="invalid",
        verified_at=None,
        audit_result="failed",
        audit_detail={"error_type": error_type},
    )
    raise HTTPException(
        status_code=status_code,
        detail={"code": error_type, "message": message},
    ) from cause


async def _audit_retryable_failure(
    gateway: StoreWorkspaceGateway,
    workspace: StoreWorkspace,
    error_type: str,
) -> None:
    # 暂时性失败不应让已验证工作区失效，pending 也保持可重试。
    """执行内部步骤 _audit_retryable_failure，供同一模块的公开流程复用。"""
    await gateway.set_verification_status(
        workspace_id=workspace.id,
        status=workspace.status,
        verified_at=workspace.verified_at,
        audit_result="failed",
        audit_detail={"error_type": error_type},
    )


def _workspace_not_found() -> HTTPException:
    """执行内部步骤 _workspace_not_found，供同一模块的公开流程复用。"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "workspace_not_found", "message": "工作区不存在"},
    )
