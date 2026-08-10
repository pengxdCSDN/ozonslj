import asyncio
from uuid import uuid4

from backend.app.domain.external_notification import ExternalNotificationConfig
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresExternalNotificationGateway:
    """保存通知渠道配置；默认预览，不调用真实 IM 或邮件发送器。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_config(
        self, *, workspace_id: str, config: ExternalNotificationConfig
    ) -> ExternalNotificationConfig:
        return await asyncio.to_thread(self._save, workspace_id, config)

    def _save(
        self, workspace_id: str, config: ExternalNotificationConfig
    ) -> ExternalNotificationConfig:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO external_notification_configs
                    (id, organization_id, workspace_id, channel, enabled, template,
                     retry_limit, sensitive_data_allowed, preview_only)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    config.channel, config.enabled, config.template, config.retry_limit,
                    config.sensitive_data_allowed, config.preview_only,
                ),
            )
        return config

    async def list_configs(
        self, *, workspace_id: str, limit: int
    ) -> list[ExternalNotificationConfig]:
        return await asyncio.to_thread(self._list_configs, workspace_id, limit)

    def _list_configs(self, workspace_id: str, limit: int) -> list[ExternalNotificationConfig]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT channel, enabled, template, retry_limit,
                    sensitive_data_allowed, preview_only FROM external_notification_configs
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [ExternalNotificationConfig(
            channel=str(row["channel"]), enabled=bool(row["enabled"]),
            template=str(row["template"]), retry_limit=int(row["retry_limit"]),
            sensitive_data_allowed=bool(row["sensitive_data_allowed"]),
            preview_only=bool(row["preview_only"]),
        ) for row in rows]
