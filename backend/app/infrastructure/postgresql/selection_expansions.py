"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.selection_expand import ExpandResult
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresExpandResultGateway:
    """保存关键词、属性、场景和变体扩展快照，供人工进入 Validate。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。"""
        self._sessions = sessions
        self._context = context

    async def save_expansion(self, *, workspace_id: str, result: ExpandResult) -> ExpandResult:
        """执行 save_expansion 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._save, workspace_id, result)

    def _save(self, workspace_id: str, result: ExpandResult) -> ExpandResult:
        """执行内部步骤 _save，供同一模块的公开流程复用。"""
        payload = asdict(result)
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO selection_expansions
                    (id, organization_id, workspace_id, seed_product, core_terms,
                     attribute_terms, scene_terms, variant_candidates, estimated)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    result.seed_product, json.dumps(payload["core_terms"], ensure_ascii=False),
                    json.dumps(payload["attribute_terms"], ensure_ascii=False),
                    json.dumps(payload["scene_terms"], ensure_ascii=False),
                    json.dumps(payload["variant_candidates"], ensure_ascii=False),
                    result.estimated,
                ),
            )
        return result

    async def list_expansions(
        self, *, workspace_id: str, limit: int
    ) -> list[ExpandResult]:
        """执行 list_expansions 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._list_expansions, workspace_id, limit)

    def _list_expansions(self, workspace_id: str, limit: int) -> list[ExpandResult]:
        """执行内部步骤 _list_expansions，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT seed_product, core_terms, attribute_terms, scene_terms,
                    variant_candidates, estimated FROM selection_expansions
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [ExpandResult(
            seed_product=str(row["seed_product"]),
            core_terms=tuple(str(value) for value in row["core_terms"]),
            attribute_terms=tuple(str(value) for value in row["attribute_terms"]),
            scene_terms=tuple(str(value) for value in row["scene_terms"]),
            variant_candidates=tuple(str(value) for value in row["variant_candidates"]),
            estimated=bool(row["estimated"]), missing_inputs=(),
        ) for row in rows]
