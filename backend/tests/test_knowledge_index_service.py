"""知识索引服务的数据库先行与向量同步测试。"""

import pytest

from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
from backend.app.domain.knowledge_index_service import KnowledgeIndexService
from backend.app.domain.knowledge_retrieval import DeterministicEmbedding, InMemoryVectorIndex


class FakeGateway:
    def __init__(self) -> None:
        self.upserted: list[KnowledgeChunk] = []
        self.status_updates: list[tuple[list[str], str]] = []

    async def upsert_chunks(self, *, organization_id: str, chunks: list[KnowledgeChunk]) -> None:
        self.upserted.extend(chunks)

    async def set_chunk_status(
        self, *, organization_id: str, chunk_ids: list[str], status: str
    ) -> None:
        self.status_updates.append((chunk_ids, status))


def _chunk() -> KnowledgeChunk:
    return KnowledgeChunk(
        "svc-chunk", "库存安全线是 10 件", "svc-hash", 0,
        ChunkMetadata(
            document_id="doc", document_version_id="ver", business_domain="sop",
            source_type="markdown", source_level="b", language="zh-CN", title_path=("SOP",),
            source_locator="docs/sop.md", chunk_strategy="markdown_sections",
            chunk_strategy_version="1", status="draft",
        ),
    )


@pytest.mark.asyncio
async def test_publish_writes_published_metadata_before_vector_and_withdraws() -> None:
    gateway = FakeGateway()
    service = KnowledgeIndexService(
        chunk_gateway=gateway,
        embedding=DeterministicEmbedding(),
        vector_index=InMemoryVectorIndex(dimension=32),
    )
    result = await service.publish(organization_id="org", chunks=[_chunk()])
    assert result == result.__class__("publish", 1, True)
    assert gateway.upserted[0].metadata.status == "published"
    withdrawn = await service.withdraw(organization_id="org", chunks=[_chunk()])
    assert withdrawn.operation == "withdraw"
    assert gateway.status_updates == [(["svc-chunk"], "withdrawn")]
