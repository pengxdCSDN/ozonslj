"""RAG 模型供应商配置的 PostgreSQL 适配器。

该适配器只持久化非敏感模型配置、凭据引用和末尾掩码；API Key 本体由
``ModelCredentialStore`` 写入应用专用 Secret 卷，避免数据库备份意外携带密钥。
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresRagModelProviderGateway:
    """按组织隔离供应商配置，并维护用途级主备绑定。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def create_provider(self, **kwargs: object) -> None:
        await asyncio.to_thread(self._create_provider, kwargs)

    def _create_provider(self, values: dict[str, object]) -> None:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO rag_model_providers
                    (id, organization_id, name, adapter_type, model, base_url,
                     api_key, credential_ref, credential_suffix, priority, enabled)
                VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, TRUE)
                """,
                (
                    values["provider_id"], self._context.organization_id, values["name"],
                    values["adapter_type"], values["model"], values["base_url"],
                    values["credential_ref"], values["credential_suffix"], values["priority"],
                ),
            )

    async def list_provider_metadata(self) -> list[dict[str, object]]:
        return await asyncio.to_thread(self._list_provider_metadata)

    def _list_provider_metadata(self) -> list[dict[str, object]]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT id, name, adapter_type, model, base_url, priority, enabled,
                       credential_ref, credential_suffix
                FROM rag_model_providers
                WHERE organization_id = %s
                ORDER BY priority, id
                """,
                (self._context.organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    async def update_provider(self, **kwargs: object) -> None:
        await asyncio.to_thread(self._update_provider, kwargs)

    def _update_provider(self, values: dict[str, object]) -> None:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                UPDATE rag_model_providers
                SET name=%s, adapter_type=%s, model=%s, base_url=%s, priority=%s,
                    credential_ref=COALESCE(%s, credential_ref),
                    credential_suffix=COALESCE(%s, credential_suffix),
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND organization_id=%s
                """,
                (
                    values["name"], values["adapter_type"], values["model"], values["base_url"],
                    values["priority"], values.get("credential_ref"),
                    values.get("credential_suffix"),
                    values["provider_id"], self._context.organization_id,
                ),
            )

    async def disable_provider(self, provider_id: str) -> None:
        await asyncio.to_thread(self._disable_provider, provider_id)

    def _disable_provider(self, provider_id: str) -> None:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                UPDATE rag_model_providers SET enabled=FALSE, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND organization_id=%s
                """,
                (provider_id, self._context.organization_id),
            )

    async def bind_purpose(
        self, *, purpose: str, primary_provider_id: str, fallback_provider_ids: Sequence[str]
    ) -> None:
        if primary_provider_id in fallback_provider_ids:
            raise ValueError("主模型不能同时出现在备用模型列表")
        await asyncio.to_thread(
            self._bind_purpose, purpose, primary_provider_id, list(fallback_provider_ids)
        )

    def _bind_purpose(self, purpose: str, primary: str, fallbacks: list[str]) -> None:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO rag_model_purpose_bindings
                    (organization_id, purpose, primary_provider_id, fallback_provider_ids)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (organization_id, purpose) DO UPDATE SET
                    primary_provider_id=EXCLUDED.primary_provider_id,
                    fallback_provider_ids=EXCLUDED.fallback_provider_ids,
                    revision=rag_model_purpose_bindings.revision+1,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (self._context.organization_id, purpose, primary, fallbacks),
            )

    async def list_bindings(self) -> list[dict[str, object]]:
        return await asyncio.to_thread(self._list_bindings)

    def _list_bindings(self) -> list[dict[str, object]]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT purpose, primary_provider_id, fallback_provider_ids, revision, updated_at
                FROM rag_model_purpose_bindings
                WHERE organization_id=%s
                ORDER BY purpose
                """,
                (self._context.organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]
