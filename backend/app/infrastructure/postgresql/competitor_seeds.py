import asyncio
from typing import Any
from uuid import uuid4

from backend.app.domain.competitor_seed import CompetitorSeed
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresCompetitorSeedGateway:
    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def create_seed(self, *, workspace_id: str, url: str) -> CompetitorSeed:
        return await asyncio.to_thread(self._create_seed, workspace_id, url)

    def _create_seed(self, workspace_id: str, url: str) -> CompetitorSeed:
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
        return await asyncio.to_thread(self._list_seeds, workspace_id)

    def _list_seeds(self, workspace_id: str) -> list[CompetitorSeed]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT id, workspace_id, url, title, status FROM competitor_seeds
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC""",
                (self._context.organization_id, workspace_id),
            ).fetchall()
        return [_seed_from_row(row) for row in rows]

    async def update_status(self, *, seed_id: str, status: str) -> CompetitorSeed | None:
        return await asyncio.to_thread(self._update_status, seed_id, status)

    def _update_status(self, seed_id: str, status: str) -> CompetitorSeed | None:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE competitor_seeds SET status = %s
                WHERE id = %s AND organization_id = %s
                RETURNING id, workspace_id, url, title, status""",
                (status, seed_id, self._context.organization_id),
            ).fetchone()
        return _seed_from_row(row) if row is not None else None


def _seed_from_row(row: dict[str, Any]) -> CompetitorSeed:
    return CompetitorSeed(
        id=str(row["id"]), workspace_id=str(row["workspace_id"]),
        url=str(row["url"]), title=str(row["title"]) if row["title"] else None,
        status=str(row["status"]),
    )
