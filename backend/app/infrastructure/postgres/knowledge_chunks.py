"""RAG 切片目录的 PostgreSQL 持久化适配器。"""

from __future__ import annotations

from psycopg_pool import AsyncConnectionPool

from backend.app.domain.knowledge_chunking import KnowledgeChunk
from backend.app.domain.knowledge_governance import KnowledgeChunkGateway


class PostgresKnowledgeChunkGateway(KnowledgeChunkGateway):
    """幂等写入切片正文和完整元数据，状态变更仅影响当前组织。"""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def upsert_chunks(self, *, organization_id: str, chunks: list[KnowledgeChunk]) -> None:
        if not organization_id.strip():
            raise ValueError("organization_id 不能为空")
        async with self._pool.connection() as connection, connection.transaction():
            for chunk in chunks:
                metadata = chunk.metadata
                await connection.execute(
                    """
                    INSERT INTO rag_knowledge_chunks (
                        id, organization_id, document_version_id, ordinal, parent_chunk_id,
                        content, content_hash, source_locator, title_path, language,
                        chunk_strategy, chunk_strategy_version, page_from, page_to, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content, content_hash = EXCLUDED.content_hash,
                        source_locator = EXCLUDED.source_locator, title_path = EXCLUDED.title_path,
                        status = EXCLUDED.status, updated_at = CURRENT_TIMESTAMP
                    WHERE rag_knowledge_chunks.organization_id = EXCLUDED.organization_id
                    """,
                    (
                        chunk.chunk_id, organization_id, chunk.metadata.document_version_id,
                        chunk.ordinal, metadata.parent_chunk_id, chunk.content, chunk.content_hash,
                        metadata.source_locator, list(metadata.title_path), metadata.language,
                        metadata.chunk_strategy, metadata.chunk_strategy_version,
                        metadata.page_from, metadata.page_to, metadata.status,
                    ),
                )

    async def set_chunk_status(
        self, *, organization_id: str, chunk_ids: list[str], status: str
    ) -> None:
        if not chunk_ids:
            return
        async with self._pool.connection() as connection, connection.transaction():
            await connection.execute(
                """
                UPDATE rag_knowledge_chunks
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = %s AND id = ANY(%s)
                """,
                (status, organization_id, chunk_ids),
            )
