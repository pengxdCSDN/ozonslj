"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from decimal import Decimal
from uuid import uuid4

from backend.app.domain.public_snapshot import PublicSnapshot
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresPublicSnapshotGateway:
    """保存已规范化公开样本，不保存原始 HTML。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def save_snapshot(self, *, workspace_id: str, snapshot: PublicSnapshot) -> PublicSnapshot:
        """执行 save_snapshot 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    snapshot: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save_snapshot, workspace_id, snapshot)

    def _save_snapshot(self, workspace_id: str, snapshot: PublicSnapshot) -> PublicSnapshot:
        """执行内部步骤 _save_snapshot，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    snapshot: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO public_snapshots
                    (id, organization_id, workspace_id, url, sampled_at, title, price_minor,
                     currency, rating, review_count, image_url, attributes, sample_size, estimated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id, snapshot.url,
                    snapshot.sampled_at, snapshot.title, snapshot.price_minor, snapshot.currency,
                    snapshot.rating, snapshot.review_count, snapshot.image_url,
                    json.dumps(snapshot.attributes, ensure_ascii=False), snapshot.sample_size,
                    snapshot.estimated,
                ),
            )
        return snapshot

    async def list_snapshots(self, *, workspace_id: str, limit: int = 50) -> list[PublicSnapshot]:
        """执行 list_snapshots 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_snapshots, workspace_id, limit)

    def _list_snapshots(self, workspace_id: str, limit: int) -> list[PublicSnapshot]:
        # 只读取规范化公开字段，不读取或保存原始 HTML。
        """执行内部步骤 _list_snapshots，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT url, sampled_at, title, price_minor, currency, rating,
                       review_count, image_url, attributes, sample_size, estimated
                FROM public_snapshots
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY sampled_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [PublicSnapshot(
            url=str(row["url"]), sampled_at=row["sampled_at"], title=row["title"],
            price_minor=row["price_minor"], currency=row["currency"],
            rating=Decimal(str(row["rating"])) if row["rating"] is not None else None,
            review_count=row["review_count"], image_url=row["image_url"],
            attributes=dict(row["attributes"]), sample_size=int(row["sample_size"]),
            estimated=bool(row["estimated"]),
        ) for row in rows]
