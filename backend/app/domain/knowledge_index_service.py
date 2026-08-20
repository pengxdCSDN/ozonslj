"""PostgreSQL 治理表与向量索引之间的安全编排。

Worker 只应通过此服务执行发布、撤回和删除，不能直接对 Chroma Collection
做任意写入。数据库切片目录先记录权威状态，向量索引失败时返回异常并由
任务队列重试；撤回操作始终先把数据库状态改为不可检索，再删除向量。
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from backend.app.domain.knowledge_chunking import KnowledgeChunk
from backend.app.domain.knowledge_governance import KnowledgeChunkGateway
from backend.app.domain.knowledge_retrieval import EmbeddingPort, VectorIndexPort


@dataclass(frozen=True, slots=True)
class IndexingResult:
    """说明 IndexingResult 的职责、状态边界和对外协作关系。"""
    operation: str
    chunk_count: int
    vector_index_updated: bool


class KnowledgeIndexService:
    """用同一批切片 ID 协调 PostgreSQL 与向量索引。"""

    def __init__(
        self,
        *,
        chunk_gateway: KnowledgeChunkGateway,
        embedding: EmbeddingPort,
        vector_index: VectorIndexPort,
    ) -> None:
        """初始化对象依赖和运行时状态。"""
        self._chunk_gateway = chunk_gateway
        self._embedding = embedding
        self._vector_index = vector_index

    async def publish(
        self, *, organization_id: str, chunks: list[KnowledgeChunk]
    ) -> IndexingResult:
        """执行 publish 的业务流程并返回该流程的结果。"""
        if not chunks:
            raise ValueError("禁止发布空切片集合")
        published = [
            replace(chunk, metadata=replace(chunk.metadata, status="published"))
            for chunk in chunks
        ]
        await self._chunk_gateway.upsert_chunks(
            organization_id=organization_id, chunks=published
        )
        embeddings = await self._embedding.embed([chunk.content for chunk in published])
        await self._vector_index.upsert(published, embeddings)
        return IndexingResult("publish", len(published), True)

    async def withdraw(
        self, *, organization_id: str, chunks: list[KnowledgeChunk]
    ) -> IndexingResult:
        """执行 withdraw 的业务流程并返回该流程的结果。"""
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        if not chunk_ids:
            return IndexingResult("withdraw", 0, True)
        await self._chunk_gateway.set_chunk_status(
            organization_id=organization_id, chunk_ids=chunk_ids, status="withdrawn"
        )
        await self._vector_index.delete(chunk_ids)
        return IndexingResult("withdraw", len(chunk_ids), True)

    async def delete(
        self, *, organization_id: str, chunks: list[KnowledgeChunk]
    ) -> IndexingResult:
        """删除索引内容；治理表采用 withdrawn 状态保留审计事实。"""

        return await self.withdraw(organization_id=organization_id, chunks=chunks)
