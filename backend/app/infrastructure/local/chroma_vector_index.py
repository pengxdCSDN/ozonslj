"""Chroma 向量索引适配器。

Chroma 是可替换的基础设施实现，领域层只依赖 ``VectorIndexPort``。模块采用
依赖注入接收 collection，因此未安装 chromadb 的测试环境也可以用 fake collection
验证 upsert/delete/search 契约；生产启动时再注入真实 Chroma collection。
"""

from __future__ import annotations

from typing import Protocol, cast

import httpx

from backend.app.domain.knowledge_chunking import KnowledgeChunk
from backend.app.domain.knowledge_retrieval import RetrievalHit, VectorIndexPort


class ChromaCollection(Protocol):
    def upsert(
        self, *, ids: list[str], documents: list[str], embeddings: list[list[float]],
        metadatas: list[dict[str, str]]
    ) -> None: ...

    def delete(self, *, ids: list[str]) -> None: ...

    def query(
        self, *, query_embeddings: list[list[float]], n_results: int, include: list[str]
    ) -> dict[str, object]: ...


class HttpChromaCollection:
    """Chroma v1 HTTP Collection 客户端；不依赖 ``chromadb`` Python 包。"""

    def __init__(
        self,
        base_url: str,
        collection_id: str,
        *,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._collection_id = collection_id
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def upsert(
        self,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, str]],
    ) -> None:
        await self._request(
            "POST",
            "upsert",
            {"ids": ids, "documents": documents, "embeddings": embeddings, "metadatas": metadatas},
        )

    async def delete(self, *, ids: list[str]) -> None:
        await self._request("POST", "delete", {"ids": ids})

    async def query(
        self, *, query_embeddings: list[list[float]], n_results: int, include: list[str]
    ) -> dict[str, object]:
        return await self._request(
            "POST",
            "query",
            {"query_embeddings": query_embeddings, "n_results": n_results, "include": include},
        )

    async def _request(
        self, method: str, operation: str, payload: dict[str, object]
    ) -> dict[str, object]:
        path = f"/api/v1/collections/{self._collection_id}/{operation}"
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.request(method, path, json=payload)
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as error:
            raise RuntimeError(f"Chroma {operation} 请求失败") from error
        if not response.content:
            return {}
        try:
            body = response.json()
        except ValueError as error:
            raise RuntimeError(f"Chroma {operation} 返回非 JSON") from error
        if not isinstance(body, dict):
            raise RuntimeError(f"Chroma {operation} 返回格式无效")
        return cast(dict[str, object], body)


class ChromaVectorIndex(VectorIndexPort):
    """将 Chroma 的距离结果转换为统一的 ``RetrievalHit``。"""

    def __init__(self, collection: ChromaCollection, chunks: dict[str, KnowledgeChunk]) -> None:
        self._collection = collection
        self._chunks = chunks

    async def upsert(self, chunks: list[KnowledgeChunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("切片和向量数量不一致，禁止写入不完整索引")
        self._chunks.update({chunk.chunk_id: chunk for chunk in chunks})
        self._collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.content for chunk in chunks],
            embeddings=embeddings,
            metadatas=[{"source_locator": chunk.metadata.source_locator} for chunk in chunks],
        )

    async def delete(self, chunk_ids: list[str]) -> None:
        self._collection.delete(ids=chunk_ids)
        for chunk_id in chunk_ids:
            self._chunks.pop(chunk_id, None)

    async def search(self, embedding: list[float], *, limit: int) -> list[RetrievalHit]:
        result = self._collection.query(
            query_embeddings=[embedding], n_results=limit, include=["distances"]
        )
        ids = _nested_strings(result.get("ids"))
        distances = _nested_numbers(result.get("distances"))
        return [
            RetrievalHit(self._chunks[chunk_id], 1.0 / (1.0 + distance), "vector")
            for chunk_id, distance in zip(ids, distances, strict=False)
            if chunk_id in self._chunks
        ]


class HttpChromaVectorIndex(VectorIndexPort):
    """将异步 HTTP Collection 转换为统一的向量索引端口。"""

    def __init__(self, collection: HttpChromaCollection, chunks: dict[str, KnowledgeChunk]) -> None:
        self._collection = collection
        self._chunks = chunks

    async def upsert(self, chunks: list[KnowledgeChunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("切片和向量数量不一致，禁止写入不完整索引")
        await self._collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.content for chunk in chunks],
            embeddings=embeddings,
            metadatas=[{"source_locator": chunk.metadata.source_locator} for chunk in chunks],
        )
        self._chunks.update({chunk.chunk_id: chunk for chunk in chunks})

    async def delete(self, chunk_ids: list[str]) -> None:
        await self._collection.delete(ids=chunk_ids)
        for chunk_id in chunk_ids:
            self._chunks.pop(chunk_id, None)

    async def search(self, embedding: list[float], *, limit: int) -> list[RetrievalHit]:
        result = await self._collection.query(
            query_embeddings=[embedding], n_results=limit, include=["distances"]
        )
        ids = _nested_strings(result.get("ids"))
        distances = _nested_numbers(result.get("distances"))
        return [
            RetrievalHit(self._chunks[chunk_id], 1.0 / (1.0 + distance), "vector")
            for chunk_id, distance in zip(ids, distances, strict=False)
            if chunk_id in self._chunks
        ]


def _nested_strings(value: object) -> list[str]:
    rows = cast(list[object], value) if isinstance(value, list) else []
    first = rows[0] if rows and isinstance(rows[0], list) else rows
    return [item for item in first if isinstance(item, str)]


def _nested_numbers(value: object) -> list[float]:
    rows = cast(list[object], value) if isinstance(value, list) else []
    first = rows[0] if rows and isinstance(rows[0], list) else rows
    return [float(item) for item in first if isinstance(item, (int, float))]
