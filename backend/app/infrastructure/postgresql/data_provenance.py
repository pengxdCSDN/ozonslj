import asyncio
from datetime import datetime
from uuid import uuid4

from backend.app.domain.data_provenance import DataProvenance
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresDataProvenanceGateway:
    """保存来源、观测时间和解释，保证分析结果可以回溯可信度边界。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save(self, *, workspace_id: str, provenance: DataProvenance) -> DataProvenance:
        return await asyncio.to_thread(self._save, workspace_id, provenance)

    def _save(self, workspace_id: str, provenance: DataProvenance) -> DataProvenance:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO data_provenance
                    (id, organization_id, workspace_id, source, observed_at, explanation)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (str(uuid4()), self._context.organization_id, workspace_id,
                 provenance.source, datetime.fromisoformat(
                     provenance.observed_at.replace("Z", "+00:00")
                 ), provenance.explanation),
            )
        return provenance

    async def list_history(self, *, workspace_id: str, limit: int = 50) -> list[DataProvenance]:
        return await asyncio.to_thread(self._list_history, workspace_id, limit)

    def _list_history(self, workspace_id: str, limit: int) -> list[DataProvenance]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT source, observed_at, explanation
                FROM data_provenance
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY observed_at DESC, created_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [DataProvenance(
            source=row["source"], observed_at=row["observed_at"].isoformat(),
            explanation=str(row["explanation"]),
        ) for row in rows]
