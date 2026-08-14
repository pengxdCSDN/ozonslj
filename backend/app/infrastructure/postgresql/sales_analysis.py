import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.sales_analysis import SalesAnalysis
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresSalesAnalysisGateway:
    """保存销售分析快照；分析只读，不改变业务事实。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_report(self, *, workspace_id: str, report: SalesAnalysis) -> SalesAnalysis:
        return await asyncio.to_thread(self._save, workspace_id, report)

    def _save(self, workspace_id: str, report: SalesAnalysis) -> SalesAnalysis:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO sales_analysis_reports
                    (id, organization_id, workspace_id, report)
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    json.dumps(asdict(report), ensure_ascii=False),
                ),
            )
        return report

    async def list_reports(self, *, workspace_id: str, limit: int) -> list[SalesAnalysis]:
        return await asyncio.to_thread(self._list_reports, workspace_id, limit)

    def _list_reports(self, workspace_id: str, limit: int) -> list[SalesAnalysis]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT report FROM sales_analysis_reports
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [SalesAnalysis(**row["report"]) for row in rows]
