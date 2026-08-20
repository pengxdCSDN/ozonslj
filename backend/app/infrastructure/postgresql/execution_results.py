"""说明本模块的职责、边界和主要协作对象。"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from uuid import uuid4

from backend.app.domain.execution_result import BatchExecutionResult, ItemExecutionResult
from backend.app.domain.execution_result_store import StoredExecutionResult
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresExecutionResultGateway:
    """保存批量执行结果，避免前端刷新后丢失部分成功和失败证据。"""

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
        self, *, workspace_id: str, result: BatchExecutionResult
    ) -> StoredExecutionResult:
        """执行 save 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    result: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, result)

    def _save(self, workspace_id: str, result: BatchExecutionResult) -> StoredExecutionResult:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    result: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
        result_id = str(uuid4())
        payload = {
            "total": result.total,
            "succeeded": result.succeeded,
            "failed": result.failed,
            "status": result.status,
            "items": [
                {"item_id": item.item_id, "success": item.success, "message": item.message}
                for item in result.items
            ],
        }
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """INSERT INTO execution_results
                    (id, organization_id, workspace_id, result)
                    VALUES (%s, %s, %s, %s::jsonb)
                    RETURNING id, workspace_id, result, created_at""",
                (result_id, self._context.organization_id, workspace_id, json.dumps(payload)),
            ).fetchone()
        if row is None:
            raise RuntimeError("执行结果写入后未返回记录")
        return _stored_result_from_row(row)

    async def list_results(self, *, workspace_id: str, limit: int) -> list[StoredExecutionResult]:
        """执行 list_results 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[StoredExecutionResult]:
        """执行内部步骤 _list，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT id, workspace_id, result, created_at FROM execution_results
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [_stored_result_from_row(row) for row in rows]


def _stored_result_from_row(row: dict[str, object]) -> StoredExecutionResult:
    """执行内部步骤 _stored_result_from_row，供同一模块的公开流程复用。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
    payload = row["result"]
    if not isinstance(payload, dict):
        raise RuntimeError("执行结果 JSON 结构无效")
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise RuntimeError("执行结果缺少逐项结果")
    result = BatchExecutionResult(
        total=int(payload["total"]), succeeded=int(payload["succeeded"]),
        failed=int(payload["failed"]), status=str(payload["status"]),
        items=[ItemExecutionResult(**item) for item in raw_items if isinstance(item, dict)],
    )
    created_at = row["created_at"]
    if not isinstance(created_at, datetime):
        raise RuntimeError("执行结果时间字段无效")
    return StoredExecutionResult(str(row["id"]), str(row["workspace_id"]), result, created_at)
