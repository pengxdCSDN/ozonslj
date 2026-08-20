"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from typing import Any

from backend.app.domain.stock_position import StockPosition, StockPositionPage
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresStockPositionGateway:
    """读取 PostgreSQL 中按内部组织和店铺工作区隔离的库存事实。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def list_stock_positions(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> StockPositionPage:
        """执行 list_stock_positions 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    cursor: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(
            self._list_stock_positions,
            workspace_id,
            int(cursor) if cursor is not None else 0,
            limit,
        )

    def _list_stock_positions(
        self,
        workspace_id: str,
        offset: int,
        limit: int,
    ) -> StockPositionPage:
        # SQL 显式限定内部组织与工作区，RLS 同时作为不可绕过的数据库隔离边界。
        """执行内部步骤 _list_stock_positions，供同一模块的公开流程复用。

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
                FROM stock_positions
                WHERE organization_id = %s AND workspace_id = %s
                """,
                (self._context.organization_id, workspace_id),
            ).fetchone()
            rows = connection.execute(
                """
                SELECT offer_id, warehouse_id, warehouse_name, fulfillment_type,
                       available_quantity, reserved_quantity, synced_at
                FROM stock_positions
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY offer_id, fulfillment_type, warehouse_id
                LIMIT %s OFFSET %s
                """,
                (self._context.organization_id, workspace_id, limit, offset),
            ).fetchall()

        total = int(count_row["total"]) if count_row is not None else 0
        items = [_stock_position_from_row(row) for row in rows]
        end = offset + len(items)
        return StockPositionPage(
            items=items,
            total=total,
            next_cursor=str(end) if end < total else None,
        )


def _stock_position_from_row(row: dict[str, Any]) -> StockPosition:
    """将已由数据库约束校验的库存行映射为只读领域模型。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return StockPosition(
        offer_id=str(row["offer_id"]),
        warehouse_id=str(row["warehouse_id"]),
        warehouse_name=(str(row["warehouse_name"]) if row["warehouse_name"] else None),
        fulfillment_type=row["fulfillment_type"],
        available_quantity=int(row["available_quantity"]),
        reserved_quantity=int(row["reserved_quantity"]),
        synced_at=row["synced_at"],
    )
