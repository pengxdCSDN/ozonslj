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
        self._sessions = sessions
        self._context = context

    async def create(self, task_type: str, idempotency_key: str, source_id: str,
                     document_version_id: str) -> RagWorkerTask:
        return await asyncio.to_thread(
            self._create, task_type, idempotency_key, source_id, document_version_id
        )

    def _create(self, task_type: str, idempotency_key: str, source_id: str,
                document_version_id: str) -> RagWorkerTask:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """INSERT INTO rag_ingestion_jobs
                   (id, organization_id, source_id, document_version_id, job_type, idempotency_key)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (organization_id, idempotency_key)
                   DO UPDATE SET idempotency_key = EXCLUDED.idempotency_key
                   RETURNING id, job_type, organization_id, status, attempt_count,
                             lease_expires_at, error_code""",
                (f"rag-{uuid4()}", self._context.organization_id, source_id,
                 document_version_id, task_type, idempotency_key),
            ).fetchone()
        if row is None:
            raise RuntimeError("RAG 任务创建后未返回任务事实")
        return _task(row)

    async def list_tasks(self) -> list[RagWorkerTask]:
        return await asyncio.to_thread(self._list)

    async def dispatchable_ids(self, limit: int) -> list[str]:
        return await asyncio.to_thread(self._dispatchable_ids, limit)

    def _dispatchable_ids(self, limit: int) -> list[str]:
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
        return await asyncio.to_thread(self._details, task_id)

    def _details(self, task_id: str) -> tuple[RagWorkerTask, str, str | None] | None:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """SELECT id, job_type, organization_id, status, attempt_count,
                          lease_expires_at, error_code, source_id, document_version_id
                   FROM rag_ingestion_jobs WHERE organization_id = %s AND id = %s""",
                (self._context.organization_id, task_id),
            ).fetchone()
        if row is None:
            return None
        return _task(row), row["source_id"], row["document_version_id"]

    async def claim(self, task_id: str, worker_id: str, lease_seconds: int) -> RagWorkerTask | None:
        return await asyncio.to_thread(self._claim, task_id, worker_id, lease_seconds)

    def _claim(self, task_id: str, worker_id: str, lease_seconds: int) -> RagWorkerTask | None:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE rag_ingestion_jobs
                   SET status = 'running', attempt_count = attempt_count + 1,
                       lease_expires_at = CURRENT_TIMESTAMP + %s
                   WHERE organization_id = %s AND id = %s
                     AND (status = 'queued' OR
                          (status = 'running' AND lease_expires_at < CURRENT_TIMESTAMP))
                   RETURNING id, job_type, organization_id, status, attempt_count,
                             lease_expires_at, error_code""",
                (timedelta(seconds=lease_seconds), self._context.organization_id, task_id),
            ).fetchone()
        return _task(row) if row is not None else None

    async def finish(
        self, task_id: str, status: str, error_code: str | None = None
    ) -> RagWorkerTask | None:
        return await asyncio.to_thread(self._finish, task_id, status, error_code)

    async def heartbeat(self, task_id: str, worker_id: str, lease_seconds: int) -> bool:
        return await asyncio.to_thread(self._heartbeat, task_id, worker_id, lease_seconds)

    def _heartbeat(self, task_id: str, worker_id: str, lease_seconds: int) -> bool:
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
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE rag_ingestion_jobs
                   SET status = %s, error_code = %s, finished_at = CURRENT_TIMESTAMP,
                       lease_expires_at = NULL
                   WHERE organization_id = %s AND id = %s AND status = 'running'
                   RETURNING id, job_type, organization_id, status, attempt_count,
                             lease_expires_at, error_code""",
                (status, error_code, self._context.organization_id, task_id),
            ).fetchone()
        return _task(row) if row is not None else None

    def _list(self) -> list[RagWorkerTask]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT id, job_type, organization_id, status, attempt_count,
                          lease_expires_at, error_code
                   FROM rag_ingestion_jobs WHERE organization_id = %s
                   ORDER BY created_at DESC""", (self._context.organization_id,)
            ).fetchall()
        return [_task(row) for row in rows]


def _task(row: dict[str, Any]) -> RagWorkerTask:
    return RagWorkerTask(
        task_id=row["id"], task_type=row["job_type"],
        organization_id=row["organization_id"], status=row["status"],
        attempt=row["attempt_count"], lease_until=row["lease_expires_at"],
        error_code=row["error_code"],
    )
