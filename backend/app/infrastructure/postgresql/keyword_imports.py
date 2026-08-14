import asyncio
from datetime import datetime
from typing import Any
from uuid import uuid4

from backend.app.domain.keyword_import import KeywordImportBatch, KeywordImportRow
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresKeywordImportGateway:
    """搜索词导入批次适配器；唯一指纹冲突时返回原批次。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def create_batch(
        self, *, workspace_id: str, fingerprint: str, rows: list[KeywordImportRow]
    ) -> KeywordImportBatch:
        return await asyncio.to_thread(
            self._create_batch, workspace_id, fingerprint, rows
        )

    def _create_batch(
        self, workspace_id: str, fingerprint: str, rows: list[KeywordImportRow]
    ) -> KeywordImportBatch:
        with self._sessions.transaction(self._context) as connection:
            existing = connection.execute(
                """
                SELECT id, workspace_id, fingerprint, row_count, created_at
                FROM keyword_report_imports
                WHERE organization_id = %s AND workspace_id = %s AND fingerprint = %s
                """,
                (self._context.organization_id, workspace_id, fingerprint),
            ).fetchone()
            row = connection.execute(
                """
                INSERT INTO keyword_report_imports
                    (id, organization_id, workspace_id, fingerprint, row_count)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (organization_id, workspace_id, fingerprint)
                DO UPDATE SET fingerprint = EXCLUDED.fingerprint
                RETURNING id, workspace_id, fingerprint, row_count, created_at
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    fingerprint, len(rows),
                ),
            ).fetchone()
            if row is not None:
                for item in rows:
                    connection.execute(
                        """
                        INSERT INTO keyword_report_import_rows
                            (id, import_id, keyword, search_count, conversion_rate, source_row)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (import_id, normalized_keyword) DO NOTHING
                        """,
                        (
                            str(uuid4()), row["id"], item.keyword, item.search_count,
                            item.conversion_rate, item.source_row,
                        ),
                    )
        if row is None:
            raise RuntimeError("导入批次创建后未返回记录")
        return _batch_from_row(row, reused=existing is not None)

    async def list_batches(self, *, workspace_id: str, limit: int = 50) -> list[KeywordImportBatch]:
        return await asyncio.to_thread(self._list_batches, workspace_id, limit)

    def _list_batches(self, workspace_id: str, limit: int) -> list[KeywordImportBatch]:
        # 指纹历史只按组织和工作区读取，便于确认重复提交复用的是哪一批事实。
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT id, workspace_id, fingerprint, row_count, created_at
                FROM keyword_report_imports
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [_batch_from_row(row) for row in rows]


def _batch_from_row(row: dict[str, Any], *, reused: bool = False) -> KeywordImportBatch:
    created_at = row["created_at"]
    if not isinstance(created_at, datetime):
        raise ValueError("导入批次 created_at 必须是有效时间")
    return KeywordImportBatch(
        id=str(row["id"]), workspace_id=str(row["workspace_id"]),
        fingerprint=str(row["fingerprint"]), row_count=int(row["row_count"]),
        created_at=created_at,
        reused=reused,
    )
