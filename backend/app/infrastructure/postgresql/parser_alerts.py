import asyncio
from uuid import uuid4

from backend.app.domain.parser_alert import ParserChange
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresParserAlertGateway:
    """保存解析差异的字段级告警，不保存原始页面内容。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def create_alerts(
        self, *, workspace_id: str, url: str, changes: list[ParserChange]
    ) -> list[ParserChange]:
        return await asyncio.to_thread(self._create_alerts, workspace_id, url, changes)

    def _create_alerts(
        self, workspace_id: str, url: str, changes: list[ParserChange]
    ) -> list[ParserChange]:
        with self._sessions.transaction(self._context) as connection:
            for change in changes:
                connection.execute(
                    """
                    INSERT INTO parser_alerts
                        (id, organization_id, workspace_id, url, field_name, old_value,
                         new_value, severity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid4()), self._context.organization_id, workspace_id, url,
                        change.field_name, change.old_value, change.new_value, change.severity,
                    ),
                )
        return changes

    async def list_alerts(self, *, workspace_id: str, limit: int = 50) -> list[ParserChange]:
        return await asyncio.to_thread(self._list_alerts, workspace_id, limit)

    def _list_alerts(self, workspace_id: str, limit: int) -> list[ParserChange]:
        # 历史只返回字段级变化，不保存原始页面内容。
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT field_name, old_value, new_value, severity, message
                FROM parser_alerts
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [ParserChange(
            field_name=str(row["field_name"]), old_value=row["old_value"],
            new_value=row["new_value"], severity=row["severity"], message=str(row["message"]),
        ) for row in rows]
