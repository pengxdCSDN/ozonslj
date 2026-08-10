import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.selection_expand import ExpandResult
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresExpandResultGateway:
    """保存关键词、属性、场景和变体扩展快照，供人工进入 Validate。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_expansion(self, *, workspace_id: str, result: ExpandResult) -> ExpandResult:
        return await asyncio.to_thread(self._save, workspace_id, result)

    def _save(self, workspace_id: str, result: ExpandResult) -> ExpandResult:
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
        return await asyncio.to_thread(self._list_expansions, workspace_id, limit)

    def _list_expansions(self, workspace_id: str, limit: int) -> list[ExpandResult]:
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
