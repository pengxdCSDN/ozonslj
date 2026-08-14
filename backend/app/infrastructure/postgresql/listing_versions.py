import asyncio
import json
from typing import cast
from uuid import uuid4

from backend.app.domain.listing_version import ListingVersion, ListingVersionStatus
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresListingVersionGateway:
    """保存原文、人工修改文本、差异和审核状态，供后续受控发布使用。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_version(
        self, *, workspace_id: str, product_scope: str, version: ListingVersion
    ) -> ListingVersion:
        return await asyncio.to_thread(self._save, workspace_id, product_scope, version)

    def _save(
        self, workspace_id: str, product_scope: str, version: ListingVersion
    ) -> ListingVersion:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO listing_versions
                    (id, organization_id, workspace_id, product_scope, version_no,
                     original_text, edited_text, status, diff)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id, product_scope,
                    version.version, version.original_text, version.edited_text,
                    version.status, json.dumps(version.diff, ensure_ascii=False),
                ),
            )
        return version

    async def list_versions(
        self, *, workspace_id: str, product_scope: str, limit: int
    ) -> list[ListingVersion]:
        return await asyncio.to_thread(self._list_versions, workspace_id, product_scope, limit)

    def _list_versions(
        self, workspace_id: str, product_scope: str, limit: int
    ) -> list[ListingVersion]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT version_no, original_text, edited_text, status, diff
                    FROM listing_versions
                    WHERE organization_id=%s AND workspace_id=%s AND product_scope=%s
                    ORDER BY version_no DESC, created_at DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, product_scope, limit),
            ).fetchall()
        return [
            ListingVersion(
                version=int(row["version_no"]), original_text=str(row["original_text"]),
                edited_text=str(row["edited_text"]),
                status=cast(ListingVersionStatus, str(row["status"])),
                diff=tuple(str(value) for value in row["diff"]),
            )
            for row in rows
        ]
