import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.selection_decision_book import SelectionDecisionBook
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresSelectionDecisionBookGateway:
    """保存固定章节的商品立项决策书，不触发采购、上架或广告写入。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_book(
        self, *, workspace_id: str, book: SelectionDecisionBook
    ) -> SelectionDecisionBook:
        return await asyncio.to_thread(self._save, workspace_id, book)

    def _save(self, workspace_id: str, book: SelectionDecisionBook) -> SelectionDecisionBook:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO selection_decision_books
                    (id, organization_id, workspace_id, content, confirmation_status)
                VALUES (%s, %s, %s, %s::jsonb, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    json.dumps(asdict(book), ensure_ascii=False), book.confirmation_status,
                ),
            )
        return book

    async def list_books(
        self, *, workspace_id: str, limit: int
    ) -> list[SelectionDecisionBook]:
        return await asyncio.to_thread(self._list_books, workspace_id, limit)

    def _list_books(self, workspace_id: str, limit: int) -> list[SelectionDecisionBook]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT content FROM selection_decision_books
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [_book_from_content(row["content"]) for row in rows]


def _book_from_content(content: object) -> SelectionDecisionBook:
    if not isinstance(content, dict):
        raise RuntimeError("选品决策书内容结构无效")
    return SelectionDecisionBook(
        opportunity_summary=str(content["opportunity_summary"]),
        customer_scene=str(content["customer_scene"]),
        market_sample=str(content["market_sample"]),
        competitor_snapshots=tuple(str(value) for value in content["competitor_snapshots"]),
        profit_calculation=str(content["profit_calculation"]),
        risks=tuple(str(value) for value in content["risks"]),
        price_range=str(content["price_range"]),
        stock_recommendation=str(content["stock_recommendation"]),
        seed_keywords=tuple(str(value) for value in content["seed_keywords"]),
        data_sources=tuple(str(value) for value in content["data_sources"]),
        uncertainty=str(content["uncertainty"]),
        confirmation_status=str(content["confirmation_status"]),
    )
