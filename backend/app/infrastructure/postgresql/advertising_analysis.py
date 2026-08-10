import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.advertising_analysis import AdvertisingAnalysis
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAdvertisingAnalysisGateway:
    """保存广告分析快照；预算、出价和否定词仍由独立审核链路控制。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_report(
        self, *, workspace_id: str, report: AdvertisingAnalysis
    ) -> AdvertisingAnalysis:
        return await asyncio.to_thread(self._save, workspace_id, report)

    def _save(self, workspace_id: str, report: AdvertisingAnalysis) -> AdvertisingAnalysis:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO advertising_analysis_reports
                    (id, organization_id, workspace_id, report)
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    json.dumps(asdict(report), ensure_ascii=False),
                ),
            )
        return report

    async def list_reports(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingAnalysis]:
        return await asyncio.to_thread(self._list_reports, workspace_id, limit)

    def _list_reports(self, workspace_id: str, limit: int) -> list[AdvertisingAnalysis]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT report FROM advertising_analysis_reports
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [AdvertisingAnalysis(**row["report"]) for row in rows]
