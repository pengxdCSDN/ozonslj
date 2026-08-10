import asyncio
from uuid import uuid4

from backend.app.domain.agent_trigger import AgentTrigger
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAgentTriggerGateway:
    """保存 Agent 定时、事件和手动触发配置；触发目标仍受只读边界约束。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_trigger(self, *, workspace_id: str, trigger: AgentTrigger) -> AgentTrigger:
        return await asyncio.to_thread(self._save, workspace_id, trigger)

    def _save(self, workspace_id: str, trigger: AgentTrigger) -> AgentTrigger:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO agent_triggers
                    (id, organization_id, workspace_id, trigger_type, target,
                     schedule, event_name, enabled, read_only)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    trigger.trigger_type, trigger.target, trigger.schedule,
                    trigger.event_name, trigger.enabled, trigger.read_only,
                ),
            )
        return trigger

    async def list_triggers(self, *, workspace_id: str, limit: int) -> list[AgentTrigger]:
        return await asyncio.to_thread(self._list_triggers, workspace_id, limit)

    def _list_triggers(self, workspace_id: str, limit: int) -> list[AgentTrigger]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT trigger_type, target, schedule, event_name, enabled, read_only
                    FROM agent_triggers WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [AgentTrigger(
            trigger_type=str(row["trigger_type"]), target=str(row["target"]),
            schedule=row["schedule"], event_name=row["event_name"],
            enabled=bool(row["enabled"]), read_only=bool(row["read_only"]),
        ) for row in rows]
