"""数据质量检查任务 PostgreSQL 适配器。"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, cast
from uuid import uuid4

from backend.app.domain.data_quality import QualityCheckJob
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresQualityCheckJobGateway:
    """以工作区和幂等键原子创建质量检查任务，Redis 只负责后续唤醒。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def schedule_quality_check(
        self, *, workspace_id: str, data_version: str, idempotency_key: str, parent_run_id: str
    ) -> bool:
        return await asyncio.to_thread(
            self._schedule_quality_check, workspace_id, data_version, idempotency_key, parent_run_id
        )

    def _schedule_quality_check(
        self, workspace_id: str, data_version: str, idempotency_key: str, parent_run_id: str
    ) -> bool:
        """重复事件命中唯一索引时复用旧任务，禁止生成重复质量事实。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                INSERT INTO quality_check_jobs
                    (id, organization_id, workspace_id, status, data_version,
                     idempotency_key, parent_run_id)
                VALUES (%s, %s, %s, 'queued', %s, %s, %s)
                ON CONFLICT (organization_id, workspace_id, idempotency_key)
                DO NOTHING
                RETURNING id
                """,
                (f"quality-{uuid4()}", self._context.organization_id, workspace_id,
                 data_version, idempotency_key, parent_run_id),
            ).fetchone()
        return row is not None

    async def claim_quality_check(
        self, *, job_id: str, worker_id: str, lease_seconds: int
    ) -> QualityCheckJob | None:
        return await asyncio.to_thread(self._claim_quality_check, job_id, worker_id, lease_seconds)

    def _claim_quality_check(
        self, job_id: str, worker_id: str, lease_seconds: int
    ) -> QualityCheckJob | None:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                UPDATE quality_check_jobs
                SET status = 'running', attempt_count = attempt_count + 1,
                    lease_owner = %s,
                    lease_expires_at = CURRENT_TIMESTAMP + %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = %s AND id = %s
                  AND status = 'queued'
                  AND (lease_expires_at IS NULL OR lease_expires_at < CURRENT_TIMESTAMP)
                RETURNING id, workspace_id, status, data_version, idempotency_key,
                          parent_run_id, attempt_count, created_at
                """,
                (
                    worker_id, timedelta(seconds=lease_seconds), self._context.organization_id,
                    job_id,
                ),
            ).fetchone()
        return _job_from_row(row) if row is not None else None

    async def list_dispatchable_quality_checks(self, *, limit: int) -> list[QualityCheckJob]:
        return await asyncio.to_thread(self._list_dispatchable_quality_checks, limit)

    def _list_dispatchable_quality_checks(self, limit: int) -> list[QualityCheckJob]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT id, workspace_id, status, data_version, idempotency_key,
                       parent_run_id, attempt_count, created_at
                FROM quality_check_jobs
                WHERE organization_id = %s AND status = 'queued'
                ORDER BY created_at, id
                LIMIT %s
                """,
                (self._context.organization_id, limit),
            ).fetchall()
        return [_job_from_row(row) for row in rows]

    async def complete_quality_check(self, *, job_id: str, worker_id: str) -> bool:
        return await asyncio.to_thread(self._complete_quality_check, job_id, worker_id)

    def _complete_quality_check(self, job_id: str, worker_id: str) -> bool:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                UPDATE quality_check_jobs
                SET status = 'succeeded', lease_owner = NULL, lease_expires_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = %s AND id = %s AND status = 'running'
                  AND lease_owner = %s AND lease_expires_at >= CURRENT_TIMESTAMP
                RETURNING id
                """,
                (self._context.organization_id, job_id, worker_id),
            ).fetchone()
        return row is not None

    async def fail_quality_check(
        self, *, job_id: str, worker_id: str, retry_delay_seconds: int
    ) -> bool:
        return await asyncio.to_thread(
            self._fail_quality_check, job_id, worker_id, retry_delay_seconds
        )

    def _fail_quality_check(self, job_id: str, worker_id: str, retry_delay_seconds: int) -> bool:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                UPDATE quality_check_jobs
                SET status = CASE WHEN attempt_count >= 3 THEN 'failed' ELSE 'queued' END,
                    lease_owner = NULL, lease_expires_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = %s AND id = %s AND status = 'running'
                  AND lease_owner = %s AND lease_expires_at >= CURRENT_TIMESTAMP
                RETURNING id
                """,
                (self._context.organization_id, job_id, worker_id),
            ).fetchone()
        del retry_delay_seconds
        return row is not None


def _job_from_row(row: dict[str, object]) -> QualityCheckJob:
    """将数据库任务行映射为不含凭据和原始响应的领域事实。"""
    created_at = row["created_at"]
    if not isinstance(created_at, datetime):
        raise ValueError("质量任务 created_at 必须是有效时间")
    return QualityCheckJob(
        id=str(row["id"]), workspace_id=str(row["workspace_id"]),
        status=cast(Any, row["status"]),
        data_version=str(row["data_version"]), idempotency_key=str(row["idempotency_key"]),
        parent_run_id=str(row["parent_run_id"]),
        attempt_count=int(cast(Any, row["attempt_count"])),
        created_at=created_at,
    )
