"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Any

from backend.app.domain.customer_order import CustomerOrder, CustomerOrderPage
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext

_MINOR_UNITS_PER_MAJOR = Decimal(100)
_MAJOR_UNIT_QUANTUM = Decimal("0.01")


class PostgresCustomerOrderGateway:
    """读取 PostgreSQL 中按内部组织和店铺工作区隔离的脱敏订单摘要。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def list_customer_orders(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> CustomerOrderPage:
        """执行 list_customer_orders 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    cursor: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(
            self._list_customer_orders,
            workspace_id,
            int(cursor) if cursor is not None else 0,
            limit,
        )

    def _list_customer_orders(
        self,
        workspace_id: str,
        offset: int,
        limit: int,
    ) -> CustomerOrderPage:
        # raw_summary 可能包含上游扩展字段，运营列表不得选择或返回该列。
        """执行内部步骤 _list_customer_orders，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    offset: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            count_row = connection.execute(
                """
                SELECT count(*) AS total
                FROM customer_orders
                WHERE organization_id = %s AND workspace_id = %s
                """,
                (self._context.organization_id, workspace_id),
            ).fetchone()
            rows = connection.execute(
                """
                SELECT id, ozon_order_id, status, total_amount_minor,
                       currency, ordered_at, synced_at
                FROM customer_orders
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY ordered_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                (self._context.organization_id, workspace_id, limit, offset),
            ).fetchall()

        total = int(count_row["total"]) if count_row is not None else 0
        items = [_customer_order_from_row(row) for row in rows]
        end = offset + len(items)
        return CustomerOrderPage(
            items=items,
            total=total,
            next_cursor=str(end) if end < total else None,
        )


def _customer_order_from_row(row: dict[str, Any]) -> CustomerOrder:
    """金额由最小货币单位精确转换，禁止使用浮点数。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return CustomerOrder(
        order_id=str(row["id"]),
        ozon_order_id=str(row["ozon_order_id"]),
        status=str(row["status"]),
        total_amount=(
            Decimal(int(row["total_amount_minor"])) / _MINOR_UNITS_PER_MAJOR
        ).quantize(_MAJOR_UNIT_QUANTUM),
        currency=str(row["currency"]),
        ordered_at=_required_datetime(row["ordered_at"], "ordered_at"),
        synced_at=_required_datetime(row["synced_at"], "synced_at"),
    )


def _required_datetime(value: object, field_name: str) -> datetime:
    """数据库时间字段异常时立即失败，避免生成时间线不可追溯的订单。

Args:
    value: 参数语义、输入边界和安全约束。
    field_name: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    if not isinstance(value, datetime):
        raise ValueError(f"订单字段 {field_name!r} 不是有效时间")
    return value
