"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from uuid import uuid4

from backend.app.domain.listing_keyword import ListingKeyword
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresListingKeywordGateway:
    """保存 Listing 关键词来源、语言、分层和适用商品范围。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。"""
        self._sessions = sessions
        self._context = context

    async def save_keyword(self, *, workspace_id: str, keyword: ListingKeyword) -> ListingKeyword:
        """执行 save_keyword 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._save, workspace_id, keyword)

    def _save(self, workspace_id: str, keyword: ListingKeyword) -> ListingKeyword:
        """执行内部步骤 _save，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO listing_keywords
                    (id, organization_id, workspace_id, keyword, source, observed_at,
                     language, layer, product_scope)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    keyword.keyword, keyword.source, keyword.observed_at, keyword.language,
                    keyword.layer, keyword.product_scope,
                ),
            )
        return keyword

    async def list_keywords(self, *, workspace_id: str, limit: int = 50) -> list[ListingKeyword]:
        """执行 list_keywords 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[ListingKeyword]:
        # 只按当前组织上下文查询，避免页面历史回看绕过租户边界。
        """执行内部步骤 _list，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT keyword, source, observed_at, language, layer, product_scope
                FROM listing_keywords
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY observed_at DESC, created_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [
            ListingKeyword(
                keyword=str(row["keyword"]), source=str(row["source"]),
                observed_at=row["observed_at"], language=str(row["language"]),
                layer=row["layer"], product_scope=str(row["product_scope"]),
            )
            for row in rows
        ]
