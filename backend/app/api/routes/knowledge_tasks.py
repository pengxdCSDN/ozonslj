"""RAG Worker 任务 API；任务状态以持久化任务摘要为准，Redis 只做调度信号。"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.rag_worker import RagWorkerQueue, RagWorkerTask

router = APIRouter(prefix="/v1/knowledge-tasks", tags=["knowledge-tasks"])
_queue = RagWorkerQueue(max_concurrency=1, lease_seconds=300)


class TaskCreatePayload(BaseModel):
    task_type: str = Field(pattern="^(ingest|parse|chunk|index|withdraw|delete|rebuild)$")
    organization_id: str = Field(min_length=1, max_length=100)


class TaskFinishPayload(BaseModel):
    status: str = Field(pattern="^(succeeded|failed|cancelled)$")
    error_code: str | None = Field(default=None, max_length=100)


def _task_response(task: RagWorkerTask) -> dict[str, object]:
    return {
        "task_id": task.task_id, "task_type": task.task_type,
        "organization_id": task.organization_id, "status": task.status,
        "attempt": task.attempt,
        "lease_until": task.lease_until.isoformat() if task.lease_until else None,
        "error_code": task.error_code,
    }


@router.post("", response_model=dict[str, object], status_code=202)
async def create_knowledge_task(payload: TaskCreatePayload) -> dict[str, object]:
    task = _queue.enqueue(RagWorkerTask(str(uuid4()), payload.task_type, payload.organization_id))
    return _task_response(task)


@router.get("", response_model=list[dict[str, object]])
async def list_knowledge_tasks(organization_id: str | None = None) -> list[dict[str, object]]:
    """返回任务状态，供管理页显示排队、租约过期和失败原因。"""

    return [_task_response(task) for task in _queue.list(organization_id=organization_id)]


@router.post("/{task_id}/claim", response_model=dict[str, object], status_code=200)
async def claim_knowledge_task(task_id: str, organization_id: str) -> dict[str, object]:
    try:
        existing = _queue.get(task_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="RAG 任务不存在") from error
    if existing.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="RAG 任务不存在")
    claimed = _queue.claim(organization_id=organization_id, now=datetime.now(UTC))
    if claimed is None or claimed.task_id != task_id:
        raise HTTPException(status_code=409, detail="任务当前不可领取")
    return _task_response(claimed)


@router.post("/{task_id}/finish", response_model=dict[str, object])
async def finish_knowledge_task(task_id: str, payload: TaskFinishPayload) -> dict[str, object]:
    try:
        finished = _queue.finish(task_id, status=payload.status, error_code=payload.error_code)  # type: ignore[arg-type]
    except KeyError as error:
        raise HTTPException(status_code=404, detail="RAG 任务不存在") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _task_response(finished)
