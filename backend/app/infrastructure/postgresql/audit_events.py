"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from datetime import datetime
from uuid import uuid4

from backend.app.domain.audit_event import AuditEvent
from backend.app.domain.audit_event_store import StoredAuditEvent
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAuditEventGateway:
    """保存受控写入生命周期事件，详情仅允许脱敏业务数据。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions, self._context = sessions, context

    async def save(self, *, workspace_id: str, event: AuditEvent) -> StoredAuditEvent:
        """执行 save 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    event: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, event)

    def _save(self, workspace_id: str, event: AuditEvent) -> StoredAuditEvent:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    event: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
        event_id = str(uuid4())
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """INSERT INTO audit_events
                    (id, organization_id, workspace_id, event_type, subject_id, detail, occurred_at)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                    RETURNING id, workspace_id, event_type, subject_id, detail, occurred_at""",
                (event_id, self._context.organization_id, workspace_id, event.event_type,
                 event.subject_id, json.dumps(event.detail), event.occurred_at),
            ).fetchone()
        if row is None:
            raise RuntimeError("审计事件写入后未返回记录")
        return _from_row(row)

    async def list_events(self, *, workspace_id: str, limit: int) -> list[StoredAuditEvent]:
        """执行 list_events 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_events, workspace_id, limit)

    def _list_events(self, workspace_id: str, limit: int) -> list[StoredAuditEvent]:
        """执行内部步骤 _list_events，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT id, workspace_id, event_type, subject_id, detail, occurred_at
                    FROM audit_events WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY occurred_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [_from_row(row) for row in rows]


def _from_row(row: dict[str, object]) -> StoredAuditEvent:
    """执行内部步骤 _from_row，供同一模块的公开流程复用。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
    occurred_at = row["occurred_at"]
    if not isinstance(occurred_at, datetime) or not isinstance(row["detail"], dict):
        raise RuntimeError("审计记录结构无效")
    return StoredAuditEvent(str(row["id"]), str(row["workspace_id"]), AuditEvent(
        str(row["event_type"]), str(row["subject_id"]), row["detail"], occurred_at
    ))
