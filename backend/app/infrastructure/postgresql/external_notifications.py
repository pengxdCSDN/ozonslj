"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from uuid import uuid4

from backend.app.domain.external_notification import ExternalNotificationConfig
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresExternalNotificationGateway:
    """保存通知渠道配置；默认预览，不调用真实 IM 或邮件发送器。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def save_config(
        self, *, workspace_id: str, config: ExternalNotificationConfig
    ) -> ExternalNotificationConfig:
        """执行 save_config 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    config: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, config)

    def _save(
        self, workspace_id: str, config: ExternalNotificationConfig
    ) -> ExternalNotificationConfig:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    config: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
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
        """执行 list_configs 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_configs, workspace_id, limit)

    def _list_configs(self, workspace_id: str, limit: int) -> list[ExternalNotificationConfig]:
        """执行内部步骤 _list_configs，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
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
