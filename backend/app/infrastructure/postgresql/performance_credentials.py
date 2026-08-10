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
        self._sessions = sessions
        self._context = context
        self._protector = protector

    async def save_tokens(
        self, *, workspace_id: str, access_token: str, refresh_token: str | None,
        expires_at: str, client_id_present: bool,
    ) -> PerformanceCredentialStatus:
        return await asyncio.to_thread(
            self._save_tokens, workspace_id, access_token, refresh_token, expires_at,
            client_id_present,
        )

    def _save_tokens(
        self, workspace_id: str, access_token: str, refresh_token: str | None,
        expires_at: str, client_id_present: bool,
    ) -> PerformanceCredentialStatus:
        status = inspect_performance_credentials(
            client_id="configured" if client_id_present else None,
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
        return status

    async def get_status(self, *, workspace_id: str) -> PerformanceCredentialStatus | None:
        return await asyncio.to_thread(self._get_status, workspace_id)

    def _get_status(self, workspace_id: str) -> PerformanceCredentialStatus | None:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                SELECT expires_at, encrypted_access_token, encrypted_refresh_token
                FROM performance_oauth_credentials
                WHERE organization_id = %s AND workspace_id = %s
                """,
                (self._context.organization_id, workspace_id),
            ).fetchone()
        if row is None:
            return None
        return inspect_performance_credentials(
            client_id="configured", access_token="stored",
            refresh_token="stored" if row["encrypted_refresh_token"] else None,
            expires_at=row["expires_at"].isoformat(),
        )
