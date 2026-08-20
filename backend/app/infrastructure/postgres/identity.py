"""说明本模块的职责、边界和主要协作对象。"""

from datetime import datetime
from typing import Any, cast

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.domain.identity import AuthenticatedUser, OperatorRole


class PostgresIdentityGateway:
    """说明 PostgresIdentityGateway 的职责、状态边界和对外协作关系。"""
    def __init__(self, pool: AsyncConnectionPool) -> None:
        """初始化对象依赖和运行时状态。"""
        self._pool = pool

    async def find_login_identity(self, email: str) -> tuple[AuthenticatedUser, str] | None:
        """执行 find_login_identity 的业务流程并返回该流程的结果。"""
        async with (
            self._pool.connection() as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            await cursor.execute(
                """SELECT id, email, display_name, role, password_hash
                   FROM operators
                   WHERE lower(email) = lower(%s) AND is_active
                     AND password_hash IS NOT NULL""",
                (email,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            user = await self._load_user(cursor, str(row["id"]), row)
            return user, str(row["password_hash"])

    async def create_session(
        self, operator_id: str, token_hash: str, expires_at: datetime
    ) -> None:
        """执行 create_session 的业务流程并返回该流程的结果。"""
        async with self._pool.connection() as connection:
            await connection.execute(
                """DELETE FROM user_sessions
                   WHERE expires_at <= now()
                      OR revoked_at < now() - interval '7 days'"""
            )
            await connection.execute(
                """INSERT INTO user_sessions (token_hash, operator_id, expires_at)
                   VALUES (%s, %s, %s)""",
                (token_hash, operator_id, expires_at),
            )

    async def find_user_by_session_hash(self, token_hash: str) -> AuthenticatedUser | None:
        """执行 find_user_by_session_hash 的业务流程并返回该流程的结果。"""
        async with (
            self._pool.connection() as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            await cursor.execute(
                """SELECT operators.id, operators.email, operators.display_name, operators.role
                   FROM user_sessions
                   JOIN operators ON operators.id = user_sessions.operator_id
                   WHERE user_sessions.token_hash = %s
                     AND user_sessions.revoked_at IS NULL
                     AND user_sessions.expires_at > now()
                     AND operators.is_active""",
                (token_hash,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            await cursor.execute(
                "UPDATE user_sessions SET last_seen_at = now() WHERE token_hash = %s",
                (token_hash,),
            )
            return await self._load_user(cursor, str(row["id"]), row)

    async def revoke_session(self, token_hash: str) -> None:
        """执行 revoke_session 的业务流程并返回该流程的结果。"""
        async with self._pool.connection() as connection:
            await connection.execute(
                """UPDATE user_sessions
                   SET revoked_at = COALESCE(revoked_at, now())
                   WHERE token_hash = %s""",
                (token_hash,),
            )

    @staticmethod
    async def _load_user(
        cursor: Any, operator_id: str, row: dict[str, object]
    ) -> AuthenticatedUser:
        """执行内部步骤 _load_user，供同一模块的公开流程复用。"""
        await cursor.execute(
            """SELECT workspace_id
               FROM workspace_memberships
               WHERE operator_id = %s
               ORDER BY workspace_id""",
            (operator_id,),
        )
        memberships = await cursor.fetchall()
        return AuthenticatedUser(
            id=operator_id,
            email=str(row["email"]),
            display_name=str(row["display_name"]),
            role=cast(OperatorRole, str(row["role"])),
            workspace_ids=tuple(str(item["workspace_id"]) for item in memberships),
        )
