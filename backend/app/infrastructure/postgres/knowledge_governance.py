"""RAG 知识治理的 PostgreSQL 适配器；不负责解析、嵌入或 Chroma 写入。"""

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.domain.knowledge_governance import (
    IngestionJob,
    KnowledgeGovernanceGateway,
    KnowledgeSource,
    KnowledgeVersion,
)


class PostgresKnowledgeGovernanceGateway(KnowledgeGovernanceGateway):
    """将领域治理对象映射到 0090 migration 建立的关系表。"""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        """初始化对象依赖和运行时状态。"""
        self._pool = pool

    async def create_source(self, source: KnowledgeSource) -> KnowledgeSource:
        """执行 create_source 的业务流程并返回该流程的结果。"""
        async with self._pool.connection() as connection, connection.transaction():
            await connection.execute(
                """
                INSERT INTO rag_knowledge_sources (
                    id, organization_id, source_type, business_domain, title,
                    authority_level, sensitivity, status, source_locator
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (source.id, source.organization_id, source.source_type, source.business_domain,
                 source.title, source.authority_level, source.sensitivity, source.status,
                 source.source_locator),
            )
        return source

    async def create_version(self, version: KnowledgeVersion) -> KnowledgeVersion:
        """执行 create_version 的业务流程并返回该流程的结果。"""
        async with self._pool.connection() as connection, connection.transaction():
            await connection.execute(
                """
                INSERT INTO rag_document_versions (
                    id, organization_id, source_id, version_number, content_hash,
                    parser_name, parser_version, cleaner_version, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (version.id, version.organization_id, version.source_id, version.version_number,
                 version.content_hash, version.parser_name, version.parser_version,
                 version.cleaner_version, version.status),
            )
        return version

    async def create_job(self, job: IngestionJob) -> IngestionJob:
        """执行 create_job 的业务流程并返回该流程的结果。"""
        async with self._pool.connection() as connection, connection.transaction():
            await connection.execute(
                """
                INSERT INTO rag_ingestion_jobs (
                    id, organization_id, source_id, document_version_id, job_type,
                    status, idempotency_key, attempt_count, error_code, error_summary
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (job.id, job.organization_id, job.source_id, job.document_version_id,
                 job.job_type, job.status, job.idempotency_key, job.attempt_count,
                 job.error_code, job.error_summary),
            )
        return job

    async def set_version_status(
        self, *, organization_id: str, version_id: str, status: str
    ) -> KnowledgeVersion:
        """执行 set_version_status 的业务流程并返回该流程的结果。"""
        async with (
            self._pool.connection() as connection,
            connection.transaction(),
            connection.cursor(row_factory=dict_row) as cursor,
        ):
                await cursor.execute(
                    """
                    UPDATE rag_document_versions SET status = %s
                    WHERE id = %s AND organization_id = %s
                    RETURNING id, organization_id, source_id, version_number, content_hash,
                              parser_name, parser_version, cleaner_version, status
                    """,
                    (status, version_id, organization_id),
                )
                row = await cursor.fetchone()
                if row is None:
                    raise ValueError("RAG 文档版本不存在或不属于当前组织")
        return _version_from_row(row)

    async def set_source_status(
        self, *, organization_id: str, source_id: str, status: str
    ) -> KnowledgeSource:
        """执行 set_source_status 的业务流程并返回该流程的结果。"""
        async with (
            self._pool.connection() as connection,
            connection.transaction(),
            connection.cursor(row_factory=dict_row) as cursor,
        ):
                await cursor.execute(
                    """
                    UPDATE rag_knowledge_sources SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND organization_id = %s
                    RETURNING id, organization_id, source_type, business_domain, title,
                              authority_level, sensitivity, status, source_locator
                    """,
                    (status, source_id, organization_id),
                )
                row = await cursor.fetchone()
                if row is None:
                    raise ValueError("RAG 知识来源不存在或不属于当前组织")
        return _source_from_row(row)


def _source_from_row(row: dict[str, object]) -> KnowledgeSource:
    """执行内部步骤 _source_from_row，供同一模块的公开流程复用。"""
    return KnowledgeSource(**{key: str(row[key]) for key in (
        "id", "organization_id", "source_type", "business_domain", "title",
        "authority_level", "sensitivity", "status", "source_locator",
    )})  # type: ignore[arg-type]


def _version_from_row(row: dict[str, object]) -> KnowledgeVersion:
    """执行内部步骤 _version_from_row，供同一模块的公开流程复用。"""
    return KnowledgeVersion(
        id=str(row["id"]), organization_id=str(row["organization_id"]),
        source_id=str(row["source_id"]), version_number=int(str(row["version_number"])),
        content_hash=str(row["content_hash"]), parser_name=str(row["parser_name"]),
        parser_version=str(row["parser_version"]), cleaner_version=str(row["cleaner_version"]),
        status=str(row["status"]),  # type: ignore[arg-type]
    )
