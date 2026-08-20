"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from datetime import datetime
from uuid import uuid4

from backend.app.domain.data_provenance import DataProvenance
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresDataProvenanceGateway:
    """保存来源、观测时间和解释，保证分析结果可以回溯可信度边界。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。"""
        self._sessions = sessions
        self._context = context

    async def save(self, *, workspace_id: str, provenance: DataProvenance) -> DataProvenance:
        """执行 save 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._save, workspace_id, provenance)

    def _save(self, workspace_id: str, provenance: DataProvenance) -> DataProvenance:
        """执行内部步骤 _save，供同一模块的公开流程复用。"""
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
        """执行 list_history 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._list_history, workspace_id, limit)

    def _list_history(self, workspace_id: str, limit: int) -> list[DataProvenance]:
        """执行内部步骤 _list_history，供同一模块的公开流程复用。"""
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
