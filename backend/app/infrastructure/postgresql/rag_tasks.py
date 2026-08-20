"""RAG 任务 PostgreSQL 网关；任务事实不再依赖 API 进程内存。"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any
from uuid import uuid4

from backend.app.domain.rag_worker import RagWorkerTask
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresRagTaskGateway:
    """保存 RAG 任务状态，并以数据库租约支持进程重启后的重新领取。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def create(self, task_type: str, idempotency_key: str, source_id: str,
                     document_version_id: str) -> RagWorkerTask:
        """执行 create 的业务流程并返回该流程的结果。

Args:
    task_type: 参数语义、输入边界和安全约束。
    idempotency_key: 参数语义、输入边界和安全约束。
    source_id: 参数语义、输入边界和安全约束。
    document_version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(
            self._create, task_type, idempotency_key, source_id, document_version_id
        )

    def _create(self, task_type: str, idempotency_key: str, source_id: str,
                document_version_id: str) -> RagWorkerTask:
        """执行内部步骤 _create，供同一模块的公开流程复用。

Args:
    task_type: 参数语义、输入边界和安全约束。
    idempotency_key: 参数语义、输入边界和安全约束。
    source_id: 参数语义、输入边界和安全约束。
    document_version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """INSERT INTO rag_ingestion_jobs
                   (id, organization_id, source_id, document_version_id, job_type, idempotency_key)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (organization_id, idempotency_key)
                   DO UPDATE SET idempotency_key = EXCLUDED.idempotency_key
                   RETURNING id, job_type, organization_id, status, attempt_count,
                             lease_expires_at, error_code, source_id, document_version_id,
                             archived_at""",
                (f"rag-{uuid4()}", self._context.organization_id, source_id,
                 document_version_id, task_type, idempotency_key),
            ).fetchone()
        if row is None:
            raise RuntimeError("RAG 任务创建后未返回任务事实")
        return _task(row)

    async def list_tasks(self, *, include_archived: bool = False) -> list[RagWorkerTask]:
        """执行 list_tasks 的业务流程并返回该流程的结果。

Args:
    include_archived: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list, include_archived)

    async def archive(self, task_id: str) -> RagWorkerTask | None:
        """归档失败或取消任务；保留状态、错误码和任务 ID 供审计复盘。

Args:
    task_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._archive, task_id)

    async def cleanup_archived(self, older_than_days: int) -> int:
        """清理达到保留期的已归档终结任务，不触碰排队、运行中或成功任务。

Args:
    older_than_days: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._cleanup_archived, older_than_days)

    async def dispatchable_ids(self, limit: int) -> list[str]:
        """执行 dispatchable_ids 的业务流程并返回该流程的结果。

Args:
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._dispatchable_ids, limit)

    def _dispatchable_ids(self, limit: int) -> list[str]:
        """执行内部步骤 _dispatchable_ids，供同一模块的公开流程复用。

Args:
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """WITH candidates AS (
                       SELECT id FROM rag_ingestion_jobs
                       WHERE organization_id = %s
                         AND (status = 'queued' OR
                              (status = 'running' AND lease_expires_at < CURRENT_TIMESTAMP))
                       ORDER BY created_at
                       LIMIT %s
                   )
                   UPDATE rag_ingestion_jobs AS jobs
                   SET status = 'queued', lease_expires_at = NULL
                   FROM candidates
                   WHERE jobs.organization_id = %s AND jobs.id = candidates.id
                   RETURNING jobs.id AS id
                   """,
                (self._context.organization_id, limit, self._context.organization_id),
            ).fetchall()
        return [row["id"] for row in rows]

    async def details(self, task_id: str) -> tuple[RagWorkerTask, str, str | None] | None:
        """执行 details 的业务流程并返回该流程的结果。

Args:
    task_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._details, task_id)

    def _details(self, task_id: str) -> tuple[RagWorkerTask, str, str | None] | None:
        """执行内部步骤 _details，供同一模块的公开流程复用。

Args:
    task_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """SELECT id, job_type, organization_id, status, attempt_count,
                          lease_expires_at, error_code, source_id, document_version_id,
                          archived_at
                   FROM rag_ingestion_jobs WHERE organization_id = %s AND id = %s""",
                (self._context.organization_id, task_id),
            ).fetchone()
        if row is None:
            return None
        return _task(row), row["source_id"], row["document_version_id"]

    async def claim(self, task_id: str, worker_id: str, lease_seconds: int) -> RagWorkerTask | None:
        """执行 claim 的业务流程并返回该流程的结果。

Args:
    task_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    lease_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._claim, task_id, worker_id, lease_seconds)

    def _claim(self, task_id: str, worker_id: str, lease_seconds: int) -> RagWorkerTask | None:
        """执行内部步骤 _claim，供同一模块的公开流程复用。

Args:
    task_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    lease_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE rag_ingestion_jobs
                   SET status = 'running', attempt_count = attempt_count + 1,
                       lease_expires_at = CURRENT_TIMESTAMP + %s
                   WHERE organization_id = %s AND id = %s
                     AND (status = 'queued' OR
                          (status = 'running' AND lease_expires_at < CURRENT_TIMESTAMP))
                   RETURNING id, job_type, organization_id, status, attempt_count,
                             lease_expires_at, error_code, source_id, document_version_id,
                             archived_at""",
                (timedelta(seconds=lease_seconds), self._context.organization_id, task_id),
            ).fetchone()
        return _task(row) if row is not None else None

    async def finish(
        self, task_id: str, status: str, error_code: str | None = None
    ) -> RagWorkerTask | None:
        """执行 finish 的业务流程并返回该流程的结果。

Args:
    task_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。
    error_code: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._finish, task_id, status, error_code)

    async def cancel(self, task_id: str) -> RagWorkerTask | None:
        """取消尚未完成的任务；数据库状态先落为 cancelled，避免只取消 Redis 信号。

Args:
    task_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._cancel, task_id)

    def _cancel(self, task_id: str) -> RagWorkerTask | None:
        """执行内部步骤 _cancel，供同一模块的公开流程复用。

Args:
    task_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE rag_ingestion_jobs
                   SET status = 'cancelled', error_code = 'cancelled_by_operator',
                       finished_at = CURRENT_TIMESTAMP, lease_expires_at = NULL
                   WHERE organization_id = %s AND id = %s
                     AND status IN ('queued', 'running')
                   RETURNING id, job_type, organization_id, status, attempt_count,
                             lease_expires_at, error_code, source_id, document_version_id,
                             archived_at""",
                (self._context.organization_id, task_id),
            ).fetchone()
        return _task(row) if row is not None else None

    async def retry(self, task_id: str) -> RagWorkerTask | None:
        """把失败或已取消任务重新排队；保留原任务 ID 和尝试次数便于审计。

Args:
    task_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._retry, task_id)

    def _retry(self, task_id: str) -> RagWorkerTask | None:
        """执行内部步骤 _retry，供同一模块的公开流程复用。

Args:
    task_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE rag_ingestion_jobs
                   SET status = 'queued', error_code = NULL,
                       finished_at = NULL, lease_expires_at = NULL
                   WHERE organization_id = %s AND id = %s
                     AND status IN ('failed', 'cancelled')
                   RETURNING id, job_type, organization_id, status, attempt_count,
                             lease_expires_at, error_code, source_id, document_version_id""",
                (self._context.organization_id, task_id),
            ).fetchone()
        return _task(row) if row is not None else None

    def _archive(self, task_id: str) -> RagWorkerTask | None:
        """执行内部步骤 _archive，供同一模块的公开流程复用。

Args:
    task_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE rag_ingestion_jobs
                   SET archived_at = CURRENT_TIMESTAMP
                   WHERE organization_id = %s AND id = %s
                     AND status IN ('failed', 'cancelled')
                     AND archived_at IS NULL
                   RETURNING id, job_type, organization_id, status, attempt_count,
                             lease_expires_at, error_code, source_id, document_version_id,
                             archived_at""",
                (self._context.organization_id, task_id),
            ).fetchone()
        return _task(row) if row is not None else None

    def _cleanup_archived(self, older_than_days: int) -> int:
        """执行内部步骤 _cleanup_archived，供同一模块的公开流程复用。

Args:
    older_than_days: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            result = connection.execute(
                """DELETE FROM rag_ingestion_jobs
                   WHERE organization_id = %s
                     AND archived_at IS NOT NULL
                     AND archived_at <= CURRENT_TIMESTAMP - %s
                     AND status IN ('failed', 'cancelled')""",
                (self._context.organization_id, timedelta(days=older_than_days)),
            )
        return result.rowcount

    async def heartbeat(self, task_id: str, worker_id: str, lease_seconds: int) -> bool:
        """执行 heartbeat 的业务流程并返回该流程的结果。

Args:
    task_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    lease_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._heartbeat, task_id, worker_id, lease_seconds)

    def _heartbeat(self, task_id: str, worker_id: str, lease_seconds: int) -> bool:
        """执行内部步骤 _heartbeat，供同一模块的公开流程复用。

Args:
    task_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    lease_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE rag_ingestion_jobs
                   SET lease_expires_at = CURRENT_TIMESTAMP + %s
                   WHERE organization_id = %s AND id = %s AND status = 'running'
                   RETURNING id""",
                (timedelta(seconds=lease_seconds), self._context.organization_id, task_id),
            ).fetchone()
        return row is not None

    def _finish(self, task_id: str, status: str, error_code: str | None) -> RagWorkerTask | None:
        """执行内部步骤 _finish，供同一模块的公开流程复用。

Args:
    task_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。
    error_code: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE rag_ingestion_jobs
                   SET status = %s, error_code = %s, finished_at = CURRENT_TIMESTAMP,
                       lease_expires_at = NULL
                   WHERE organization_id = %s AND id = %s AND status = 'running'
                   RETURNING id, job_type, organization_id, status, attempt_count,
                             lease_expires_at, error_code, source_id, document_version_id""",
                (status, error_code, self._context.organization_id, task_id),
            ).fetchone()
        return _task(row) if row is not None else None

    def _list(self, include_archived: bool) -> list[RagWorkerTask]:
        """执行内部步骤 _list，供同一模块的公开流程复用。

Args:
    include_archived: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT id, job_type, organization_id, status, attempt_count,
                          lease_expires_at, error_code, source_id, document_version_id,
                          archived_at
                   FROM rag_ingestion_jobs
                   WHERE organization_id = %s
                     AND (%s OR archived_at IS NULL)
                   ORDER BY created_at DESC""",
                (self._context.organization_id, include_archived),
            ).fetchall()
        return [_task(row) for row in rows]


def _task(row: dict[str, Any]) -> RagWorkerTask:
    """执行内部步骤 _task，供同一模块的公开流程复用。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return RagWorkerTask(
        task_id=row["id"], task_type=row["job_type"],
        organization_id=row["organization_id"], status=row["status"],
        source_id=row.get("source_id"), document_version_id=row.get("document_version_id"),
        attempt=row["attempt_count"], lease_until=row["lease_expires_at"],
        error_code=row["error_code"],
        archived_at=row.get("archived_at"),
    )
