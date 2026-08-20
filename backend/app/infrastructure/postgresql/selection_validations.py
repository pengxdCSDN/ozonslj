"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.selection_validate import ValidateResult
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresValidateResultGateway:
    """保存 FBO/FBS 验证假设和结果快照，确保利润结论可回溯。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。"""
        self._sessions = sessions
        self._context = context

    async def save_validation(
        self, *, workspace_id: str, assumptions: dict[str, object], result: ValidateResult
    ) -> ValidateResult:
        """执行 save_validation 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._save, workspace_id, assumptions, result)

    def _save(
        self, workspace_id: str, assumptions: dict[str, object], result: ValidateResult
    ) -> ValidateResult:
        """执行内部步骤 _save，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO selection_validations
                    (id, organization_id, workspace_id, sku, input_assumptions,
                     result_snapshot, incomplete)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id, result.sku,
                    json.dumps(assumptions, ensure_ascii=False),
                    json.dumps(asdict(result), ensure_ascii=False), result.incomplete,
                ),
            )
        return result

    async def list_validations(
        self, *, workspace_id: str, limit: int
    ) -> list[ValidateResult]:
        """执行 list_validations 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._list_validations, workspace_id, limit)

    def _list_validations(self, workspace_id: str, limit: int) -> list[ValidateResult]:
        """执行内部步骤 _list_validations，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT result_snapshot FROM selection_validations
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [ValidateResult(**row["result_snapshot"]) for row in rows]
