"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from datetime import timedelta
from typing import Any
from uuid import uuid4

from backend.app.domain.sync_job import SyncJob, SyncJobPage, SyncResourceType
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext

_JOB_COLUMNS = """id, workspace_id, resource_type, status, processed_count, failure_count,
error_code, error_message, attempt_count, max_attempts, next_attempt_at,
created_at, started_at, completed_at, lease_owner, lease_expires_at, heartbeat_at"""


class PostgresSyncJobGateway:
    """原子创建幂等同步任务，并从 PostgreSQL 读取任务事实。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def create_sync_job(
        self,
        *,
        workspace_id: str,
        resource_type: SyncResourceType,
        idempotency_key: str,
    ) -> SyncJob:
        """执行 create_sync_job 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    resource_type: 参数语义、输入边界和安全约束。
    idempotency_key: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(
            self._create_sync_job, workspace_id, resource_type, idempotency_key
        )

    def _create_sync_job(
        self, workspace_id: str, resource_type: SyncResourceType, idempotency_key: str
    ) -> SyncJob:
        """执行内部步骤 _create_sync_job，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    resource_type: 参数语义、输入边界和安全约束。
    idempotency_key: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                f"""
                INSERT INTO sync_jobs (
                    id, organization_id, workspace_id, resource_type, status,
                    requested_user_id, idempotency_key
                ) VALUES (%s, %s, %s, %s, 'queued', %s, %s)
                ON CONFLICT (organization_id, workspace_id, idempotency_key)
                    WHERE idempotency_key IS NOT NULL
                DO UPDATE SET idempotency_key = EXCLUDED.idempotency_key
                RETURNING {_JOB_COLUMNS}
                """,
                (
                    f"sync-{uuid4()}", self._context.organization_id, workspace_id,
                    resource_type, self._context.user_id, idempotency_key,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("同步任务创建后未返回任务事实")
        return _sync_job_from_row(row)

    async def get_sync_job(self, job_id: str) -> SyncJob | None:
        """执行 get_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._get_sync_job, job_id)

    def _get_sync_job(self, job_id: str) -> SyncJob | None:
        """执行内部步骤 _get_sync_job，供同一模块的公开流程复用。

Args:
    job_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                f"SELECT {_JOB_COLUMNS} FROM sync_jobs WHERE organization_id = %s AND id = %s",
                (self._context.organization_id, job_id),
            ).fetchone()
        return _sync_job_from_row(row) if row is not None else None

    async def list_sync_jobs(
        self, *, workspace_id: str, cursor: str | None, limit: int
    ) -> SyncJobPage:
        """执行 list_sync_jobs 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    cursor: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_sync_jobs, workspace_id, cursor, limit)

    def _list_sync_jobs(self, workspace_id: str, cursor: str | None, limit: int) -> SyncJobPage:
        """使用稳定的偏移游标读取任务历史；查询只读，不改变任务生命周期。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    cursor: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        offset = int(cursor or "0")
        with self._sessions.transaction(self._context) as connection:
            total_row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM sync_jobs
                WHERE organization_id = %s AND workspace_id = %s
                """,
                (self._context.organization_id, workspace_id),
            ).fetchone()
            rows = connection.execute(
                f"""
                SELECT {_JOB_COLUMNS} FROM sync_jobs
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC, id DESC
                OFFSET %s LIMIT %s
                """,
                (self._context.organization_id, workspace_id, offset, limit),
            ).fetchall()
        total = int(total_row["total"]) if total_row is not None else 0
        next_offset = offset + len(rows)
        return SyncJobPage(
            items=[_sync_job_from_row(row) for row in rows],
            total=total,
            next_cursor=str(next_offset) if next_offset < total else None,
        )

    async def request_cancel_sync_job(self, *, job_id: str) -> bool:
        """执行 request_cancel_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._request_cancel_sync_job, job_id)

    def _request_cancel_sync_job(self, job_id: str) -> bool:
        """取消只改变任务事实；执行中的任务由处理器在安全边界处结束。

Args:
    job_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                UPDATE sync_jobs
                SET status = CASE WHEN status = 'queued' THEN 'cancelled' ELSE status END,
                    cancel_requested_at = CURRENT_TIMESTAMP,
                    completed_at = CASE WHEN status = 'queued'
                                       THEN CURRENT_TIMESTAMP ELSE completed_at END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = %s AND id = %s
                  AND status IN ('queued', 'running')
                RETURNING id
                """,
                (self._context.organization_id, job_id),
            ).fetchone()
        return row is not None

    async def retry_sync_job(self, *, job_id: str) -> SyncJob | None:
        """执行 retry_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._retry_sync_job, job_id)

    def _retry_sync_job(self, job_id: str) -> SyncJob | None:
        """失败任务复用任务 ID 重新排队，清理旧错误但保留 attempt_count 约束。

Args:
    job_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                f"""
                UPDATE sync_jobs
                SET status = 'queued', error_code = NULL, error_message = NULL,
                    next_attempt_at = CURRENT_TIMESTAMP, cancel_requested_at = NULL,
                    completed_at = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = %s AND id = %s
                  AND status IN ('failed', 'partial')
                RETURNING {_JOB_COLUMNS}
                """,
                (self._context.organization_id, job_id),
            ).fetchone()
        return _sync_job_from_row(row) if row is not None else None

    async def list_dispatchable_sync_jobs(self, *, limit: int) -> list[SyncJob]:
        """执行 list_dispatchable_sync_jobs 的业务流程并返回该流程的结果。

Args:
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_dispatchable_sync_jobs, limit)

    def _list_dispatchable_sync_jobs(self, limit: int) -> list[SyncJob]:
        """执行内部步骤 _list_dispatchable_sync_jobs，供同一模块的公开流程复用。

Args:
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                f"""
                SELECT {_JOB_COLUMNS}
                FROM sync_jobs
                WHERE organization_id = %s
                  AND status = 'queued'
                  AND next_attempt_at <= CURRENT_TIMESTAMP
                ORDER BY next_attempt_at, created_at, id
                LIMIT %s
                """,
                (self._context.organization_id, limit),
            ).fetchall()
        return [_sync_job_from_row(row) for row in rows]

    async def claim_sync_job(
        self, *, job_id: str, worker_id: str, lease_seconds: int
    ) -> SyncJob | None:
        """执行 claim_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    lease_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._claim_sync_job, job_id, worker_id, lease_seconds)

    def _claim_sync_job(
        self, job_id: str, worker_id: str, lease_seconds: int
    ) -> SyncJob | None:
        """执行内部步骤 _claim_sync_job，供同一模块的公开流程复用。

Args:
    job_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    lease_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                f"""
                UPDATE sync_jobs SET status = 'running', lease_owner = %s,
                    lease_expires_at = CURRENT_TIMESTAMP + %s,
                    heartbeat_at = CURRENT_TIMESTAMP,
                    started_at = COALESCE(started_at, CURRENT_TIMESTAMP),
                    attempt_count = attempt_count + 1, updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = %s AND id = %s
                  AND attempt_count < max_attempts AND cancel_requested_at IS NULL
                  AND next_attempt_at <= CURRENT_TIMESTAMP
                  AND (status = 'queued' OR
                      (status = 'running' AND lease_expires_at < CURRENT_TIMESTAMP))
                RETURNING {_JOB_COLUMNS}
                """,
                (worker_id, timedelta(seconds=lease_seconds),
                 self._context.organization_id, job_id),
            ).fetchone()
        return _sync_job_from_row(row) if row is not None else None

    async def heartbeat_sync_job(
        self, *, job_id: str, worker_id: str, lease_seconds: int
    ) -> bool:
        """执行 heartbeat_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    lease_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                UPDATE sync_jobs SET heartbeat_at = CURRENT_TIMESTAMP,
                    lease_expires_at = CURRENT_TIMESTAMP + %s, updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = %s AND id = %s AND status = 'running'
                  AND lease_owner = %s AND lease_expires_at >= CURRENT_TIMESTAMP
                RETURNING id
                """,
                (timedelta(seconds=lease_seconds), self._context.organization_id,
                 job_id, worker_id),
            ).fetchone()
        return row is not None

    async def complete_sync_job(
        self, *, job_id: str, worker_id: str, processed_count: int, failure_count: int
    ) -> bool:
        """执行 complete_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    processed_count: 参数语义、输入边界和安全约束。
    failure_count: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        final_status = "partial" if failure_count else "succeeded"
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                UPDATE sync_jobs SET status = %s, processed_count = %s, failure_count = %s,
                    completed_at = CURRENT_TIMESTAMP, lease_owner = NULL,
                    lease_expires_at = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = %s AND id = %s AND status = 'running'
                  AND lease_owner = %s AND lease_expires_at >= CURRENT_TIMESTAMP
                RETURNING id
                """,
                (final_status, processed_count, failure_count,
                 self._context.organization_id, job_id, worker_id),
            ).fetchone()
        return row is not None

    async def fail_sync_job(
        self, *, job_id: str, worker_id: str, error_code: str, error_message: str,
        retry_delay_seconds: int,
    ) -> bool:
        """执行 fail_sync_job 的业务流程并返回该流程的结果。

Args:
    job_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    error_code: 参数语义、输入边界和安全约束。
    error_message: 参数语义、输入边界和安全约束。
    retry_delay_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                UPDATE sync_jobs SET
                    status = CASE WHEN attempt_count >= max_attempts THEN 'failed'
                                  ELSE 'queued' END,
                    error_code = %s, error_message = %s,
                    next_attempt_at = CURRENT_TIMESTAMP + %s,
                    completed_at = CASE WHEN attempt_count >= max_attempts
                                        THEN CURRENT_TIMESTAMP ELSE NULL END,
                    lease_owner = NULL, lease_expires_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = %s AND id = %s AND status = 'running'
                  AND lease_owner = %s AND lease_expires_at >= CURRENT_TIMESTAMP
                RETURNING id
                """,
                (error_code, error_message, timedelta(seconds=retry_delay_seconds),
                 self._context.organization_id, job_id, worker_id),
            ).fetchone()
        return row is not None


def _sync_job_from_row(row: dict[str, Any]) -> SyncJob:
    """执行内部步骤 _sync_job_from_row，供同一模块的公开流程复用。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return SyncJob(**{name: row[name] for name in (
        "id", "workspace_id", "resource_type", "status", "processed_count",
        "failure_count", "error_code", "error_message", "attempt_count",
        "max_attempts", "next_attempt_at", "created_at", "started_at", "completed_at",
        "lease_owner", "lease_expires_at", "heartbeat_at",
    )})
