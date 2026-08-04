from uuid import uuid4

from psycopg import errors
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.domain.store_workspace import WorkspaceNotFoundError
from backend.app.domain.sync_job import (
    ClaimedSyncJob,
    SyncJob,
    SyncJobAlreadyActiveError,
    SyncJobGateway,
    SyncJobLeaseLostError,
    SyncJobRunnerGateway,
    SyncMode,
    SyncResourceType,
)


class PostgresSyncJobGateway(SyncJobGateway, SyncJobRunnerGateway):
    """使用 PostgreSQL 部分唯一索引串行化工作区同步任务。"""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create_sync_job(
        self,
        *,
        workspace_id: str,
        resource_type: SyncResourceType,
        sync_mode: SyncMode,
        requested_by: str,
    ) -> SyncJob:
        job_id = f"sync_{uuid4().hex}"
        try:
            async with (
                self._pool.connection() as connection,
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(
                    "SELECT 1 FROM store_workspaces WHERE id = %s AND is_active = true",
                    (workspace_id,),
                )
                if await cursor.fetchone() is None:
                    raise WorkspaceNotFoundError(workspace_id)
                await cursor.execute(
                    """
                    INSERT INTO sync_jobs (
                        id, workspace_id, resource_type, sync_mode, status, requested_by
                    )
                    VALUES (%s, %s, %s, %s, 'queued', %s)
                    RETURNING id, workspace_id, resource_type, sync_mode, status, created_at
                    """,
                    (job_id, workspace_id, resource_type, sync_mode, requested_by),
                )
                row = await cursor.fetchone()
        except errors.UniqueViolation as error:
            if error.diag.constraint_name == "idx_sync_jobs_one_active_workspace":
                raise SyncJobAlreadyActiveError(workspace_id) from error
            raise

        if row is None:
            raise RuntimeError("同步任务创建后未返回记录")
        return SyncJob.model_validate(row)

    async def get_sync_job(
        self,
        *,
        job_id: str,
        workspace_ids: tuple[str, ...],
    ) -> SyncJob | None:
        if not workspace_ids:
            return None
        async with (
            self._pool.connection() as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            await cursor.execute(
                """
                SELECT id, workspace_id, resource_type, sync_mode, status, created_at,
                       completed_at, error_code, error_message
                FROM sync_jobs
                WHERE id = %s AND workspace_id = ANY(%s)
                """,
                (job_id, list(workspace_ids)),
            )
            row = await cursor.fetchone()
        return None if row is None else SyncJob.model_validate(row)

    async def claim_next(self, *, lease_seconds: int) -> ClaimedSyncJob | None:
        """原子领取最早排队任务或接管已过期任务。"""

        async with (
            self._pool.connection() as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            await cursor.execute(
                """
                WITH candidate AS (
                    SELECT jobs.id
                    FROM sync_jobs AS jobs
                    JOIN store_workspaces AS workspaces ON workspaces.id = jobs.workspace_id
                    WHERE workspaces.is_active = true
                      AND (
                          jobs.status = 'queued'
                          OR (
                              jobs.status = 'running'
                              AND jobs.lease_expires_at < now()
                          )
                      )
                    ORDER BY jobs.created_at, jobs.id
                    FOR UPDATE OF jobs SKIP LOCKED
                    LIMIT 1
                )
                UPDATE sync_jobs AS jobs
                SET status = 'running',
                    attempt_count = jobs.attempt_count + 1,
                    started_at = COALESCE(jobs.started_at, now()),
                    heartbeat_at = now(),
                    lease_expires_at = now() + make_interval(secs => %s)
                FROM candidate
                WHERE jobs.id = candidate.id
                RETURNING jobs.id, jobs.workspace_id, jobs.resource_type, jobs.sync_mode,
                          jobs.status, jobs.created_at, jobs.attempt_count
                """,
                (lease_seconds,),
            )
            row = await cursor.fetchone()
        return None if row is None else ClaimedSyncJob.model_validate(row)

    async def heartbeat(self, job: ClaimedSyncJob, *, lease_seconds: int) -> None:
        await self._update_running_job(
            job,
            """
            UPDATE sync_jobs
            SET heartbeat_at = now(),
                lease_expires_at = now() + make_interval(secs => %s)
            WHERE id = %s AND status = 'running' AND attempt_count = %s
            """,
            (lease_seconds, job.id, job.attempt_count),
        )

    async def mark_succeeded(self, job: ClaimedSyncJob) -> None:
        await self._update_running_job(
            job,
            """
            UPDATE sync_jobs
            SET status = 'succeeded', completed_at = now(), heartbeat_at = now(),
                lease_expires_at = NULL, error_code = NULL, error_message = NULL
            WHERE id = %s AND status = 'running' AND attempt_count = %s
            """,
            (job.id, job.attempt_count),
        )

    async def mark_failed(self, job: ClaimedSyncJob, *, code: str, message: str) -> None:
        await self._update_running_job(
            job,
            """
            UPDATE sync_jobs
            SET status = 'failed', completed_at = now(), heartbeat_at = now(),
                lease_expires_at = NULL, error_code = %s, error_message = %s
            WHERE id = %s AND status = 'running' AND attempt_count = %s
            """,
            (code, message, job.id, job.attempt_count),
        )

    async def _update_running_job(
        self,
        job: ClaimedSyncJob,
        statement: str,
        parameters: tuple[object, ...],
    ) -> None:
        async with self._pool.connection() as connection:
            cursor = await connection.execute(statement, parameters)
            if cursor.rowcount != 1:
                raise SyncJobLeaseLostError(job.id)
