"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from datetime import datetime
from typing import Any

from backend.app.domain.identity import AuthenticatedUser, IdentityGateway
from backend.app.infrastructure.postgresql.session import (
    PostgresSessionFactory,
    TenantContext,
)


class PostgresIdentityGateway(IdentityGateway):
    """保存服务端会话，并在读取组织成员前建立数据库 RLS 上下文。"""

    def __init__(self, sessions: PostgresSessionFactory) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions

    async def find_login_identity(
        self,
        email: str,
        organization_id: str,
    ) -> tuple[AuthenticatedUser, str] | None:
        """执行 find_login_identity 的业务流程并返回该流程的结果。

Args:
    email: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(
            self._find_login_identity,
            email,
            organization_id,
        )

    async def create_session(
        self,
        user_id: str,
        organization_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """执行 create_session 的业务流程并返回该流程的结果。

Args:
    user_id: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    token_hash: 参数语义、输入边界和安全约束。
    expires_at: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await asyncio.to_thread(
            self._create_session,
            user_id,
            organization_id,
            token_hash,
            expires_at,
        )

    async def find_user_by_session_hash(
        self,
        token_hash: str,
    ) -> AuthenticatedUser | None:
        """执行 find_user_by_session_hash 的业务流程并返回该流程的结果。

Args:
    token_hash: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._find_user_by_session_hash, token_hash)

    async def revoke_session(self, token_hash: str) -> None:
        """执行 revoke_session 的业务流程并返回该流程的结果。

Args:
    token_hash: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await asyncio.to_thread(self._revoke_session, token_hash)

    def _find_login_identity(
        self,
        email: str,
        organization_id: str,
    ) -> tuple[AuthenticatedUser, str] | None:
        """执行内部步骤 _find_login_identity，供同一模块的公开流程复用。

Args:
    email: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.authentication_transaction() as connection:
            user_row = connection.execute(
                """
                SELECT id, email, display_name, password_hash
                FROM users
                WHERE email = %s AND status = 'active'
                """,
                (email,),
            ).fetchone()
            if user_row is None:
                return None
            _set_tenant_context(connection, organization_id, str(user_row["id"]))
            member_row = connection.execute(
                """
                SELECT member.role
                FROM organization_members AS member
                JOIN organizations AS organization
                  ON organization.id = member.organization_id
                WHERE member.organization_id = %s
                  AND member.user_id = %s
                  AND member.status = 'active'
                  AND organization.status = 'active'
                """,
                (organization_id, user_row["id"]),
            ).fetchone()
            if member_row is None:
                return None
            return (
                _authenticated_user(user_row, member_row, organization_id),
                str(user_row["password_hash"]),
            )

    def _create_session(
        self,
        user_id: str,
        organization_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """执行内部步骤 _create_session，供同一模块的公开流程复用。

Args:
    user_id: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    token_hash: 参数语义、输入边界和安全约束。
    expires_at: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(
            TenantContext(organization_id=organization_id, user_id=user_id)
        ) as connection:
            connection.execute(
                "DELETE FROM user_sessions WHERE expires_at <= CURRENT_TIMESTAMP",
            )
            connection.execute(
                """
                INSERT INTO user_sessions (
                    token_hash, user_id, active_organization_id, expires_at
                ) VALUES (%s, %s, %s, %s)
                """,
                (token_hash, user_id, organization_id, expires_at),
            )

    def _find_user_by_session_hash(self, token_hash: str) -> AuthenticatedUser | None:
        """执行内部步骤 _find_user_by_session_hash，供同一模块的公开流程复用。

Args:
    token_hash: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.authentication_transaction() as connection:
            session_row = connection.execute(
                """
                SELECT session.user_id, session.active_organization_id,
                       user_account.email, user_account.display_name
                FROM user_sessions AS session
                JOIN users AS user_account ON user_account.id = session.user_id
                WHERE session.token_hash = %s
                  AND session.revoked_at IS NULL
                  AND session.expires_at > CURRENT_TIMESTAMP
                  AND user_account.status = 'active'
                """,
                (token_hash,),
            ).fetchone()
            if session_row is None:
                return None
            organization_id = str(session_row["active_organization_id"])
            user_id = str(session_row["user_id"])
            _set_tenant_context(connection, organization_id, user_id)
            member_row = connection.execute(
                """
                SELECT member.role
                FROM organization_members AS member
                JOIN organizations AS organization
                  ON organization.id = member.organization_id
                WHERE member.organization_id = %s
                  AND member.user_id = %s
                  AND member.status = 'active'
                  AND organization.status = 'active'
                """,
                (organization_id, user_id),
            ).fetchone()
            if member_row is None:
                return None
            connection.execute(
                "UPDATE user_sessions SET last_seen_at = CURRENT_TIMESTAMP WHERE token_hash = %s",
                (token_hash,),
            )
            return _authenticated_user(session_row, member_row, organization_id)

    def _revoke_session(self, token_hash: str) -> None:
        """执行内部步骤 _revoke_session，供同一模块的公开流程复用。

Args:
    token_hash: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.authentication_transaction() as connection:
            connection.execute(
                """
                UPDATE user_sessions
                SET revoked_at = COALESCE(revoked_at, CURRENT_TIMESTAMP)
                WHERE token_hash = %s
                """,
                (token_hash,),
            )


def _set_tenant_context(connection: Any, organization_id: str, user_id: str) -> None:
    """在认证事务内补齐 RLS 上下文；值始终参数化且仅在当前事务有效。

Args:
    connection: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    user_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    connection.execute(
        """
        SELECT set_config('app.organization_id', %s, true),
               set_config('app.user_id', %s, true)
        """,
        (organization_id, user_id),
    )


def _authenticated_user(
    user_row: dict[str, Any],
    member_row: dict[str, Any],
    organization_id: str,
) -> AuthenticatedUser:
    """执行内部步骤 _authenticated_user，供同一模块的公开流程复用。

Args:
    user_row: 参数语义、输入边界和安全约束。
    member_row: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return AuthenticatedUser(
        id=str(user_row.get("id", user_row.get("user_id"))),
        email=str(user_row["email"]),
        display_name=str(user_row["display_name"]),
        organization_id=organization_id,
        organization_role=member_row["role"],
    )
