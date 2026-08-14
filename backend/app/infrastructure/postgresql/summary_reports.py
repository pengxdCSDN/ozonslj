import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.summary_report import SummaryReport
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresSummaryReportGateway:
    """保存日报、周报、月报及站内待办快照；报告只提供建议。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_report(self, *, workspace_id: str, report: SummaryReport) -> SummaryReport:
        return await asyncio.to_thread(self._save, workspace_id, report)

    def _save(self, workspace_id: str, report: SummaryReport) -> SummaryReport:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO summary_reports
                    (id, organization_id, workspace_id, report_type, period, report)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    report.report_type, report.period,
                    json.dumps(asdict(report), ensure_ascii=False),
                ),
            )
        return report

    async def list_reports(self, *, workspace_id: str, limit: int) -> list[SummaryReport]:
        return await asyncio.to_thread(self._list_reports, workspace_id, limit)

    def _list_reports(self, workspace_id: str, limit: int) -> list[SummaryReport]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT report FROM summary_reports
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [SummaryReport(**row["report"]) for row in rows]
