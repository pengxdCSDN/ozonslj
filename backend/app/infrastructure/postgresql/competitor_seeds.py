"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from typing import Any
from uuid import uuid4

from backend.app.domain.competitor_seed import CompetitorSeed
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresCompetitorSeedGateway:
    """说明 PostgresCompetitorSeedGateway 的职责、状态边界和对外协作关系。"""
    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def create_seed(self, *, workspace_id: str, url: str) -> CompetitorSeed:
        """执行 create_seed 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    url: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._create_seed, workspace_id, url)

    def _create_seed(self, workspace_id: str, url: str) -> CompetitorSeed:
        """执行内部步骤 _create_seed，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    url: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                INSERT INTO competitor_seeds (id, organization_id, workspace_id, url)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (organization_id, workspace_id, url)
                DO UPDATE SET url = EXCLUDED.url
                RETURNING id, workspace_id, url, title, status
                """,
                (str(uuid4()), self._context.organization_id, workspace_id, url),
            ).fetchone()
        if row is None:
            raise RuntimeError("竞品种子创建后未返回记录")
        return _seed_from_row(row)

    async def list_seeds(self, *, workspace_id: str) -> list[CompetitorSeed]:
        """执行 list_seeds 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_seeds, workspace_id)

    def _list_seeds(self, workspace_id: str) -> list[CompetitorSeed]:
        """执行内部步骤 _list_seeds，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT id, workspace_id, url, title, status FROM competitor_seeds
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC""",
                (self._context.organization_id, workspace_id),
            ).fetchall()
        return [_seed_from_row(row) for row in rows]

    async def update_status(self, *, seed_id: str, status: str) -> CompetitorSeed | None:
        """执行 update_status 的业务流程并返回该流程的结果。

Args:
    seed_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._update_status, seed_id, status)

    def _update_status(self, seed_id: str, status: str) -> CompetitorSeed | None:
        """执行内部步骤 _update_status，供同一模块的公开流程复用。

Args:
    seed_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE competitor_seeds SET status = %s
                WHERE id = %s AND organization_id = %s
                RETURNING id, workspace_id, url, title, status""",
                (status, seed_id, self._context.organization_id),
            ).fetchone()
        return _seed_from_row(row) if row is not None else None


def _seed_from_row(row: dict[str, Any]) -> CompetitorSeed:
    """执行内部步骤 _seed_from_row，供同一模块的公开流程复用。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return CompetitorSeed(
        id=str(row["id"]), workspace_id=str(row["workspace_id"]),
        url=str(row["url"]), title=str(row["title"]) if row["title"] else None,
        status=str(row["status"]),
    )
