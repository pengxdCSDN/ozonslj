import asyncio
import json
from uuid import uuid4

from backend.app.domain.seller_order_sync import SellerOrderSyncPreview
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresSellerOrderSnapshotGateway:
    """保存已通过领域校验的 Seller 订单摘要快照，不保存买家个人信息。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_snapshot(
        self, *, workspace_id: str, preview: SellerOrderSyncPreview
    ) -> SellerOrderSyncPreview:
        return await asyncio.to_thread(self._save_snapshot, workspace_id, preview)

    def _save_snapshot(
        self, workspace_id: str, preview: SellerOrderSyncPreview
    ) -> SellerOrderSyncPreview:
        items = [
            {
                "order_id": item.order_id,
                "ordered_at": item.ordered_at,
                "status": item.status,
                "total_amount_minor": item.total_amount_minor,
                "currency": item.currency,
                "item_count": item.item_count,
                "source": item.source,
            }
            for item in preview.items
        ]
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO seller_order_sync_snapshots
                    (id, workspace_id, cursor, total, items, source)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                """,
                (
                    str(uuid4()), workspace_id, preview.next_cursor, preview.total,
                    json.dumps(items, ensure_ascii=False), preview.source,
                ),
            )
        return preview

    async def list_snapshots(
        self, *, workspace_id: str, limit: int = 20
    ) -> list[SellerOrderSyncPreview]:
        return await asyncio.to_thread(self._list_snapshots, workspace_id, limit)

    def _list_snapshots(self, workspace_id: str, limit: int) -> list[SellerOrderSyncPreview]:
        if limit < 1 or limit > 100:
            raise ValueError("订单快照历史条数必须在 1 到 100 之间")
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT cursor, total, source
                FROM seller_order_sync_snapshots
                WHERE workspace_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (workspace_id, limit),
            ).fetchall()
        return [SellerOrderSyncPreview(
            items=[], total=row["total"], next_cursor=row["cursor"], source=row["source"],
            credentials_required=True, dry_run=True,
        ) for row in rows]
