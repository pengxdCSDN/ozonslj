"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from uuid import uuid4

from backend.app.domain.model_adapter import ModelAdapterConfig
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresModelAdapterGateway:
    """保存模型适配器元配置；不保存 API Key，也不发起模型请求。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。"""
        self._sessions = sessions
        self._context = context

    async def save_config(
        self, *, workspace_id: str, config: ModelAdapterConfig
    ) -> ModelAdapterConfig:
        """执行 save_config 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._save, workspace_id, config)

    def _save(self, workspace_id: str, config: ModelAdapterConfig) -> ModelAdapterConfig:
        """执行内部步骤 _save，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO model_adapter_configs
                    (id, organization_id, workspace_id, adapter, provider, model,
                     base_url, enabled, credential_configured)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    config.adapter, config.provider, config.model, config.base_url,
                    config.enabled, config.credential_configured,
                ),
            )
        return config

    async def list_configs(
        self, *, workspace_id: str, limit: int
    ) -> list[ModelAdapterConfig]:
        """执行 list_configs 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._list_configs, workspace_id, limit)

    async def get_active_config(self, *, workspace_id: str) -> ModelAdapterConfig | None:
        """执行 get_active_config 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._get_active_config, workspace_id)

    def _get_active_config(self, workspace_id: str) -> ModelAdapterConfig | None:
        """执行内部步骤 _get_active_config，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """SELECT adapter, provider, model, base_url, enabled,
                    credential_configured FROM model_adapter_configs
                    WHERE organization_id=%s AND workspace_id=%s AND enabled=true
                    ORDER BY created_at DESC, id DESC LIMIT 1""",
                (self._context.organization_id, workspace_id),
            ).fetchone()
        if row is None:
            return None
        return ModelAdapterConfig(
            adapter=str(row["adapter"]), provider=str(row["provider"]),
            model=str(row["model"]), base_url=row["base_url"],
            enabled=True, credential_configured=bool(row["credential_configured"]),
        )

    def _list_configs(self, workspace_id: str, limit: int) -> list[ModelAdapterConfig]:
        """执行内部步骤 _list_configs，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT adapter, provider, model, base_url, enabled,
                    credential_configured FROM model_adapter_configs
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [ModelAdapterConfig(
            adapter=str(row["adapter"]), provider=str(row["provider"]),
            model=str(row["model"]), base_url=row["base_url"],
            enabled=bool(row["enabled"]), credential_configured=bool(row["credential_configured"]),
        ) for row in rows]
