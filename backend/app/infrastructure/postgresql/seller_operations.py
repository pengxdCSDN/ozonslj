"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from datetime import datetime
from typing import Any

from backend.app.domain.seller_operation import (
    SellerOperationPage,
    SellerOperationSummary,
)
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresSellerOperationGateway:
    """读取 PostgreSQL 追加式审计中的固定脱敏字段。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。"""
        self._sessions = sessions
        self._context = context

    async def list_seller_operations(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> SellerOperationPage:
        """执行 list_seller_operations 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(
            self._list_seller_operations,
            workspace_id,
            int(cursor) if cursor is not None else 0,
            limit,
        )

    def _list_seller_operations(
        self,
        workspace_id: str,
        offset: int,
        limit: int,
    ) -> SellerOperationPage:
        # detail、operator_id 和 user_id 不进入查询白名单，防止泄露凭据或内部身份。
        """执行内部步骤 _list_seller_operations，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            count_row = connection.execute(
                """
                SELECT count(*) AS total
                FROM seller_operations
                WHERE organization_id = %s AND workspace_id = %s
                """,
                (self._context.organization_id, workspace_id),
            ).fetchone()
            rows = connection.execute(
                """
                SELECT id, operation_type, risk_level, target_type,
                       target_count, request_id, result, occurred_at
                FROM seller_operations
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY occurred_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                (self._context.organization_id, workspace_id, limit, offset),
            ).fetchall()

        total = int(count_row["total"]) if count_row is not None else 0
        items = [_seller_operation_from_row(row) for row in rows]
        end = offset + len(items)
        return SellerOperationPage(
            items=items,
            total=total,
            next_cursor=str(end) if end < total else None,
        )


def _seller_operation_from_row(row: dict[str, Any]) -> SellerOperationSummary:
    """将数据库约束后的审计行映射为固定白名单摘要。"""
    occurred_at = row["occurred_at"]
    if not isinstance(occurred_at, datetime):
        raise ValueError("审计 occurred_at 不是有效时间")
    return SellerOperationSummary(
        operation_id=str(row["id"]),
        operation_type=str(row["operation_type"]),
        risk_level=row["risk_level"],
        target_type=str(row["target_type"]) if row["target_type"] is not None else None,
        target_count=int(row["target_count"]),
        request_id=str(row["request_id"]) if row["request_id"] is not None else None,
        result=row["result"],
        occurred_at=occurred_at,
    )
