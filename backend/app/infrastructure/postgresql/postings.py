import asyncio
from datetime import date, datetime
from typing import Any

from backend.app.domain.posting import PostingPage, PostingSummary
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresPostingGateway:
    """读取 PostgreSQL 中按内部组织和工作区隔离的履约摘要。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def list_postings(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> PostingPage:
        return await asyncio.to_thread(
            self._list_postings,
            workspace_id,
            int(cursor) if cursor is not None else 0,
            limit,
        )

    def _list_postings(self, workspace_id: str, offset: int, limit: int) -> PostingPage:
        # tracking_number 和商品明细不属于列表摘要，SQL 不选择这些字段。
        with self._sessions.transaction(self._context) as connection:
            count_row = connection.execute(
                """
                SELECT count(*) AS total
                FROM postings
                WHERE organization_id = %s AND workspace_id = %s
                """,
                (self._context.organization_id, workspace_id),
            ).fetchone()
            rows = connection.execute(
                """
                SELECT posting.id, posting.customer_order_id,
                       posting.ozon_posting_number, posting.fulfillment_type,
                       posting.status, posting.shipment_date, posting.synced_at,
                       count(item.id) AS item_count,
                       COALESCE(sum(item.quantity), 0) AS total_quantity
                FROM postings AS posting
                LEFT JOIN posting_items AS item
                  ON item.organization_id = posting.organization_id
                 AND item.workspace_id = posting.workspace_id
                 AND item.posting_id = posting.id
                WHERE posting.organization_id = %s AND posting.workspace_id = %s
                GROUP BY posting.id, posting.customer_order_id,
                         posting.ozon_posting_number, posting.fulfillment_type,
                         posting.status, posting.shipment_date, posting.synced_at
                ORDER BY posting.shipment_date DESC NULLS LAST, posting.id DESC
                LIMIT %s OFFSET %s
                """,
                (self._context.organization_id, workspace_id, limit, offset),
            ).fetchall()

        total = int(count_row["total"]) if count_row is not None else 0
        items = [_posting_from_row(row) for row in rows]
        end = offset + len(items)
        return PostingPage(
            items=items,
            total=total,
            next_cursor=str(end) if end < total else None,
        )


def _posting_from_row(row: dict[str, Any]) -> PostingSummary:
    """将数据库聚合结果映射为不含追踪号和商品详情的履约摘要。"""
    return PostingSummary(
        posting_id=str(row["id"]),
        customer_order_id=(
            str(row["customer_order_id"]) if row["customer_order_id"] is not None else None
        ),
        ozon_posting_number=str(row["ozon_posting_number"]),
        fulfillment_type=row["fulfillment_type"],
        status=str(row["status"]),
        shipment_date=_optional_date(row["shipment_date"]),
        item_count=int(row["item_count"]),
        total_quantity=int(row["total_quantity"]),
        synced_at=_required_datetime(row["synced_at"]),
    )


def _optional_date(value: object) -> date | None:
    if value is None:
        return None
    if not isinstance(value, date):
        raise ValueError("履约单 shipment_date 不是有效日期")
    return value


def _required_datetime(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError("履约单 synced_at 不是有效时间")
    return value
