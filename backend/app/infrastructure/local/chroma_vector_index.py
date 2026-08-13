"""Chroma 向量索引适配器。

Chroma 是可替换的基础设施实现，领域层只依赖 ``VectorIndexPort``。模块采用
依赖注入接收 collection，因此未安装 chromadb 的测试环境也可以用 fake collection
验证 upsert/delete/search 契约；生产启动时再注入真实 Chroma collection。
"""

from __future__ import annotations

from typing import Literal, Protocol, cast

import httpx

from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
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

    @classmethod
    async def ensure(
        cls,
        base_url: str,
        name: str,
        *,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> HttpChromaCollection:
        """获取或创建受控 collection；名称固定，避免每次 API 重启生成新索引。"""
        async with httpx.AsyncClient(
            base_url=base_url.rstrip("/"), timeout=timeout_seconds, transport=transport
        ) as client:
            response = await client.post(
                "/api/v1/collections", json={"name": name, "get_or_create": True}
            )
            response.raise_for_status()
            body = response.json()
        collection_id = body.get("id") if isinstance(body, dict) else None
        if not isinstance(collection_id, str) or not collection_id:
            raise RuntimeError("Chroma collection 响应缺少 id")
        return cls(
            base_url,
            collection_id,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )

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
            metadatas=[_metadata_for_chunk(chunk) for chunk in chunks],
        )

    async def delete(self, chunk_ids: list[str]) -> None:
        self._collection.delete(ids=chunk_ids)
        for chunk_id in chunk_ids:
            self._chunks.pop(chunk_id, None)

    async def search(self, embedding: list[float], *, limit: int) -> list[RetrievalHit]:
        result = self._collection.query(
            query_embeddings=[embedding], n_results=limit,
            include=["distances", "documents", "metadatas"],
        )
        ids = _nested_strings(result.get("ids"))
        distances = _nested_numbers(result.get("distances"))
        documents = _nested_strings(result.get("documents"))
        metadata_rows = _nested_metadata(result.get("metadatas"))
        hits: list[RetrievalHit] = []
        for index, (chunk_id, distance) in enumerate(zip(ids, distances, strict=False)):
            chunk = self._chunks.get(chunk_id)
            if chunk is None and index < len(documents):
                chunk = _chunk_from_chroma(chunk_id, documents[index], metadata_rows[index])
            if chunk is not None:
                hits.append(RetrievalHit(chunk, 1.0 / (1.0 + distance), "vector"))
        return hits


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
            metadatas=[_metadata_for_chunk(chunk) for chunk in chunks],
        )
        self._chunks.update({chunk.chunk_id: chunk for chunk in chunks})

    async def delete(self, chunk_ids: list[str]) -> None:
        await self._collection.delete(ids=chunk_ids)
        for chunk_id in chunk_ids:
            self._chunks.pop(chunk_id, None)

    async def search(self, embedding: list[float], *, limit: int) -> list[RetrievalHit]:
        result = await self._collection.query(
            query_embeddings=[embedding], n_results=limit,
            include=["distances", "documents", "metadatas"],
        )
        ids = _nested_strings(result.get("ids"))
        distances = _nested_numbers(result.get("distances"))
        documents = _nested_strings(result.get("documents"))
        metadata_rows = _nested_metadata(result.get("metadatas"))
        hits: list[RetrievalHit] = []
        for index, (chunk_id, distance) in enumerate(zip(ids, distances, strict=False)):
            chunk = self._chunks.get(chunk_id)
            if chunk is None and index < len(documents):
                chunk = _chunk_from_chroma(chunk_id, documents[index], metadata_rows[index])
            if chunk is not None:
                hits.append(RetrievalHit(chunk, 1.0 / (1.0 + distance), "vector"))
        return hits


def _nested_strings(value: object) -> list[str]:
    rows = cast(list[object], value) if isinstance(value, list) else []
    first = rows[0] if rows and isinstance(rows[0], list) else rows
    return [item for item in first if isinstance(item, str)]


def _nested_numbers(value: object) -> list[float]:
    rows = cast(list[object], value) if isinstance(value, list) else []
    first = rows[0] if rows and isinstance(rows[0], list) else rows
    return [float(item) for item in first if isinstance(item, (int, float))]


def _metadata_for_chunk(chunk: KnowledgeChunk) -> dict[str, str]:
    """写入引用所需的非敏感元数据，支持 API 重启后从 Chroma 恢复结果。"""
    metadata = chunk.metadata
    return {
        "document_id": metadata.document_id,
        "document_version_id": metadata.document_version_id,
        "business_domain": metadata.business_domain,
        "source_type": metadata.source_type,
        "source_level": metadata.source_level,
        "language": metadata.language,
        "title_path": "\\n".join(metadata.title_path),
        "source_locator": metadata.source_locator,
        "chunk_strategy": metadata.chunk_strategy,
        "chunk_strategy_version": metadata.chunk_strategy_version,
        "status": metadata.status,
        "sensitivity": metadata.sensitivity,
        "page_from": str(metadata.page_from or ""),
        "page_to": str(metadata.page_to or ""),
        # 暂停来源仍保留数据库版本，但向量召回必须忽略其结果。
        "source_status": dict(metadata.extra).get("source_status", "active"),
    }


def _nested_metadata(value: object) -> list[dict[str, str]]:
    rows = cast(list[object], value) if isinstance(value, list) else []
    first = rows[0] if rows and isinstance(rows[0], list) else rows
    return [
        {str(key): str(item) for key, item in row.items()}
        for row in first
        if isinstance(row, dict)
    ]


def _chunk_from_chroma(
    chunk_id: str, content: str, metadata: dict[str, str]
) -> KnowledgeChunk | None:
    if (
        not content
        or not metadata.get("document_version_id")
        or metadata.get("source_status", "active") != "active"
    ):
        return None
    title_path = tuple(filter(None, metadata.get("title_path", "").split("\\n")))
    chunk_metadata = ChunkMetadata(
        document_id=metadata.get("document_id", ""),
        document_version_id=metadata["document_version_id"],
        business_domain=cast(
            Literal[
                "domain_language", "requirements", "architecture", "api", "database", "sop",
                "troubleshooting", "ozon_official", "general",
            ],
            metadata.get("business_domain", "general"),
        ),
        source_type=cast(
            Literal["markdown", "postgres_schema", "pdf"],
            metadata.get("source_type", "markdown"),
        ),
        source_level=cast(Literal["a", "b", "c"], metadata.get("source_level", "c")),
        language=metadata.get("language", "unknown"), title_path=title_path,
        source_locator=metadata.get("source_locator", "unknown"),
        chunk_strategy=metadata.get("chunk_strategy", "unknown"),
        chunk_strategy_version=metadata.get("chunk_strategy_version", "unknown"),
        status=cast(
            Literal["draft", "published", "withdrawn", "deleted"],
            metadata.get("status", "published"),
        ),
        sensitivity=cast(
            Literal["public", "internal", "restricted"],
            metadata.get("sensitivity", "internal"),
        ),
        page_from=int(metadata["page_from"]) if metadata.get("page_from") else None,
        page_to=int(metadata["page_to"]) if metadata.get("page_to") else None,
    )
    return KnowledgeChunk(chunk_id, content, "chroma", 0, chunk_metadata)
