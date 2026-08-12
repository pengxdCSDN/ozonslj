from backend.app.domain.citation_validation import validate_claims
from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
from backend.app.domain.knowledge_retrieval import RetrievalHit


def test_claim_cannot_cite_unknown_or_unpublished_chunk() -> None:
    metadata = ChunkMetadata(
        document_id="d", document_version_id="v", business_domain="general",
        source_type="markdown", source_level="a", language="zh-CN", title_path=(),
        source_locator="docs/a.md", chunk_strategy="markdown_sections",
        chunk_strategy_version="1", status="published",
    )
    hit = RetrievalHit(KnowledgeChunk("c1", "证据", "h", 0, metadata), 1.0, "hybrid")
    supported, unsupported = validate_claims(
        [("claim-1", "有证据", ("c1",)), ("claim-2", "无证据", ("missing",))], [hit]
    )
    assert supported.support_status == "supported"
    assert unsupported.support_status == "unsupported"
