import asyncio
import json
from uuid import uuid4

from backend.app.domain.readonly_tool import ReadonlyToolDecision
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresReadonlyToolGateway:
    """记录只读工具授权结果，便于审计参数过滤和 SQL/写入阻断。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_decision(
        self, *, workspace_id: str, decision: ReadonlyToolDecision
    ) -> ReadonlyToolDecision:
        return await asyncio.to_thread(self._save, workspace_id, decision)

    def _save(
        self, workspace_id: str, decision: ReadonlyToolDecision
    ) -> ReadonlyToolDecision:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO readonly_tool_authorizations
                    (id, organization_id, workspace_id, tool, allowed, parameters,
                     reason, sql_allowed)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    decision.tool, decision.allowed, json.dumps(decision.parameters),
                    decision.reason, decision.sql_allowed,
                ),
            )
        return decision

    async def list_decisions(
        self, *, workspace_id: str, limit: int
    ) -> list[ReadonlyToolDecision]:
        return await asyncio.to_thread(self._list_decisions, workspace_id, limit)

    def _list_decisions(self, workspace_id: str, limit: int) -> list[ReadonlyToolDecision]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT tool, allowed, parameters, reason, sql_allowed
                    FROM readonly_tool_authorizations
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [ReadonlyToolDecision(
            tool=str(row["tool"]), allowed=bool(row["allowed"]),
            parameters={str(key): str(value) for key, value in row["parameters"].items()},
            reason=str(row["reason"]), sql_allowed=bool(row["sql_allowed"]),
        ) for row in rows]
