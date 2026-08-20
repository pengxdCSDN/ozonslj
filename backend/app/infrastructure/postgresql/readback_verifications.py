"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from datetime import datetime
from uuid import uuid4

from backend.app.domain.readback_store import StoredReadbackVerification
from backend.app.domain.readback_verification import ReadbackField, ReadbackVerification
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresReadbackVerificationGateway:
    """保存回读逐字段结果，支持运营人员复核外部写入是否真正生效。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def save(
        self, *, workspace_id: str, verification: ReadbackVerification
    ) -> StoredReadbackVerification:
        """执行 save 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    verification: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, verification)

    def _save(
        self, workspace_id: str, verification: ReadbackVerification
    ) -> StoredReadbackVerification:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    verification: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
        verification_id = str(uuid4())
        payload = {
            "matched": verification.matched,
            "message": verification.message,
            "fields": [
                {"field": field.field, "expected": field.expected, "actual": field.actual,
                 "matched": field.matched}
                for field in verification.fields
            ],
        }
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """INSERT INTO readback_verifications
                    (id, organization_id, workspace_id, verification)
                    VALUES (%s, %s, %s, %s::jsonb)
                    RETURNING id, workspace_id, verification, created_at""",
                (verification_id, self._context.organization_id, workspace_id, json.dumps(payload)),
            ).fetchone()
        if row is None:
            raise RuntimeError("回读结果写入后未返回记录")
        return _stored_from_row(row)

    async def list_results(
        self, *, workspace_id: str, limit: int
    ) -> list[StoredReadbackVerification]:
        """执行 list_results 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_results, workspace_id, limit)

    def _list_results(self, workspace_id: str, limit: int) -> list[StoredReadbackVerification]:
        """执行内部步骤 _list_results，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT id, workspace_id, verification, created_at
                    FROM readback_verifications
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [_stored_from_row(row) for row in rows]


def _stored_from_row(row: dict[str, object]) -> StoredReadbackVerification:
    """执行内部步骤 _stored_from_row，供同一模块的公开流程复用。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
    payload = row["verification"]
    if not isinstance(payload, dict) or not isinstance(payload.get("fields"), list):
        raise RuntimeError("回读结果 JSON 结构无效")
    verification = ReadbackVerification(
        matched=bool(payload["matched"]),
        fields=[ReadbackField(**field) for field in payload["fields"] if isinstance(field, dict)],
        message=str(payload["message"]),
    )
    created_at = row["created_at"]
    if not isinstance(created_at, datetime):
        raise RuntimeError("回读结果时间字段无效")
    return StoredReadbackVerification(
        str(row["id"]), str(row["workspace_id"]), verification, created_at
    )
