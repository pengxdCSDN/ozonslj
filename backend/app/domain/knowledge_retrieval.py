"""知识型混合检索端口与确定性内存实现。"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Protocol

from backend.app.domain.knowledge_chunking import KnowledgeChunk


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    """候选命中及其来源通道分数；回答层必须再次执行治理校验。"""

    chunk: KnowledgeChunk
    score: float
    channel: str


class EmbeddingPort(Protocol):
    model_id: str
    dimension: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class KeywordSearchPort(Protocol):
    async def search(self, query: str, *, limit: int) -> list[RetrievalHit]: ...


class VectorIndexPort(Protocol):
    async def upsert(self, chunks: list[KnowledgeChunk], embeddings: list[list[float]]) -> None: ...

    async def delete(self, chunk_ids: list[str]) -> None: ...

    async def search(self, embedding: list[float], *, limit: int) -> list[RetrievalHit]: ...


class DeterministicEmbedding:
    """测试专用哈希向量，不代表生产嵌入模型。"""

    model_id = "fake-hash-v1"
    dimension = 32

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_hash_vector(text, self.dimension) for text in texts]


class InMemoryVectorIndex:
    """Chroma 契约的内存替身，用于不依赖外部服务的契约测试。"""

    def __init__(self, *, dimension: int) -> None:
        self._dimension = dimension
        self._items: dict[str, tuple[KnowledgeChunk, list[float]]] = {}

    async def upsert(self, chunks: list[KnowledgeChunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("切片和向量数量不一致")
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            if len(embedding) != self._dimension:
                raise ValueError("嵌入维度不匹配，禁止混用向量空间")
            self._items[chunk.chunk_id] = (chunk, embedding)

    async def delete(self, chunk_ids: list[str]) -> None:
        for chunk_id in chunk_ids:
            self._items.pop(chunk_id, None)

    async def search(self, embedding: list[float], *, limit: int) -> list[RetrievalHit]:
        if len(embedding) != self._dimension:
            raise ValueError("查询向量维度不匹配")
        ranked = sorted(
            (
                RetrievalHit(chunk, _cosine(embedding, vector), "vector")
                for chunk, vector in self._items.values()
            ),
            key=lambda hit: (-hit.score, hit.chunk.chunk_id),
        )
        return ranked[:limit]


class InMemoryKeywordIndex:
    """确定性关键词替身；生产实现由 PostgreSQL FTS 适配器承载。"""

    def __init__(self) -> None:
        self._chunks: dict[str, KnowledgeChunk] = {}

    async def replace(self, chunks: list[KnowledgeChunk]) -> None:
        self._chunks = {chunk.chunk_id: chunk for chunk in chunks}

    async def search(self, query: str, *, limit: int) -> list[RetrievalHit]:
        # 中文没有稳定的空格分词；同时保留空格词和连续汉字单字，避免中文问题完全失去关键词通道。
        terms = {term.casefold() for term in query.split() if term.strip()}
        terms.update(character for character in query if "\u4e00" <= character <= "\u9fff")
        hits = []
        for chunk in self._chunks.values():
            haystack = chunk.content.casefold()
            score = sum(term in haystack for term in terms) / max(len(terms), 1)
            # 中文单字召回容易让共享字符的切片并列；完整短语命中是更强的确定性信号。
            if query.casefold() in haystack:
                score += 2.0
            if score > 0:
                hits.append(RetrievalHit(chunk, float(score), "keyword"))
        return sorted(hits, key=lambda hit: (-hit.score, hit.chunk.chunk_id))[:limit]


async def hybrid_retrieve(
    query: str,
    *,
    embedding: EmbeddingPort,
    keyword_index: KeywordSearchPort,
    vector_index: VectorIndexPort,
    limit: int = 10,
) -> list[RetrievalHit]:
    """并行前的最小混合召回；RRF 融合避免跨模型原始分数不可比。"""

    query_embedding = (await embedding.embed([query]))[0]
    keyword_hits = await keyword_index.search(query, limit=limit)
    vector_hits = await vector_index.search(query_embedding, limit=limit)
    ranks: dict[str, tuple[KnowledgeChunk, float, set[str]]] = {}
    for rank, hit in enumerate([*keyword_hits, *vector_hits], start=1):
        chunk, score, channels = ranks.get(hit.chunk.chunk_id, (hit.chunk, 0.0, set()))
        # RRF 负责融合通道，明确的连续短语命中仍需保留少量词法优势；否则哈希向量
        # 的偶然近邻会把唯一正确片段挤出前五，中文固定评测尤其容易暴露这一点。
        lexical_bonus = min(hit.score, 3.0) * 0.1 if hit.channel == "keyword" else 0.0
        ranks[hit.chunk.chunk_id] = (
            chunk, score + 1.0 / (60 + rank) + lexical_bonus, channels | {hit.channel}
        )
    return [
        RetrievalHit(chunk, score, "+".join(sorted(channels)))
        for chunk, score, channels in sorted(
            ranks.values(), key=lambda item: (-item[1], item[0].chunk_id)
        )[:limit]
    ]


def _hash_vector(text: str, dimension: int) -> list[float]:
    values = [0.0] * dimension
    for index, byte in enumerate(text.encode("utf-8")):
        values[index % dimension] += (byte - 127) / 127
    norm = sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))
