"""RAG Worker 任务 API；任务状态以持久化任务摘要为准，Redis 只做调度信号。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_rag_task_gateway, get_rag_task_queue
from backend.app.domain.rag_worker import RagWorkerTask
from backend.app.infrastructure.postgresql.rag_tasks import PostgresRagTaskGateway
from backend.app.infrastructure.redis_rag_tasks import RedisRagTaskQueue

router = APIRouter(prefix="/v1/knowledge-tasks", tags=["knowledge-tasks"])
class TaskCreatePayload(BaseModel):
    """说明 TaskCreatePayload 的职责、状态边界和对外协作关系。"""
    task_type: str = Field(pattern="^(ingest|parse|chunk|index|withdraw|delete|rebuild)$")
    organization_id: str = Field(min_length=1, max_length=100)
    source_id: str = Field(min_length=1, max_length=100)
    document_version_id: str = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=1, max_length=200)


class TaskFinishPayload(BaseModel):
    """说明 TaskFinishPayload 的职责、状态边界和对外协作关系。"""
    status: str = Field(pattern="^(succeeded|failed|cancelled)$")
    error_code: str | None = Field(default=None, max_length=100)


def _task_response(task: RagWorkerTask) -> dict[str, object]:
    """执行内部步骤 _task_response，供同一模块的公开流程复用。

Args:
    task: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return {
        "task_id": task.task_id, "task_type": task.task_type,
        "organization_id": task.organization_id, "status": task.status,
        "source_id": task.source_id, "document_version_id": task.document_version_id,
        "attempt": task.attempt,
        "lease_until": task.lease_until.isoformat() if task.lease_until else None,
        "error_code": task.error_code,
        "archived": task.archived_at is not None,
    }


@router.post("", response_model=dict[str, object], status_code=202)
async def create_knowledge_task(
    payload: TaskCreatePayload,
    gateway: Annotated[PostgresRagTaskGateway, Depends(get_rag_task_gateway)],
    queue: Annotated[RedisRagTaskQueue, Depends(get_rag_task_queue)],
) -> dict[str, object]:
    """执行 create_knowledge_task 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    queue: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
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
    include_archived: bool = False,
) -> list[dict[str, object]]:
    """返回任务状态，供管理页显示排队、租约过期和失败原因。

Args:
    gateway: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    include_archived: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    tasks = await gateway.list_tasks(include_archived=include_archived)
    return [
        _task_response(task)
        for task in tasks
        if organization_id is None or task.organization_id == organization_id
    ]


@router.post("/cleanup", response_model=dict[str, int])
async def cleanup_knowledge_tasks(
    gateway: Annotated[PostgresRagTaskGateway, Depends(get_rag_task_gateway)],
    older_than_days: int = Query(default=30, ge=1, le=3650),
) -> dict[str, int]:
    """清理已归档且超过保留期的失败/取消任务；默认保留 30 天。

Args:
    gateway: 参数语义、输入边界和安全约束。
    older_than_days: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return {"deleted_count": await gateway.cleanup_archived(older_than_days)}


@router.post("/{task_id}/claim", response_model=dict[str, object], status_code=200)
async def claim_knowledge_task(
    task_id: str,
    organization_id: str,
    gateway: Annotated[
        PostgresRagTaskGateway, Depends(get_rag_task_gateway)
    ],
) -> dict[str, object]:
    """执行 claim_knowledge_task 的业务流程并返回该流程的结果。

Args:
    task_id: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    claimed = await gateway.claim(task_id, "rag-api-claim", 300)
    if claimed is None or claimed.organization_id != organization_id:
        raise HTTPException(status_code=409, detail="任务当前不可领取")
    return _task_response(claimed)


@router.post("/{task_id}/finish", response_model=dict[str, object])
async def finish_knowledge_task(
    task_id: str, payload: TaskFinishPayload,
    gateway: Annotated[PostgresRagTaskGateway, Depends(get_rag_task_gateway)],
) -> dict[str, object]:
    """执行 finish_knowledge_task 的业务流程并返回该流程的结果。

Args:
    task_id: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    finished = await gateway.finish(task_id, payload.status, payload.error_code)
    if finished is None:
        raise HTTPException(status_code=409, detail="任务不存在或不在 running 状态")
    return _task_response(finished)


@router.post("/{task_id}/cancel", response_model=dict[str, object])
async def cancel_knowledge_task(
    task_id: str,
    gateway: Annotated[PostgresRagTaskGateway, Depends(get_rag_task_gateway)],
) -> dict[str, object]:
    """执行 cancel_knowledge_task 的业务流程并返回该流程的结果。

Args:
    task_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    task = await gateway.cancel(task_id)
    if task is None:
        raise HTTPException(status_code=409, detail="任务当前不可取消")
    return _task_response(task)


@router.post("/{task_id}/archive", response_model=dict[str, object])
async def archive_knowledge_task(
    task_id: str,
    gateway: Annotated[PostgresRagTaskGateway, Depends(get_rag_task_gateway)],
) -> dict[str, object]:
    """执行 archive_knowledge_task 的业务流程并返回该流程的结果。

Args:
    task_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    task = await gateway.archive(task_id)
    if task is None:
        raise HTTPException(status_code=409, detail="只有失败或已取消任务可以归档")
    return _task_response(task)


@router.post("/{task_id}/retry", response_model=dict[str, object], status_code=202)
async def retry_knowledge_task(
    task_id: str,
    gateway: Annotated[PostgresRagTaskGateway, Depends(get_rag_task_gateway)],
    queue: Annotated[RedisRagTaskQueue, Depends(get_rag_task_queue)],
) -> dict[str, object]:
    """执行 retry_knowledge_task 的业务流程并返回该流程的结果。

Args:
    task_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    queue: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    task = await gateway.retry(task_id)
    if task is None:
        raise HTTPException(status_code=409, detail="只有失败或已取消任务可以重试")
    await queue.enqueue(task.task_id)
    return _task_response(task)
