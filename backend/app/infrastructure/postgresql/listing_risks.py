import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.listing_risk import ListingRiskFinding, ListingRiskReport
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresListingRiskGateway:
    """保存风险检测报告和原文；系统只标记风险，不自动删除用户内容。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_report(
        self, *, workspace_id: str, product_scope: str, report: ListingRiskReport
    ) -> ListingRiskReport:
        return await asyncio.to_thread(self._save, workspace_id, product_scope, report)

    def _save(
        self, workspace_id: str, product_scope: str, report: ListingRiskReport
    ) -> ListingRiskReport:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO listing_risk_reports
                    (id, organization_id, workspace_id, product_scope, original_text,
                     findings, safe_to_review)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id, product_scope,
                    report.original_text,
                    json.dumps([asdict(item) for item in report.findings], ensure_ascii=False),
                    report.safe_to_review,
                ),
            )
        return report

    async def list_reports(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[ListingRiskReport]:
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[ListingRiskReport]:
        # 风险历史保留原文并限制在当前组织和工作区，供人工复核且不自动改文。
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT findings, original_text, safe_to_review
                FROM listing_risk_reports
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [ListingRiskReport(
            findings=tuple(ListingRiskFinding(**item) for item in row["findings"]),
            original_text=str(row["original_text"]),
            safe_to_review=bool(row["safe_to_review"]),
        ) for row in rows]
