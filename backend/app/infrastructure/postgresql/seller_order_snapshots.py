"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from uuid import uuid4

from backend.app.domain.seller_order_sync import SellerOrderSyncPreview
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresSellerOrderSnapshotGateway:
    """保存已通过领域校验的 Seller 订单摘要快照，不保存买家个人信息。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def save_snapshot(
        self, *, workspace_id: str, preview: SellerOrderSyncPreview
    ) -> SellerOrderSyncPreview:
        """执行 save_snapshot 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    preview: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save_snapshot, workspace_id, preview)

    def _save_snapshot(
        self, workspace_id: str, preview: SellerOrderSyncPreview
    ) -> SellerOrderSyncPreview:
        """执行内部步骤 _save_snapshot，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    preview: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
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
        """执行 list_snapshots 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_snapshots, workspace_id, limit)

    def _list_snapshots(self, workspace_id: str, limit: int) -> list[SellerOrderSyncPreview]:
        """执行内部步骤 _list_snapshots，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
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
