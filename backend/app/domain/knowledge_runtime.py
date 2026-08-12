"""知识问答运行时索引的最小生命周期实现。

摄取完成与可检索发布明确分开：切片先进入草稿区，只有发布后才重建关键词
和向量索引。撤回或删除会同时重建两条检索通道，避免已撤回知识残留。
"""

from __future__ import annotations

from dataclasses import replace

from backend.app.domain.knowledge_chunking import KnowledgeChunk
from backend.app.domain.knowledge_query import KnowledgeQueryEngine
from backend.app.domain.knowledge_retrieval import (
    DeterministicEmbedding,
    InMemoryKeywordIndex,
    InMemoryVectorIndex,
)


class KnowledgeRuntimeIndex:
    """内存运行时索引；生产环境可替换为 PostgreSQL + Chroma 实现。"""

    def __init__(self) -> None:
        self._embedding = DeterministicEmbedding()
        self._keyword = InMemoryKeywordIndex()
        self._vector = InMemoryVectorIndex(dimension=self._embedding.dimension)
        self._staged: dict[str, tuple[KnowledgeChunk, ...]] = {}
        self._published: dict[str, tuple[KnowledgeChunk, ...]] = {}
        self._indexed_chunk_ids: set[str] = set()

    def stage(self, version_id: str, chunks: tuple[KnowledgeChunk, ...]) -> None:
        """暂存质量门禁通过的草稿切片，索引尚未可见。"""

        self._staged[version_id] = chunks

    async def publish(self, version_id: str) -> int:
        chunks = self._staged.get(version_id)
        if chunks is None:
            raise KeyError(version_id)
        published = tuple(
            replace(chunk, metadata=replace(chunk.metadata, status="published"))
            for chunk in chunks
        )
        self._published[version_id] = published
        await self._rebuild()
        return len(published)

    async def withdraw(self, version_id: str) -> int:
        removed = len(self._published.pop(version_id, ()))
        await self._rebuild()
        return removed

    async def delete(self, version_id: str) -> int:
        removed = len(self._published.pop(version_id, ()))
        removed += len(self._staged.pop(version_id, ()))
        await self._rebuild()
        return removed

    def engine(self) -> KnowledgeQueryEngine:
        return KnowledgeQueryEngine(
            embedding=self._embedding,
            keyword_index=self._keyword,
            vector_index=self._vector,
        )

    def has_published(self) -> bool:
        return bool(self._published)

    def has_staged(self, version_id: str) -> bool:
        return version_id in self._staged

    def has_published_version(self, version_id: str) -> bool:
        return version_id in self._published

    async def _rebuild(self) -> None:
        chunks = [chunk for group in self._published.values() for chunk in group]
        await self._keyword.replace(chunks)
        await self._vector.delete(list(self._indexed_chunk_ids))
        if chunks:
            await self._vector.upsert(
                chunks, await self._embedding.embed([chunk.content for chunk in chunks])
            )
        self._indexed_chunk_ids = {
            chunk.chunk_id
            for group in self._published.values()
            for chunk in group
        }


runtime_index = KnowledgeRuntimeIndex()
