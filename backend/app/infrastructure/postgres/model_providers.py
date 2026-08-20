"""模型供应商配置 PostgreSQL 适配器；API Key 不参与返回模型。"""

from __future__ import annotations

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


class PostgresModelProviderGateway:
    """持久化供应商配置和用途主备绑定，调用方必须自行施加管理员权限。"""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        """初始化对象依赖和运行时状态。

Args:
    pool: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._pool = pool

    async def create_provider(
        self, *, provider_id: str, organization_id: str, name: str,
        adapter_type: str, model: str, api_key: str, priority: int,
        base_url: str | None = None,
    ) -> None:
        """执行 create_provider 的业务流程并返回该流程的结果。

Args:
    provider_id: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    name: 参数语义、输入边界和安全约束。
    adapter_type: 参数语义、输入边界和安全约束。
    model: 参数语义、输入边界和安全约束。
    api_key: 参数语义、输入边界和安全约束。
    priority: 参数语义、输入边界和安全约束。
    base_url: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        async with self._pool.connection() as connection, connection.transaction():
            await connection.execute(
                """
                INSERT INTO rag_model_providers
                    (id, organization_id, name, adapter_type, model, api_key, priority, base_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    provider_id, organization_id, name, adapter_type, model, api_key,
                    priority, base_url,
                ),
            )

    async def list_provider_metadata(self, *, organization_id: str) -> list[dict[str, object]]:
        """执行 list_provider_metadata 的业务流程并返回该流程的结果。

Args:
    organization_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        async with self._pool.connection() as connection, connection.cursor(
            row_factory=dict_row
        ) as cursor:
                await cursor.execute(
                    """
                    SELECT id, name, adapter_type, model, base_url, priority, enabled,
                           (api_key <> '') AS credential_configured,
                           right(api_key, 4) AS credential_suffix
                    FROM rag_model_providers
                    WHERE organization_id = %s
                    ORDER BY priority, id
                    """,
                    (organization_id,),
                )
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def bind_purpose(
        self, *, organization_id: str, purpose: str,
        primary_provider_id: str, fallback_provider_ids: list[str],
    ) -> None:
        """执行 bind_purpose 的业务流程并返回该流程的结果。

Args:
    organization_id: 参数语义、输入边界和安全约束。
    purpose: 参数语义、输入边界和安全约束。
    primary_provider_id: 参数语义、输入边界和安全约束。
    fallback_provider_ids: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
        if primary_provider_id in fallback_provider_ids:
            raise ValueError("主模型不能同时出现在备用模型列表")
        async with self._pool.connection() as connection, connection.transaction():
            await connection.execute(
                """
                INSERT INTO rag_model_purpose_bindings
                    (organization_id, purpose, primary_provider_id, fallback_provider_ids)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (organization_id, purpose) DO UPDATE SET
                    primary_provider_id = EXCLUDED.primary_provider_id,
                    fallback_provider_ids = EXCLUDED.fallback_provider_ids,
                    revision = rag_model_purpose_bindings.revision + 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (organization_id, purpose, primary_provider_id, fallback_provider_ids),
            )
