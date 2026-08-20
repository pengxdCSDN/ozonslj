"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.diff_preview import DiffPreview
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresDiffPreviewGateway:
    """保存写入前差异预览，强制保留来源、影响和人工复核标记。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。"""
        self._sessions = sessions
        self._context = context

    async def save_preview(
        self, *, workspace_id: str, previews: list[DiffPreview]
    ) -> list[DiffPreview]:
        """执行 save_preview 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._save, workspace_id, previews)

    def _save(self, workspace_id: str, previews: list[DiffPreview]) -> list[DiffPreview]:
        """执行内部步骤 _save，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO diff_previews
                    (id, organization_id, workspace_id, previews)
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    json.dumps([asdict(item) for item in previews], ensure_ascii=False),
                ),
            )
        return previews
