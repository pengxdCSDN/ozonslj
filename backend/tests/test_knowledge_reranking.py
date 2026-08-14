"""精排和多跳预算的回归测试。"""

from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
from backend.app.domain.knowledge_reranking import bounded_hop_queries, rerank_hits
from backend.app.domain.knowledge_retrieval import RetrievalHit


def _hit(chunk_id: str, status: str, level: str, score: float, title: str) -> RetrievalHit:
    metadata = ChunkMetadata(
        document_id="d", document_version_id="v", business_domain="general",
        source_type="markdown", source_level=level, language="zh-CN", title_path=(title,),
        source_locator="docs/a.md", chunk_strategy="markdown_section", chunk_strategy_version="1",
        status=status,
    )
    chunk = KnowledgeChunk(chunk_id, "evidence", "h" + chunk_id, 0, metadata)
    return RetrievalHit(chunk, score, "hybrid")


def test_rerank_filters_draft_and_prefers_authority() -> None:
    hits = [
        _hit("b", "published", "b", 0.8, "B"),
        _hit("a", "published", "a", 0.8, "A"),
        _hit("d", "draft", "a", 1.0, "D"),
    ]
    ranked = rerank_hits(hits)
    assert [hit.chunk.chunk_id for hit in ranked] == ["a", "b"]


def test_multi_hop_is_bounded_and_deduplicated() -> None:
    evidence = [_hit("a", "published", "a", 1.0, "成本"), _hit("b", "published", "a", 0.9, "利润")]
    assert bounded_hop_queries("价格", evidence, max_hops=1) == ("成本",)
