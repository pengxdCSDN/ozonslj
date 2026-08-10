import asyncio
from typing import cast
from uuid import uuid4

from backend.app.domain.listing_publish import PublishCommand, PublishStatus
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresListingPublishGateway:
    """持久化受控发布命令、回读结果和审计状态；不直接连接真实写接口。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_command(
        self, *, workspace_id: str, product_scope: str, command: PublishCommand
    ) -> PublishCommand:
        return await asyncio.to_thread(self._save, workspace_id, product_scope, command)

    def _save(
        self, workspace_id: str, product_scope: str, command: PublishCommand
    ) -> PublishCommand:
        with self._sessions.transaction(self._context) as connection:
            # 幂等键代表一次不可替换的受控命令：同键同内容直接复用，
            # 同键不同内容必须拒绝，避免重试请求悄悄覆盖原始审核对象。
            existing = connection.execute(
                """SELECT version_no, status, requested_text, readback_text,
                    matched, message
                    FROM listing_publish_commands
                    WHERE organization_id=%s AND workspace_id=%s
                      AND product_scope=%s AND idempotency_key=%s""",
                (
                    self._context.organization_id,
                    workspace_id,
                    product_scope,
                    command.idempotency_key,
                ),
            ).fetchone()
            if existing is not None:
                same_command = (
                    int(existing["version_no"]) == command.version
                    and str(existing["requested_text"]) == command.requested_text
                )
                if not same_command:
                    raise ValueError("相同幂等键不能提交不同版本或不同内容")
                return PublishCommand(
                    command.idempotency_key,
                    int(existing["version_no"]),
                    cast(PublishStatus, existing["status"]),
                    str(existing["requested_text"]),
                    existing["readback_text"],
                    bool(existing["matched"]),
                    str(existing["message"]),
                )
            connection.execute(
                """
                INSERT INTO listing_publish_commands
                    (id, organization_id, workspace_id, product_scope, idempotency_key,
                     version_no, status, requested_text, readback_text, matched, message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id, product_scope,
                    command.idempotency_key, command.version, command.status,
                    command.requested_text, command.readback_text, command.matched, command.message,
                ),
            )
        return command

    async def list_commands(
        self, *, workspace_id: str, product_scope: str, limit: int
    ) -> list[PublishCommand]:
        return await asyncio.to_thread(self._list_commands, workspace_id, product_scope, limit)

    def _list_commands(
        self, workspace_id: str, product_scope: str, limit: int
    ) -> list[PublishCommand]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT idempotency_key, version_no, status, requested_text,
                    readback_text, matched, message FROM listing_publish_commands
                    WHERE organization_id=%s AND workspace_id=%s AND product_scope=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, product_scope, limit),
            ).fetchall()
        return [
            PublishCommand(
                idempotency_key=str(row["idempotency_key"]), version=int(row["version_no"]),
                status=cast(PublishStatus, row["status"]),
                requested_text=str(row["requested_text"]),
                readback_text=row["readback_text"], matched=bool(row["matched"]),
                message=str(row["message"]),
            )
            for row in rows
        ]
