import asyncio
import json
from uuid import uuid4

from backend.app.domain.listing_title_draft import ListingTitleDraft
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresListingTitleDraftGateway:
    """保存可编辑标题草稿和关键词覆盖报告，不执行外部发布。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_draft(
        self, *, workspace_id: str, product_scope: str, draft: ListingTitleDraft
    ) -> ListingTitleDraft:
        return await asyncio.to_thread(self._save, workspace_id, product_scope, draft)

    def _save(
        self, workspace_id: str, product_scope: str, draft: ListingTitleDraft
    ) -> ListingTitleDraft:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO listing_title_drafts
                    (id, organization_id, workspace_id, product_scope, title, category,
                     covered_terms, missing_terms, character_count, risks, editable)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id, product_scope,
                    draft.title, draft.category,
                    json.dumps(draft.covered_terms, ensure_ascii=False),
                    json.dumps(draft.missing_terms, ensure_ascii=False), draft.character_count,
                    json.dumps(draft.risks, ensure_ascii=False), draft.editable,
                ),
            )
        return draft

    async def list_drafts(self, *, workspace_id: str, limit: int = 50) -> list[ListingTitleDraft]:
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[ListingTitleDraft]:
        # 标题草稿历史只读当前组织和工作区，便于人工复核且不触发发布。
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT title, category, covered_terms, missing_terms, character_count,
                       risks, editable
                FROM listing_title_drafts
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [ListingTitleDraft(
            title=str(row["title"]), category=str(row["category"]),
            covered_terms=tuple(row["covered_terms"]), missing_terms=tuple(row["missing_terms"]),
            character_count=int(row["character_count"]), risks=tuple(row["risks"]),
            editable=bool(row["editable"]),
        ) for row in rows]
