"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from datetime import datetime
from uuid import uuid4

from backend.app.domain.performance_credentials import (
    PerformanceCredentialStatus,
    inspect_performance_credentials,
)
from backend.app.domain.store_workspace import CredentialProtector
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresPerformanceCredentialGateway:
    """加密保存 Performance OAuth 令牌；查询只返回状态，不返回任何明文令牌。"""

    def __init__(
        self, sessions: PostgresSessionFactory, context: TenantContext,
        protector: CredentialProtector,
    ) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。
    protector: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context
        self._protector = protector

    async def save_tokens(
        self, *, workspace_id: str, access_token: str, refresh_token: str | None,
        expires_at: str, client_id_present: bool,
    ) -> PerformanceCredentialStatus:
        """执行 save_tokens 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    access_token: 参数语义、输入边界和安全约束。
    refresh_token: 参数语义、输入边界和安全约束。
    expires_at: 参数语义、输入边界和安全约束。
    client_id_present: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(
            self._save_tokens, workspace_id, access_token, refresh_token, expires_at,
            client_id_present,
        )

    async def save_client_credentials(
        self, *, workspace_id: str, client_id: str, client_secret: str,
    ) -> PerformanceCredentialStatus:
        """执行 save_client_credentials 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    client_id: 参数语义、输入边界和安全约束。
    client_secret: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(
            self._save_client_credentials, workspace_id, client_id, client_secret,
        )

    def _save_client_credentials(
        self, workspace_id: str, client_id: str, client_secret: str,
    ) -> PerformanceCredentialStatus:
        """执行内部步骤 _save_client_credentials，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    client_id: 参数语义、输入边界和安全约束。
    client_secret: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
        if not client_id.strip() or not client_secret.strip():
            raise ValueError("Performance Client ID 和 Client Secret 不能为空")
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO performance_oauth_credentials
                    (id, organization_id, workspace_id, encrypted_client_id,
                     encrypted_client_secret, encrypted_access_token, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (organization_id, workspace_id) DO UPDATE SET
                    encrypted_client_id = EXCLUDED.encrypted_client_id,
                    encrypted_client_secret = EXCLUDED.encrypted_client_secret,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    self._protector.protect(client_id),
                    self._protector.protect(client_secret),
                    None,
                ),
            )
        status = self._get_status(workspace_id)
        if status is None:
            raise RuntimeError("Performance 凭据保存后无法读取状态")
        return status

    def _save_tokens(
        self, workspace_id: str, access_token: str, refresh_token: str | None,
        expires_at: str, client_id_present: bool,
    ) -> PerformanceCredentialStatus:
        """执行内部步骤 _save_tokens，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    access_token: 参数语义、输入边界和安全约束。
    refresh_token: 参数语义、输入边界和安全约束。
    expires_at: 参数语义、输入边界和安全约束。
    client_id_present: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
        inspect_performance_credentials(
            client_id="configured" if client_id_present else None,
            client_secret="stored",
            access_token=access_token, refresh_token=refresh_token, expires_at=expires_at,
        )
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        access_cipher = self._protector.protect(access_token)
        refresh_cipher = self._protector.protect(refresh_token) if refresh_token else None
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO performance_oauth_credentials
                    (id, organization_id, workspace_id, encrypted_access_token,
                     encrypted_refresh_token, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id, workspace_id) DO UPDATE SET
                    encrypted_access_token = EXCLUDED.encrypted_access_token,
                    encrypted_refresh_token = EXCLUDED.encrypted_refresh_token,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (str(uuid4()), self._context.organization_id, workspace_id,
                 access_cipher, refresh_cipher, expiry),
            )
        saved_status = self._get_status(workspace_id)
        if saved_status is None:
            raise RuntimeError("Performance 令牌保存后无法读取状态")
        return saved_status

    async def get_status(self, *, workspace_id: str) -> PerformanceCredentialStatus | None:
        """执行 get_status 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._get_status, workspace_id)

    async def get_client_credentials(self, *, workspace_id: str) -> tuple[str, str] | None:
        """执行 get_client_credentials 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._get_client_credentials, workspace_id)

    async def get_access_token(self, *, workspace_id: str) -> tuple[str, str] | None:
        """执行 get_access_token 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._get_access_token, workspace_id)

    def _get_client_credentials(self, workspace_id: str) -> tuple[str, str] | None:
        """执行内部步骤 _get_client_credentials，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                SELECT encrypted_client_id, encrypted_client_secret
                FROM performance_oauth_credentials
                WHERE organization_id = %s AND workspace_id = %s
                """,
                (self._context.organization_id, workspace_id),
            ).fetchone()
        if row is None or not row["encrypted_client_id"] or not row["encrypted_client_secret"]:
            return None
        return (
            self._protector.unprotect(
                row["encrypted_client_id"], credential_version=self._protector.key_version,
            ),
            self._protector.unprotect(
                row["encrypted_client_secret"], credential_version=self._protector.key_version,
            ),
        )

    def _get_access_token(self, workspace_id: str) -> tuple[str, str] | None:
        """读取解密后的令牌和过期时间，仅供后端外部 API 适配器使用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                SELECT encrypted_access_token, expires_at
                FROM performance_oauth_credentials
                WHERE organization_id = %s AND workspace_id = %s
                """,
                (self._context.organization_id, workspace_id),
            ).fetchone()
        if row is None or not row["encrypted_access_token"] or row["expires_at"] is None:
            return None
        return (
            self._protector.unprotect(
                row["encrypted_access_token"], credential_version=self._protector.key_version,
            ),
            row["expires_at"].isoformat(),
        )

    def _get_status(self, workspace_id: str) -> PerformanceCredentialStatus | None:
        """执行内部步骤 _get_status，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                SELECT expires_at, encrypted_client_id, encrypted_access_token,
                       encrypted_refresh_token, encrypted_client_secret
                FROM performance_oauth_credentials
                WHERE organization_id = %s AND workspace_id = %s
                """,
                (self._context.organization_id, workspace_id),
            ).fetchone()
        if row is None:
            return None
        return inspect_performance_credentials(
            client_id="stored" if row["encrypted_client_id"] else None,
            client_secret="stored" if row["encrypted_client_secret"] else None,
            access_token="stored" if row["encrypted_access_token"] else None,
            refresh_token="stored" if row["encrypted_refresh_token"] else None,
            expires_at=row["expires_at"].isoformat(),
        )
