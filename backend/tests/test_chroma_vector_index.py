"""Chroma 适配器契约测试，不连接真实 Chroma 服务。"""

import json

import httpx
import pytest

from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
from backend.app.infrastructure.local.chroma_vector_index import (
    ChromaVectorIndex,
    HttpChromaCollection,
    HttpChromaVectorIndex,
)


class FakeCollection:
    def __init__(self) -> None:
        self.ids: list[str] = []

    def upsert(
        self, *, ids: list[str], documents: list[str], embeddings: list[list[float]],
        metadatas: list[dict[str, str]]
    ) -> None:
        self.ids = ids

    def delete(self, *, ids: list[str]) -> None:
        self.ids = [item for item in self.ids if item not in ids]

    def query(
        self, *, query_embeddings: list[list[float]], n_results: int, include: list[str]
    ) -> dict[str, object]:
        return {"ids": [self.ids[:n_results]], "distances": [[0.25 for _ in self.ids[:n_results]]]}


def _chunk() -> KnowledgeChunk:
    metadata = ChunkMetadata(
        document_id="d", document_version_id="v", business_domain="general",
        source_type="markdown", source_level="a", language="zh-CN", title_path=("测试",),
        source_locator="docs/test.md", chunk_strategy="markdown_section",
        chunk_strategy_version="1", status="published",
    )
    return KnowledgeChunk("chunk-1", "测试证据", "hash", 0, metadata)


@pytest.mark.asyncio
async def test_chroma_adapter_upsert_query_delete() -> None:
    collection = FakeCollection()
    index = ChromaVectorIndex(collection, {})
    chunk = _chunk()
    await index.upsert([chunk], [[1.0, 0.0]])
    hits = await index.search([1.0, 0.0], limit=2)
    assert hits[0].chunk.chunk_id == "chunk-1"
    assert hits[0].score == pytest.approx(0.8)
    await index.delete(["chunk-1"])
    assert await index.search([1.0, 0.0], limit=2) == []


@pytest.mark.asyncio
async def test_http_chroma_adapter_uses_collection_endpoints() -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        payload = json.loads(body.decode("utf-8")) if body else {}
        calls.append((request.method, request.url.path, payload))
        if request.url.path.endswith("/query"):
            return httpx.Response(200, json={"ids": [["chunk-1"]], "distances": [[0.25]]})
        return httpx.Response(200, json={})

    collection = HttpChromaCollection(
        "http://chroma:8000", "collection-1", transport=httpx.MockTransport(handler)
    )
    index = HttpChromaVectorIndex(collection, {})
    chunk = _chunk()
    await index.upsert([chunk], [[1.0, 0.0]])
    hits = await index.search([1.0, 0.0], limit=2)
    await index.delete(["chunk-1"])

    assert hits[0].chunk.chunk_id == "chunk-1"
    assert [call[1].rsplit("/", 1)[-1] for call in calls] == ["upsert", "query", "delete"]


@pytest.mark.asyncio
async def test_http_chroma_collection_ensure_uses_stable_collection_name() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, json.loads(request.read().decode("utf-8"))))
        return httpx.Response(200, json={"id": "stable-collection"})

    collection = await HttpChromaCollection.ensure(
        "http://chroma:8000",
        "ozonslj_knowledge",
        transport=httpx.MockTransport(handler),
    )

    assert collection._collection_id == "stable-collection"  # noqa: SLF001
    assert calls == [("/api/v1/collections", {"name": "ozonslj_knowledge", "get_or_create": True})]


@pytest.mark.asyncio
async def test_http_chroma_collection_count_reads_integer_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path.endswith("/count")
        return httpx.Response(200, json=1234)

    collection = HttpChromaCollection(
        "http://chroma:8000", "collection-1", transport=httpx.MockTransport(handler)
    )
    assert await collection.count() == 1234


@pytest.mark.asyncio
async def test_http_chroma_collection_existing_ids_reads_id_list() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("/get")
        return httpx.Response(200, json={"ids": ["chunk-1"]})

    collection = HttpChromaCollection(
        "http://chroma:8000", "collection-1", transport=httpx.MockTransport(handler)
    )
    assert await collection.existing_ids(["chunk-1", "chunk-2"]) == {"chunk-1"}


@pytest.mark.asyncio
async def test_http_chroma_adapter_rejects_invalid_json() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    collection = HttpChromaCollection(
        "http://chroma:8000", "collection-1", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(RuntimeError, match="非 JSON"):
        await collection.query(query_embeddings=[[1.0]], n_results=1, include=["distances"])
