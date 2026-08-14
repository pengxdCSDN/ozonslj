"""知识索引对账 API；只生成计划，不接受客户端直接指定 Collection。"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.domain.rag_reconciliation import build_reconciliation_plan

router = APIRouter(prefix="/v1/knowledge-indexes", tags=["knowledge-indexes"])


class ReconcilePayload(BaseModel):
    published_chunk_ids: list[str] = Field(default_factory=list, max_length=10_000)
    indexed_chunk_ids: list[str] = Field(default_factory=list, max_length=10_000)
    metadata_chunk_ids: list[str] = Field(default_factory=list, max_length=10_000)


@router.post("/reconcile", response_model=dict[str, object])
async def reconcile_knowledge_index(payload: ReconcilePayload) -> dict[str, object]:
    plan = build_reconciliation_plan(
        set(payload.published_chunk_ids), set(payload.indexed_chunk_ids),
        metadata_ids=set(payload.metadata_chunk_ids),
    )
    return {
        "upsert_ids": list(plan.upsert_ids), "delete_ids": list(plan.delete_ids),
        "missing_metadata_ids": list(plan.missing_metadata_ids),
        "safe_to_publish": plan.safe_to_publish,
        "status": "ready" if plan.safe_to_publish else "blocked",
    }
