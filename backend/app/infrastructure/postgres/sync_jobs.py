from uuid import uuid4

from psycopg import errors
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.domain.store_workspace import WorkspaceNotFoundError
from backend.app.domain.sync_job import (
    SyncJob,
    SyncJobAlreadyActiveError,
    SyncJobGateway,
    SyncMode,
    SyncResourceType,
)


class PostgresSyncJobGateway(SyncJobGateway):
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
