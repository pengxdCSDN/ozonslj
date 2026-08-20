"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.listing_fabe import FabePoint, ListingFabeDraft
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresListingFabeGateway:
    """保存可编辑的 FABE 草稿；只产生内容建议，不触发 Ozon 写入。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。"""
        self._sessions = sessions
        self._context = context

    async def save_draft(
        self, *, workspace_id: str, product_scope: str, draft: ListingFabeDraft
    ) -> ListingFabeDraft:
        """执行 save_draft 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._save, workspace_id, product_scope, draft)

    def _save(
        self, workspace_id: str, product_scope: str, draft: ListingFabeDraft
    ) -> ListingFabeDraft:
        """执行内部步骤 _save，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO listing_fabe_drafts
                    (id, organization_id, workspace_id, product_scope, bullets,
                     long_description, image_copy_suggestions, missing_evidence, editable)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id, product_scope,
                    json.dumps([asdict(point) for point in draft.bullets], ensure_ascii=False),
                    draft.long_description,
                    json.dumps(draft.image_copy_suggestions, ensure_ascii=False),
                    json.dumps(draft.missing_evidence, ensure_ascii=False), draft.editable,
                ),
            )
        return draft

    async def list_drafts(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[ListingFabeDraft]:
        """执行 list_drafts 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[ListingFabeDraft]:
        # FABE 历史仅可在当前组织和工作区内读取，避免卖点内容跨工作区复用。
        """执行内部步骤 _list，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT bullets, long_description, image_copy_suggestions,
                       missing_evidence, editable
                FROM listing_fabe_drafts
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [ListingFabeDraft(
            bullets=tuple(FabePoint(**item) for item in row["bullets"]),
            long_description=str(row["long_description"]),
            image_copy_suggestions=tuple(row["image_copy_suggestions"]),
            missing_evidence=tuple(row["missing_evidence"]),
            editable=bool(row["editable"]),
        ) for row in rows]
