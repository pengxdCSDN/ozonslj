import pytest

from backend.app.domain.knowledge_chunking import (
    ChunkingRequest,
    ChunkMetadata,
    build_default_chunk_registry,
)
from backend.app.domain.knowledge_retrieval import (
    DeterministicEmbedding,
    InMemoryKeywordIndex,
    InMemoryVectorIndex,
    hybrid_retrieve,
)


def _chunks() -> list:
    metadata = ChunkMetadata(
        document_id="d", document_version_id="v", business_domain="requirements",
        source_type="markdown", source_level="b", language="zh-CN", title_path=("RAG",),
        source_locator="docs/rag.md",
        chunk_strategy="markdown_sections",
        chunk_strategy_version="1",
    )
    return build_default_chunk_registry().chunk(
        ChunkingRequest(
            content="# RAG\n\nChroma 向量检索\n\nPostgreSQL 关键词检索",
            metadata=metadata,
        )
    )


@pytest.mark.asyncio
async def test_vector_upsert_delete_and_dimension_guard() -> None:
    chunks = _chunks()
    model = DeterministicEmbedding()
    index = InMemoryVectorIndex(dimension=model.dimension)
    vectors = await model.embed([chunk.content for chunk in chunks])
    await index.upsert(chunks, vectors)
    assert (await index.search(vectors[0], limit=1))[0].chunk.chunk_id == chunks[0].chunk_id
    await index.delete([chunks[0].chunk_id])
    remaining = await index.search(vectors[0], limit=10)
    assert all(hit.chunk.chunk_id != chunks[0].chunk_id for hit in remaining)
    with pytest.raises(ValueError, match="维度"):
        await index.upsert(chunks, [[0.0]])


@pytest.mark.asyncio
async def test_hybrid_retrieve_fuses_keyword_and_vector_channels() -> None:
    chunks = _chunks()
    model = DeterministicEmbedding()
    vector = InMemoryVectorIndex(dimension=model.dimension)
    await vector.upsert(chunks, await model.embed([chunk.content for chunk in chunks]))
    keyword = InMemoryKeywordIndex()
    await keyword.replace(chunks)
    hits = await hybrid_retrieve(
        "Chroma", embedding=model, keyword_index=keyword, vector_index=vector, limit=5
    )
    assert hits
    assert any("vector" in hit.channel for hit in hits)
    assert any("keyword" in hit.channel for hit in hits)
