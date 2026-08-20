"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from uuid import uuid4

from backend.app.domain.listing_layering import LayeredKeyword
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresListingLayerGateway:
    """保存关键词分层结果、规则原因和人工确认状态。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def save_layers(
        self, *, workspace_id: str, layers: list[LayeredKeyword]
    ) -> list[LayeredKeyword]:
        """执行 save_layers 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    layers: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, layers)

    def _save(self, workspace_id: str, layers: list[LayeredKeyword]) -> list[LayeredKeyword]:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    layers: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            for item in layers:
                connection.execute(
                    """
                    INSERT INTO listing_keyword_layers
                        (id, organization_id, workspace_id, keyword, layer, reason,
                         manually_confirmed)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid4()), self._context.organization_id, workspace_id,
                        item.keyword, item.layer, item.reason, item.manually_confirmed,
                    ),
                )
        return layers

    async def list_layers(self, *, workspace_id: str, limit: int = 50) -> list[LayeredKeyword]:
        """执行 list_layers 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[LayeredKeyword]:
        # 历史查询必须同时约束组织和工作区，防止不同工作区的词层结果串读。
        """执行内部步骤 _list，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT keyword, layer, reason, manually_confirmed
                FROM listing_keyword_layers
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [
            LayeredKeyword(
                keyword=str(row["keyword"]), layer=row["layer"],
                reason=str(row["reason"]), manually_confirmed=bool(row["manually_confirmed"]),
            ) for row in rows
        ]
