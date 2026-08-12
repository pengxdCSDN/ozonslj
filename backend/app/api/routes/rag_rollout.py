"""RAG 能力探针与受控试运行切换接口。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.model_fallback import RolloutFlag, rollout_allows_execution

router = APIRouter(tags=["rag-rollout"])
_flag = RolloutFlag("knowledge-rag", "pilot", "2099-01-01T00:00:00Z")


class RolloutTransitionPayload(BaseModel):
    mode: str = Field(pattern="^(disabled|shadow|pilot|internal)$")
    reason: str = Field(min_length=1, max_length=500)
    pilot_until: str | None = None


@router.get("/v1/capabilities/knowledge-rag")
async def knowledge_rag_capabilities() -> dict[str, object]:
    return {
        "knowledge_management": True,
        "knowledge_query": True,
        "citations": True,
        "feedback": True,
        "evaluation": True,
        "rollout_mode": _flag.mode,
        "single_user_deployment": True,
    }


@router.post("/v1/rag-rollout/transitions")
async def transition_rag_rollout(payload: RolloutTransitionPayload) -> dict[str, object]:
    global _flag
    if payload.mode == "internal" and not payload.reason.strip():
        raise HTTPException(status_code=400, detail="internal 模式必须提供切换理由")
    _flag = RolloutFlag("knowledge-rag", payload.mode, payload.pilot_until)  # type: ignore[arg-type]
    allowed = rollout_allows_execution(_flag, is_admin=True, now_iso="2026-08-12T00:00:00Z")
    return {"mode": _flag.mode, "pilot_until": _flag.pilot_until, "execution_allowed": allowed}
