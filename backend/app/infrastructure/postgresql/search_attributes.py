import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.search_attributes import SearchAttributesReport, SearchAttributeSuggestion
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresSearchAttributesGateway:
    """保存 Search Attributes 建议及覆盖报告，保持可编辑只读边界。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_report(
        self, *, workspace_id: str, product_scope: str, report: SearchAttributesReport
    ) -> SearchAttributesReport:
        return await asyncio.to_thread(self._save, workspace_id, product_scope, report)

    def _save(
        self, workspace_id: str, product_scope: str, report: SearchAttributesReport
    ) -> SearchAttributesReport:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO search_attributes_reports
                    (id, organization_id, workspace_id, product_scope, report, coverage_percent,
                     missing_required, editable)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id, product_scope,
                    json.dumps(asdict(report), ensure_ascii=False), report.coverage_percent,
                    json.dumps(report.missing_required, ensure_ascii=False), report.editable,
                ),
            )
        return report

    async def list_reports(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[SearchAttributesReport]:
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[SearchAttributesReport]:
        # 报告历史仅按当前组织和工作区读取，保证属性建议不会跨工作区串用。
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT report
                FROM search_attributes_reports
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [SearchAttributesReport(
            suggestions=tuple(
                SearchAttributeSuggestion(**item)
                for item in row["report"]["suggestions"]
            ),
            coverage_percent=float(row["report"]["coverage_percent"]),
            missing_required=tuple(row["report"]["missing_required"]),
            editable=bool(row["report"]["editable"]),
        ) for row in rows]
