import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.agent_permissions import AgentPermissionDecision
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAgentPermissionGateway:
    """保存 Agent 权限判定；权限硬编码为只读，不接受提示词覆盖。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_decision(
        self, *, workspace_id: str, decision: AgentPermissionDecision
    ) -> AgentPermissionDecision:
        return await asyncio.to_thread(self._save, workspace_id, decision)

    def _save(
        self, workspace_id: str, decision: AgentPermissionDecision
    ) -> AgentPermissionDecision:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO agent_permission_checks
                    (id, organization_id, workspace_id, agent, decision)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    decision.agent, json.dumps(asdict(decision), ensure_ascii=False),
                ),
            )
        return decision

    async def list_decisions(
        self, *, workspace_id: str, limit: int
    ) -> list[AgentPermissionDecision]:
        return await asyncio.to_thread(self._list_decisions, workspace_id, limit)

    def _list_decisions(self, workspace_id: str, limit: int) -> list[AgentPermissionDecision]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT decision FROM agent_permission_checks
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [AgentPermissionDecision(**row["decision"]) for row in rows]
