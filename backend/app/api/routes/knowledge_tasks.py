"""RAG Worker 任务 API；任务状态以持久化任务摘要为准，Redis 只做调度信号。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_rag_task_gateway, get_rag_task_queue
from backend.app.domain.rag_worker import RagWorkerTask
from backend.app.infrastructure.postgresql.rag_tasks import PostgresRagTaskGateway
from backend.app.infrastructure.redis_rag_tasks import RedisRagTaskQueue

router = APIRouter(prefix="/v1/knowledge-tasks", tags=["knowledge-tasks"])
class TaskCreatePayload(BaseModel):
    task_type: str = Field(pattern="^(ingest|parse|chunk|index|withdraw|delete|rebuild)$")
    organization_id: str = Field(min_length=1, max_length=100)
    source_id: str = Field(min_length=1, max_length=100)
    document_version_id: str = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=1, max_length=200)


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
async def create_knowledge_task(
    payload: TaskCreatePayload,
    gateway: Annotated[PostgresRagTaskGateway, Depends(get_rag_task_gateway)],
    queue: Annotated[RedisRagTaskQueue, Depends(get_rag_task_queue)],
) -> dict[str, object]:
    task = await gateway.create(
        payload.task_type, payload.idempotency_key, payload.source_id,
        payload.document_version_id,
    )
    await queue.enqueue(task.task_id)
    return _task_response(task)


@router.get("", response_model=list[dict[str, object]])
async def list_knowledge_tasks(
    gateway: Annotated[PostgresRagTaskGateway, Depends(get_rag_task_gateway)],
    organization_id: str | None = None,
) -> list[dict[str, object]]:
    """返回任务状态，供管理页显示排队、租约过期和失败原因。"""

    tasks = await gateway.list_tasks()
    return [
        _task_response(task)
        for task in tasks
        if organization_id is None or task.organization_id == organization_id
    ]


@router.post("/{task_id}/claim", response_model=dict[str, object], status_code=200)
async def claim_knowledge_task(
    task_id: str,
    organization_id: str,
    gateway: Annotated[
        PostgresRagTaskGateway, Depends(get_rag_task_gateway)
    ],
) -> dict[str, object]:
    claimed = await gateway.claim(task_id, "rag-api-claim", 300)
    if claimed is None or claimed.organization_id != organization_id:
        raise HTTPException(status_code=409, detail="任务当前不可领取")
    return _task_response(claimed)


@router.post("/{task_id}/finish", response_model=dict[str, object])
async def finish_knowledge_task(
    task_id: str, payload: TaskFinishPayload,
    gateway: Annotated[PostgresRagTaskGateway, Depends(get_rag_task_gateway)],
) -> dict[str, object]:
    finished = await gateway.finish(task_id, payload.status, payload.error_code)
    if finished is None:
        raise HTTPException(status_code=409, detail="任务不存在或不在 running 状态")
    return _task_response(finished)


@router.post("/{task_id}/cancel", response_model=dict[str, object])
async def cancel_knowledge_task(
    task_id: str,
    gateway: Annotated[PostgresRagTaskGateway, Depends(get_rag_task_gateway)],
) -> dict[str, object]:
    task = await gateway.cancel(task_id)
    if task is None:
        raise HTTPException(status_code=409, detail="任务当前不可取消")
    return _task_response(task)


@router.post("/{task_id}/retry", response_model=dict[str, object], status_code=202)
async def retry_knowledge_task(
    task_id: str,
    gateway: Annotated[PostgresRagTaskGateway, Depends(get_rag_task_gateway)],
    queue: Annotated[RedisRagTaskQueue, Depends(get_rag_task_queue)],
) -> dict[str, object]:
    task = await gateway.retry(task_id)
    if task is None:
        raise HTTPException(status_code=409, detail="只有失败或已取消任务可以重试")
    await queue.enqueue(task.task_id)
    return _task_response(task)
