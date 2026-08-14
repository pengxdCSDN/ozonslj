import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.data_freshness import DataFreshnessDecision
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresDataFreshnessGateway:
    """保存数据新鲜度判定，供差异预览和受控执行前复核。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_decision(
        self, *, workspace_id: str, decision: DataFreshnessDecision
    ) -> DataFreshnessDecision:
        return await asyncio.to_thread(self._save, workspace_id, decision)

    def _save(
        self, workspace_id: str, decision: DataFreshnessDecision
    ) -> DataFreshnessDecision:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO data_freshness_checks
                    (id, organization_id, workspace_id, data_domain, decision)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    decision.data_domain,
                    json.dumps(asdict(decision), default=str, ensure_ascii=False),
                ),
            )
        return decision

    async def list_decisions(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[DataFreshnessDecision]:
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[DataFreshnessDecision]:
        # 新鲜度历史按组织和工作区隔离，JSONB 仅保存判定快照，不替代业务事实。
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT decision
                FROM data_freshness_checks
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [DataFreshnessDecision(**row["decision"]) for row in rows]
