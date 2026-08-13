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
                     model_kind, api_key, credential_ref, credential_suffix, priority, enabled)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, TRUE)
                """,
                (
                    values["provider_id"], self._context.organization_id, values["name"],
                    values["adapter_type"], values["model"], values["base_url"],
                    values["model_kind"],
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
                       credential_ref, credential_suffix, model_kind
                FROM rag_model_providers
                WHERE organization_id = %s
                ORDER BY model_kind, priority, id
                """,
                (self._context.organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    async def update_provider(self, **kwargs: object) -> None:
        await asyncio.to_thread(self._update_provider, kwargs)

    def _update_provider(self, values: dict[str, object]) -> None:
        with self._sessions.transaction(self._context) as connection:
            current = connection.execute(
                """
                SELECT model_kind
                FROM rag_model_providers
                WHERE id=%s AND organization_id=%s
                """,
                (values["provider_id"], self._context.organization_id),
            ).fetchone()
            if current is not None and str(current["model_kind"]) != str(values["model_kind"]):
                bound = connection.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM rag_model_purpose_bindings
                        WHERE organization_id=%s
                          AND (primary_provider_id=%s OR %s = ANY(fallback_provider_ids))
                    ) AS bound
                    """,
                    (self._context.organization_id, values["provider_id"], values["provider_id"]),
                ).fetchone()
                if bound and bool(bound["bound"]):
                    raise ValueError("provider_bound_kind")
            connection.execute(
                """
                UPDATE rag_model_providers
                SET name=%s, adapter_type=%s, model=%s, base_url=%s, model_kind=%s, priority=%s,
                    enabled=COALESCE(%s, enabled),
                    credential_ref=COALESCE(%s, credential_ref),
                    credential_suffix=COALESCE(%s, credential_suffix),
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND organization_id=%s
                """,
                (
                    values["name"], values["adapter_type"], values["model"], values["base_url"],
                    values["model_kind"], values["priority"], values.get("enabled"),
                    values.get("credential_ref"),
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

    async def delete_provider(self, provider_id: str) -> bool:
        return await asyncio.to_thread(self._delete_provider, provider_id)

    def _delete_provider(self, provider_id: str) -> bool:
        """删除未被用途绑定的配置；绑定中的配置必须先停用或解绑，避免运行时悬挂引用。"""
        with self._sessions.transaction(self._context) as connection:
            bound = connection.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM rag_model_purpose_bindings
                    WHERE organization_id=%s
                      AND (primary_provider_id=%s OR %s = ANY(fallback_provider_ids))
                ) AS bound
                """,
                (self._context.organization_id, provider_id, provider_id),
            ).fetchone()
            if bound and bool(bound["bound"]):
                raise ValueError("provider_bound")
            result = connection.execute(
                """
                DELETE FROM rag_model_providers
                WHERE id=%s AND organization_id=%s
                """,
                (provider_id, self._context.organization_id),
            )
            return result.rowcount > 0

    async def bind_purpose(
        self, *, purpose: str, primary_provider_id: str, fallback_provider_ids: Sequence[str]
    ) -> None:
        provider_ids = [primary_provider_id, *fallback_provider_ids]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("provider_duplicate")
        if primary_provider_id in fallback_provider_ids:
            raise ValueError("主模型不能同时出现在备用模型列表")
        await asyncio.to_thread(
            self._bind_purpose, purpose, provider_ids[0], provider_ids[1:]
        )

    def _bind_purpose(self, purpose: str, primary: str, fallbacks: list[str]) -> None:
        with self._sessions.transaction(self._context) as connection:
            provider_ids = [primary, *fallbacks]
            required_kind = "embedding" if purpose == "embedding" else "text"
            rows = connection.execute(
                """
                SELECT id, enabled, model_kind
                FROM rag_model_providers
                WHERE organization_id=%s AND id = ANY(%s)
                """,
                (self._context.organization_id, provider_ids),
            ).fetchall()
            if len(rows) != len(provider_ids):
                raise ValueError("provider_not_found")
            if any(not bool(row["enabled"]) for row in rows):
                raise ValueError("provider_disabled")
            if any(str(row["model_kind"]) != required_kind for row in rows):
                raise ValueError("provider_kind_mismatch")
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
