import asyncio
from uuid import uuid4

from backend.app.domain.listing_layering import LayeredKeyword
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresListingLayerGateway:
    """保存关键词分层结果、规则原因和人工确认状态。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_layers(
        self, *, workspace_id: str, layers: list[LayeredKeyword]
    ) -> list[LayeredKeyword]:
        return await asyncio.to_thread(self._save, workspace_id, layers)

    def _save(self, workspace_id: str, layers: list[LayeredKeyword]) -> list[LayeredKeyword]:
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
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[LayeredKeyword]:
        # 历史查询必须同时约束组织和工作区，防止不同工作区的词层结果串读。
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
